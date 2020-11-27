import argparse
import boto3
import csv
import logging
import htmlmin
import requests
import sys
import time
import tldextract

from htmlmin import parser
from multiprocessing.dummy import Pool
from functools import partial
from math import log, ceil
from pathlib import Path
from requests import Response
from time import sleep


# Check Python version
if sys.version_info < (3, 6):
    sys.stdout.write("This script requires Python 3.4 or higher\n")
    sys.exit(1)

s3 = boto3.resource("s3")


class Counter:
    def __init__(self, limit: int = 10):
        """
        Counter object with a limit.
        :param limit: Limit of the counter. Any negatives
        """
        self._value = 0
        self._limit = limit

    def increment(self):
        """
        Increment counter unless limit has reached.
        :return: Whether the increment operation was successful.
        """
        if self._value == self._limit:
            return False

        self._value += 1
        return True

    def decrement(self):
        """
        Decrement counter unless the counter is zero.
        :return: Whether the decrement operation was successful.
        """
        if self._value <= 0:
            return False

        self._value -= 1
        return True

    def reset(self, limit: int = 1) -> None:
        """
        Reset the counter.
        :param limit: New limit.
        """
        self._limit = limit
        self._value = 0


class PageFetcher:
    def __init__(self, bucket_name: str, limit_rate: int = 10) -> None:
        """
        Initialise PageFetcher class.

        :param bucket_name: Name of the S3 Bucket to store the fetched HTML files in.
        :param limit_rate: Maximum amount of requests to sent per second.
        """
        # Rate limiting and thread pooling
        self._counter = Counter(limit_rate)
        self._pool = Pool(pow(2, ceil(log(limit_rate) / log(2))))  # IO-Bound, thus increase pool size
        self._error_detected = 0
        self._cool_off_secs = 4  # 15 reqs / min (ddos rate)
        self._ddos_mode = 0
        self._ddos_detection_time = None
        self._ddos_detection_timeout = 180  # 3min

        # Upload
        self.bucket_name = bucket_name

    @staticmethod
    def _get_url(timestamp, url_key):
        return f"http://web.archive.org/web/{timestamp}/{url_key}"

    def _cool_off(self):
        time.sleep(self._cool_off_secs)

    def fetch(self, csv_path: Path, fetch_limit: int = -1) -> None:
        """
        Fetch HTML pages from the Internet Archive.

        :param csv_path: Path to the csv data.
        :param fetch_limit: Limit to the amount of pages to be fetched. A limit of -1 means unbounded fetching from the
        supplied csv file.
        """
        if not csv_path.exists():
            raise IOError("Given csv file does not exists")

        if fetch_limit == 0:
            raise ValueError("Nothing to fetch with a limit of 0")

        try:
            file = open("/tmp/status", "r")
            prev_progress = int(file.read())
            file.close()
        except Exception:
            prev_progress = 0

        with open(str(csv_path), 'r') as csv_file:
            reader = csv.reader(csv_file)
            for i, line in enumerate(reader):
                if i < prev_progress:
                    continue

                # Limit the amount of futures
                if 0 < fetch_limit <= i:
                    break

                # Convert timestamp and url_key to InternetArchive url
                url = self._get_url(timestamp=line[0], url_key=line[1]).encode("utf-8")

                while not self._counter.increment():
                    time.sleep(0.01)

                file = open("/tmp/status", "w")
                file.write(str(i))
                file.close()

                # Error cool off
                if time.time() - self._error_detected < self._cool_off_secs:
                    logging.getLogger().warning("Cool-off initiated")
                    self._cool_off()

                self._pool.apply_async(
                    requests.get,
                    [url],
                    dict(timeout=10),
                    callback=partial(self.__on_success, timestamp=line[0], url_key=line[1]),
                    error_callback=partial(self.__on_error, url=url)
                )

    @staticmethod
    def __url_to_domain(url: str) -> str:
        ext = tldextract.extract(url)
        return '.'.join(part for part in ext if part)

    def __on_success(self, response: Response, timestamp: str, url_key: str) -> None:
        """
        Success callback for a GET request. Does not automatically mean the request was successful, only that there were
        no exceptions.
        :param response: Response from the request.
        :param timestamp: Timestamp from IA, used for logging and traceability.
        :param url_key: Url_key from IA, used for logging and traceability.
        """
        if self._ddos_mode > 0:
            self._error_detected = time.time()
            if self._ddos_mode > 10:
                self._error_detected += 300  # 5min timeout
                logging.getLogger().error("Preventing block with 5 min timeout")
                self._ddos_mode = 1
            if time.time() - self._ddos_detection_time > self._ddos_detection_timeout:
                self._ddos_mode = 0
                self._ddos_detection_time = None
                logging.getLogger().warning("Disabling DDOS Mode")

        url = self._get_url(timestamp, url_key)
        self._counter.decrement()
        if response.ok:  # Status code: 2xx
            logging.getLogger().info(f'{response.status_code}: {url}')
            self.__upload_s3(timestamp, url_key, response.text)
        elif response.status_code == 404:
            logging.getLogger().warning(f'{response.status_code}: {url}')
        elif response.status_code == 429:
            logging.getLogger().error("DDOS prevention detected. Stopping requests to prevent ban")
            self._counter.reset(1)
            self._ddos_mode += 1
            if self._ddos_detection_time is None:
                self._ddos_detection_time = time.time()
        else:
            print(f"Code: {response.status_code} | {url}")
            logging.getLogger().error(f'{response.status_code}: {url} ||| {response.text}|||')

    def __on_error(self, ex: Exception, url: str) -> None:
        """
        Error callback for a GET request.

        :param ex: Exception that has occurred.
        :param url: Url that triggered an exception, used for traceability.
        """
        self._error_detected = time.time()
        self._counter.decrement()
        logging.getLogger().error(f"Exception occurred while fetching {url}")
        logging.getLogger().exception(ex)

    def upload(self, timestamp: str, url_key: str, html: str):
        try:
            encoded_string = htmlmin.minify(html, remove_empty_space=True).encode("utf-8")
        except (htmlmin.parser.OpenTagNotFoundError, NotImplementedError) as e:
            logging.getLogger().warning("Could not parse " + self._get_url(timestamp, url_key))
            encoded_string = html

        s3_path = f"{self.__url_to_domain(url_key)}/{timestamp}_{url_key.replace('/', '_')}"
        bucket = s3.Bucket(self.bucket_name)
        bucket.put_object(Key=s3_path, Body=encoded_string)

    def __upload_s3(self, timestamp: str, url_key: str, html: str) -> None:
        """
        Upload html file to a S3 bucket.

        :param timestamp: Timestamp from IA, used for filepath.
        :param url_key: Url_key from IA, used for filepath.
        :param html: Html to be uploaded.
        """
        url = self._get_url(timestamp, url_key)
        self._pool.apply_async(
            self.upload,
            [timestamp, url_key, html],
            callback=partial(self.success_callback, url_=url),
            error_callback=partial(self.error_callback, url_=url)
        )

    def success_callback(self, _, url_: str) -> None:
        logging.getLogger().info(f'Successfully uploaded {url_}')

    def error_callback(self, ex: Exception, url_: str) -> None:
        logging.getLogger().error(f"Exception occurred while uploading {url_}")
        logging.getLogger().exception(ex)
        if ex is MemoryError:
            print("############EXITING############")
            self._pool.shutdown()
            exit(1)

    def __getstate__(self):
        self_dict = self.__dict__.copy()
        del self_dict['_pool']
        return self_dict

    def __setstate__(self, state):
        self.__dict__.update(state)


def init_logging(log_file: Path) -> None:
    """
    Initialise Python logger

    :param log_file: Path to the log file.
    """
    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format='[%(asctime)s] {%(threadName)s:%(lineno)d} %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    # Log all levels to file
    logging.getLogger().setLevel(logging.INFO)

    # Set up logging to console
    console = logging.StreamHandler()
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    # console.setLevel(logging.DEBUG)

    # Add the handler to the root logger
    logging.getLogger().addHandler(console)


def main():
    parser = argparse.ArgumentParser(description='Fetch pages from the Internet Archive.')
    parser.add_argument("--data", "-d", help="Path to csv data formatted as (timestamp, url).", default="./data.csv")
    parser.add_argument("--log", "-l", help="Path to log file", default="./log.txt")
    parser.add_argument("--bucket_name", "-b", help="Amazon S3 Bucket name", default="975435234474-global-goals")
    parser.add_argument("--measure", help="Measure the performance using 500 requests", default=False)
    args = parser.parse_args()

    init_logging(Path(args.log))
    limit = 4
    if args.measure:
        request_count = 500
        scores = []
        repeat = 5

        for i in range(0, repeat):
            start = time.time()
            logging.getLogger().info(f"Started fetching {request_count} records.")
            PageFetcher(args.bucket_name, limit).fetch(Path(args.data), request_count)
            end = time.time()
            logging.getLogger().info(f"Finished fetching {request_count} records in {end - start} seconds.")
            print(end - start)
            scores.append(end - start)
            time.sleep(3)

        print(scores)
    else:
        start = time.time()
        logging.getLogger().info(f"Started fetching records.")
        PageFetcher(args.bucket_name, limit).fetch(Path(args.data))
        end = time.time()
        logging.getLogger().info(f"Finished fetching records in {end - start} seconds.")


if __name__ == '__main__':
    bashCommand = "systemd-notify --ready --status='Started fetching'"
    import subprocess
    process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    main()

    # Sleep to allow last uploads to finish
    sleep(10)


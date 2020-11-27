import csv
import json
import urllib.parse
from pathlib import Path
from typing import Tuple, Set
from urllib.parse import urlparse

import requests
from joblib import Parallel, delayed


class CDXRecord(object):
    def __init__(self, timestamp, url):
        self.timestamp = timestamp
        self.url = url

    def __hash__(self):
        return hash((self.timestamp, self.url))


class UrlFetcher:
    def __init__(self, domain: str, output_folder: Path = Path("./output/url_list/")):
        self.domain = domain
        output_folder.mkdir(parents=True, exist_ok=True)
        output_file = urllib.parse.quote(self.domain.replace('/', '_'))
        self.output_path = output_folder / Path(output_file)

    def __write(self, header: str, urls: Set[CDXRecord], resume_key: str):
        data = {'domain': self.domain, 'header': header, 'resume_key': resume_key,
                'urls': [page.__dict__ for page in urls]}

        # Output path exists --> Append mode
        with open(self.output_path, "w") as file:
            json.dump(data, file, indent=2)

    def __read(self) -> Tuple[str, Set[CDXRecord], str]:
        if not self.output_path.exists():
            raise FileNotFoundError(f"File {self.output_path} does not exist.")

        # Output path exists --> Append mode
        with open(self.output_path, "r") as json_file:
            saved_data = json.load(json_file)

            if self.domain != saved_data['domain']:
                raise ValueError("Saved domain is different from current domain")

            return saved_data['header'], \
                   set(CDXRecord(p['timestamp'], p['url']) for p in saved_data['urls']), \
                   saved_data['resume_key']

    def __checkpoint_available(self) -> bool:
        return self.output_path.exists()

    def __get_url_list(self):
        payload = {
            'url': self.domain,
            'matchType': 'prefix',
            'fl': 'urlkey,timestamp',
            'collapse': 'timestamp:4',
            'from': '2012',
            # 'showDupeCount': 'true',
            # 'showSkipCount': 'true',
            # 'limit': '4',
            'output': 'json',
            'showResumeKey': 'true',
        }
        filtered_urls = set()

        if self.__checkpoint_available():
            prev_header, prev_urls, prev_resume_key = self.__read()

            # Fetching has been completed
            if prev_resume_key == "finished":
                return prev_urls

            # Fetching can be resumed
            filtered_urls = prev_urls
            payload["resumeKey"] = prev_resume_key

        # Get response from url
        response = requests.get('http://web.archive.org/cdx/search/cdx', params=payload)
        response_list = response.json()

        # Extraction
        if not response_list:
            print(f"Nope: {self.domain}")
            return

        header = response_list[0]
        if not response_list[-2]:
            resume_key = response_list[-1][0]
            urls = response_list[1:-2]  # The before last one is always empty -> -2
        else:
            resume_key = "finished"
            urls = response_list[1:]

        # Replace org.example) with example.org
        domain_split = self.domain.split('.')
        domain_split.reverse()
        domain_key = ",".join(domain_split) + ')'

        for link, timestamp in urls:
            filtered_urls.add(CDXRecord(timestamp, link.replace(domain_key, self.domain)))

        # Write to file
        self.__write(header, filtered_urls, resume_key)

        return filtered_urls

    @staticmethod
    def __filter_html_urls(records: Set[CDXRecord]) -> Set[CDXRecord]:
        result = set()
        for r in records:
            url = urlparse(r.url).path
            included_extensions = ['.ae', '.aero', '.br', '.by', '.ca', '.cern', '.ch', '.com', '.cr', '.dk', '.es',
                                   '.et', '.eu', '.fi', '.fj', '.info', '.int', '.international', '.is', '.jm', '.mk',
                                   '.my', '.ne', '.net', '.org', '.pl', '.qa', '.ru', '.se',

                                   '.html', '.htm', '.php']
            if any([url[-5:].endswith(ext) for ext in included_extensions]) or '.' not in url[-5:]:
                result.add(r)

        return result

    def get_html_urls(self):
        links = self.__get_url_list()
        return self.__filter_html_urls(links)

    def write_to_csv(self, records: Set[CDXRecord]):
        with open(str(self.output_path) + '.csv', mode='w') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

            csv_writer.writerow(["timestamp", "url"])
            for record in records:
                csv_writer.writerow([record.timestamp, record.url])


def main():
    output_folder = Path("output")
    output_folder.mkdir(parents=True, exist_ok=True)
    """
    CDX returns record
    Record contains url, timestamp
    Url contains links
    """
    domains = [line.strip() for line in open("organisations.txt", 'r')]

    def csv_all(domain):
        try:
            uf = UrlFetcher(domain)
            uf.write_to_csv(uf.get_html_urls())
        except Exception as e:
            print(domain)
            print(e)

    Parallel(n_jobs=-1)(delayed(csv_all)(domain) for domain in domains)


if __name__ == "__main__":
    main()

import argparse
import logging
import subprocess
import sys
from pathlib import Path

from joblib import Parallel, delayed
from tqdm import tqdm

# Check Python version
if sys.version_info < (3, 7):
    sys.stdout.write("This script requires Python 3.7 or higher\n")
    sys.exit(1)


class LinkFetcher:
    @staticmethod
    def get_links(filepath: Path) -> list:
        """
        Get links using lynx.
        :param filepath: Html file to extract links from.
        :return: List of lynx.
        """
        command = """lynx \
             -dump \
             -force_html \
             -listonly \
             -unique_urls \
             -hiddenlinks=merge \
             -nonumbers \
             '{}' \
             | sed 's/#.*//' \
             | sort \
             | uniq""".format(filepath)

        output = subprocess.run(command,
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                check=True,
                                text=True)

        if output.stderr is not None:
            raise RuntimeError("Exception occurred while fetching links\nCommand:{}\nOutput:{}"
                               .format(command, output.stderr))

        # Command assumed to have succeeded
        links = str(output.stdout).split('\n')
        src = '/'.join(filepath.parts[5:7])
        combined = []
        for i in range(len(links)):
            combined.append('∞'.join([src, links[i]]))
        return combined

    @staticmethod
    def write_to_file(output_file: Path, data: list) -> None:
        """
        Write data to file.
        :param output_file: Path to output file.
        :param data: List to write.
        """
        with open(str(output_file), 'w') as f:
            for item in data:
                f.write("%s\n" % item)


def process_organisation(organisation_folder: Path, output_folder: Path, log_file: Path) -> list:
    """
    Extract all links for all html files of an individual organisation.
    :param organisation_folder: Path to the organisation' html files.
    :param output_folder: Output folder.
    :param log_file:
    :return failed: list of html pages that could not be processed
    """
    organisation_domain = organisation_folder.stem + ".".join(organisation_folder.suffixes)
    output_file = output_folder / Path(f"{organisation_domain}_links")

    all_links = []
    html_files = [inode for inode in organisation_folder.glob("*") if inode.is_file()]
    failed = []

    def process_single_page(html_file: Path) -> list:
        logging.basicConfig(
            filename=str(log_file),
            level=logging.INFO,
            format='[%(asctime)s] {%(threadName)s:%(lineno)d} %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        try:
            return LinkFetcher().get_links(html_file)
        except UnicodeDecodeError:
            logging.error(f"Unicode decoding error occurred while processing {html_file}")
            pass
        except Exception as e:
            logging.error(f"Exception occurred while processing {html_file}")
            logging.exception(e)

    results = Parallel(n_jobs=-1)(delayed(process_single_page)(html_file) for html_file in tqdm(html_files))
    for result in results:
        if result and result[0]:
            all_links.extend(result)
    LinkFetcher.write_to_file(output_file, data=all_links)

    logging.getLogger().info(f'Successfully written to file {output_file}')


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
    parser = argparse.ArgumentParser(description='Extract links from html pages.')
    parser.add_argument("--input_folder", "-i", help="Input folder containing organisations",
                        default="../output/html")
    parser.add_argument("--output_folder", help="Output folder to write results to", default="../output/lynx")
    parser.add_argument("--log", "-l", help="Path to log file", default="../output/log2.txt")
    args = parser.parse_args()
    Path(args.output_folder).mkdir(parents=True, exist_ok=True)

    init_logging(Path(args.log))

    organisation_folders = [inode for inode in Path(args.input_folder).glob("*") if inode.is_dir()]

    failed_file = Path("/home/aztec/output/failed.txt")

    all_failed = []

    for f in organisation_folders:
        process_organisation(f, Path(args.output_folder), Path(args.log))


if __name__ == "__main__":
    main()

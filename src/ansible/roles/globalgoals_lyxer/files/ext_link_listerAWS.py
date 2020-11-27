from pathlib import Path
from urllib.parse import urlparse
import pandas as pd
import argparse
import re


class ExtLinkLister():
    def __init__(self, source: str, targets_path: Path):
        """
        Retrieves external hyperlinks and stores these in csv file
        ready to be used in network analyses
        :param source:
        """
        self.source = source
        self.targets_path = targets_path
        self.no_link = []

    def list_ext_links(self, source_path: Path, output_path: Path):
        """
        Retrieves external hyperlinks and stores these in csv file
        ready to be used in network analyses.
        :param source_path: Path to input file
        :param output_path: Path to output file
        """
        if not source_path.exists():
            raise IOError("Given csv file does not exists")

        with open(str(source_path), 'r') as file:
            urls = [line.rstrip() for line in file]
        src_links, ext_links = self.__filter_links(urls)
        my_dict = self.__create_list(src_links, ext_links)

        self.__write_csv(my_dict, output_path)

    def __filter_links(self, urls: list):
        """
        Split source url into requested output parts
        :param urls: List with all complete IA urls
        :return: subset of urls split into source and destination url
        """
        prefix = "http://web.archive.org"
        domain = self.source[:-4]
        mail = "mailto"

        with open(str(self.targets_path), 'r') as file:
            targets = [line.rstrip() for line in file]
        l_index = []
        src_link = []
        ext_link = []

        for i in range(0, len(urls)):
            src = ([urls[i].split('∞', 1)[0]])
            ext = ([urls[i].split('∞', 1)[1]])
            if mail not in ext[0].lower():
                if prefix in ext[0]:
                    if domain not in ext[0]:
                        if any(target in ext[0] for target in targets):
                            if "WB_wombat" not in ext[0]:
                                src_link.append(src)
                                ext_link.append(ext)
        return src_link, ext_link

    def __create_list(self, org_src_links: list, org_ext_links: list):
        """
        Split source url into requested output parts
        :param org_src_links: List with urls of source website.
        :param org_ext_links: List with urls to external website.
        :return: List with source and destination organizations and timestamps
        """
        data = []
        for i in range(0, len(org_ext_links)):
            src_link = self.__split_source(org_src_links[i])
            ext_link = self.__split_url(org_ext_links[i])
            data.append([src_link[0], src_link[1], src_link[2], ext_link[0], ext_link[1]])
        return data

    def __split_source(self, url: str):
        """
        Split source url into requested output parts
        :param url: Url to external website.
        :return: Url parts
        """
        try:
            p = url[0].split('_')
            q = p[0]
            return [q.split('/')[0], q.split('/')[1], '/'.join(p[1:])]    # [q, p[1:-1]]??
        except Exception:
            print(url)
            self.no_link.append(url)

    def __split_url(self, url: str):
        """
        Split destination url into requested output parts
        :param url: Url to external website.
        :return: Url parts
        """
        try:
            p = urlparse(url[0])
            ia_link = ''.join([p.path, p.query])
            full_link = re.split(r'[\./: ][a-z]{3,6}: ?//', ia_link, maxsplit=1)[1]
            with open(str(self.targets_path), 'r') as file:
                targets = [line.rstrip() for line in file]

            for target in targets:
                if target in full_link:
                    t_org = target
            return [t_org, full_link]
        except Exception:
            print(url)
            self.no_link.append(url)

    def __write_csv(self, data: list, output_path: Path):
        """
        Write data to file.
        :param output_path: Path to output file.
        :param data: List to write.
        """
        df = pd.DataFrame(data)
        df.index.name = "index"
        df.rename(columns={0: "source", 1: "timestamp", 2: "src_link", 3: "target", 4: "full_link"}, inplace=True)
        df.to_csv(output_path)


def main():
    parser = argparse.ArgumentParser(description='Extract external links from csv')
    parser.add_argument("--input_data", "-i", help="Input folder containing organisations", default="../output/html")
    parser.add_argument("--input_folder", help="Input folder containing organisations", default="../output/lynx")
    parser.add_argument("--output_folder", help="Output folder to write results to", default="../output/dummy_data")
    args = parser.parse_args()
    Path(args.output_folder).mkdir(parents=True, exist_ok=True)

    targets_file = Path("organisations.txt")

    organisation_folders = [inode for inode in Path(args.input_data).glob("*") if inode.is_dir()]
    for org in organisation_folders:
        organisation_domain = org.stem + ".".join(org.suffixes)
        input_file = Path(args.input_folder) / f"{organisation_domain}_links"
        output_file = Path(args.output_folder) / f"{organisation_domain}_ext_links.csv"
        s = ExtLinkLister(organisation_domain, targets_file)
        s.list_ext_links(input_file, output_file)


if __name__ == "__main__":
    main()

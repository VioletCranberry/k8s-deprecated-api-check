import requests
import argparse
import logging
import sys
import re

from deepdiff import DeepDiff
from tabulate import tabulate
from glob import glob


# This class provides a deepDiff wrapper around two k8s API json specs
class K8sApiSpecDiff:

    def __init__(self, k8s_lesser_ver: str, k8s_greater_ver: str):
        """
        :param k8s_lesser_ver:  lesser  k8s version (e.g. 1.21)
        :param k8s_greater_ver: greater k8s version (e.g. 1.22)
        """
        self.k8s_api_spec_old = Utils.load_k8s_git_api_spec(
            k8s_lesser_ver)
        self.k8s_api_spec_new = Utils.load_k8s_git_api_spec(
            k8s_greater_ver)
        self.k8s_api_spec_key = "paths"

        self.verify_k8s_api_spec_key(self.k8s_api_spec_key)
        self.k8s_api_spec_diff = self.generate_k8s_api_spec_diff()

    def verify_k8s_api_spec_key(self, k8s_api_spec_key: str):
        """
        validate whether k8s OpenApi spec contains a key
        :param k8s_api_spec_key: schema key
        """
        logging.info(f"key [{k8s_api_spec_key}]: "
                     f"validating OpenApi Swagger JSON")

        if any(k8s_api_spec_key not in k8s_api_spec
               for k8s_api_spec in (
                       self.k8s_api_spec_old,
                       self.k8s_api_spec_new)):
            logging.fatal(f"key [{k8s_api_spec_key}] is missing "
                          f"in the kubernetes api specification")
            sys.exit(1)

    def generate_k8s_api_spec_diff(self):
        """
        generate DeepDiff between two k8s OpenApi specs
        :return: deepdiff.diff.DeepDiff object
        """
        logging.info(f"key [{self.k8s_api_spec_key}]: "
                     f"generating OpenApi Swagger JSON diff ")

        # ignore 'description' field as most frequently changed
        diff_path_excluded = [r"root\[.+?].+\['description']"]
        spec_diff = DeepDiff(
            self.k8s_api_spec_old.get(self.k8s_api_spec_key),
            self.k8s_api_spec_new.get(self.k8s_api_spec_key),
            exclude_regex_paths=diff_path_excluded,
            ignore_order=True, view="tree"
        )
        return spec_diff


# Provides parsing utilities for k8s_api_spec_diff attribute of K8sApiSpecDiff class
class PrettySpecDiff:

    def __init__(self, k8s_api_spec_diff: DeepDiff):
        """
        :param k8s_api_spec_diff: diff returned by K8sApiSpecDiff class
        """
        self.deep_diff_req_key = ["dictionary_item_removed",
                                  "dictionary_item_added"]

        self.k8s_api_spec_diff = k8s_api_spec_diff
        self.verify_diff_changes()

        self.k8s_api_paths_new = self.fetch_api_paths(
            self.deep_diff_req_key[1])
        self.k8s_api_paths_old = self.fetch_api_paths(
            self.deep_diff_req_key[0])

    def fetch_api_paths(self, diff_key: str):
        """
        extract kubernetes API paths from DeepDiff object,
        remove duplicates (if any) and sort the results
        :param diff_key: default deepdiff key
        :return: list of kubernetes APIs
        """
        api_diff_list = self.k8s_api_spec_diff.get(diff_key)
        k8s_api_paths = [api_item.path(output_format='list')[0]
                         for api_item in api_diff_list]

        k8s_api_paths = sorted(set(k8s_api_paths))
        logging.info(f"diff key [{diff_key}]: fetched "
                     f"{len(k8s_api_paths)} APIs")
        return k8s_api_paths

    def verify_diff_changes(self):
        """
        validate whether any changes between OpenApi specs exist
        """
        if any(diff_key not in self.k8s_api_spec_diff
               for diff_key in self.deep_diff_req_key):
            logging.fatal(f"no changes in OpenApi spec detected")
            sys.exit(1)


# This class provides utilities for working with kubernetes APIs
class ApisListParser:

    def __init__(self, k8s_api_paths_list: list):
        """
        :param k8s_api_paths_list: list of kubernetes APIs
        """
        self.k8s_api_paths_list = k8s_api_paths_list

        self.api_core_group = [api_path for api_path
                               in self.k8s_api_paths_list
                               if api_path.startswith("/api/v1")]

        self.api_named_group = [api_path for api_path
                                in self.k8s_api_paths_list
                                if api_path.startswith("/apis")]

    def filter_api_named_groups(self):
        """
        parse kubernetes named API groups by group name and version
        :return: sorted group names without duplicates
        """
        # match API paths of (/apis) group_name version
        # r"(?<=/apis/).+/.+\d$" is also a valid pattern
        # however not an entire group is usually removed
        # so we give user a hint that group is removed,
        # and it's better to migrate
        re_group_pattern = r"(?<=/apis/).+/.+\d"
        groups = [match.group() for api_path
                  in self.api_named_group
                  if (match := re.search(re_group_pattern, api_path))]
        groups = sorted(set(groups))
        logging.info(f"kubernetes named API groups: "
                     f"filtered {len(groups)} APIs")
        return groups

    def filter_api_core_groups(self):
        """
        parse kubernetes legacy API groups by group name and version
        :return: sorted group names without duplicates
        """
        # match API paths of (/api) version group_name (/)
        re_group_pattern = r"(?<=/api/).+?/.+?(?=/)"
        groups = [match.group() for api_path
                  in self.api_core_group
                  if (match := re.search(re_group_pattern, api_path))]
        groups = sorted(set(groups))
        logging.info(f"kubernetes legacy API groups: "
                     f"filtered {len(groups)} APIs")
        return groups


# This class provides utilities to track kubernetes APIs in files under directory
class YamlFileParser:

    def __init__(self, dir_path: str, api_list: list):
        """
        :param dir_path: directory of files
        :param api_list: list of kubernetes apis to compare against
        """
        self.dir_path = dir_path
        self.k8s_apis = api_list

        self.files_pattern = re.compile(r"(?<=apiVersion: ).+")
        for file in self.get_files_to_track():
            self.process_file(file)

    def get_files_to_track(self):
        """
        locate files recursively
        :return: list of file paths
        """
        tracked_files = []
        file_extensions = ("*.yaml", "*.yml", "*.tpl")
        for ext in file_extensions:
            _path = f"{self.dir_path}/**/{ext}"
            files = glob(_path, recursive=True)
            tracked_files.extend(files)
            logging.info(f"file extension [{ext}]: "
                         f"tracking {len(files)} files")
        tracked_files.sort()
        return tracked_files

    def search_apis_in_file(self, file_path: str):
        """
        locate all API resources in file
        :param file_path: path to file
        :return: all k8s apis in file
        """
        with open(file_path, "r") as tracked_file:
            apis = [match.group().strip("'").strip('"')
                    for line in tracked_file if
                    (match := self.files_pattern.search(line))]
            return apis

    def process_file(self, file_path: str):
        """
        search for all API resources in file and
        compare them against a list of k8s apis
        :param file_path: path to file
        """
        files_apis = self.search_apis_in_file(file_path)
        for api in files_apis:
            if api in self.k8s_apis:
                logging.warning(f"deprecated api "
                                f"[{api}] in "
                                f"file [{file_path}]")


class Utils:

    @staticmethod
    def load_k8s_git_api_spec(version: str):
        """
        Load kubernetes swagger OpenApi spec from GitHub
        :param version: Kubernetes version (e.g 1.22)
        :return: swagger OpenApi spec json
        """
        logging.info(f"fetching api spec for version {version}")

        release_ver = f"release-{version}"
        swagger_url = f"https://raw.githubusercontent.com/" \
                      f"kubernetes/kubernetes/{release_ver}" \
                      f"/api/openapi-spec/swagger.json"
        try:
            api_spec = requests.get(swagger_url)
            api_spec.raise_for_status()

            return api_spec.json()
        except requests.exceptions.RequestException as err:
            logging.fatal(f"error while fetching "
                          f"k8s api spec: {err}")
            sys.exit(1)
        except requests.exceptions.JSONDecodeError as err:
            logging.fatal(f"error while fetching "
                          f"k8s api spec: {err} - "
                          f"invalid json")
            sys.exit(1)


def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-lv', '--lesser_ver',
                        action='store',
                        type=str,
                        required=True,
                        help='lesser k8s versions (e.g. 1.21)')
    parser.add_argument('-gv', '--greater_ver',
                        action='store',
                        type=str,
                        required=True,
                        help='greater k8s versions (e.g. 1.22)')
    parser.add_argument('-pp', '--pretty_print',
                        action='store_true',
                        required=False,
                        help='print deprecated k8s API groups')
    parser.add_argument('-yp', '--yaml_path',
                        action='store',
                        type=str,
                        required=False,
                        help='path to directory to look for '
                             'deprecated APIs')
    parser.add_argument('-d', '--debug',
                        action='store_true',
                        required=False)
    return parser.parse_args()


def main():
    args = get_arguments()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - "
                               "%(levelname)s - "
                               "%(message)s")

    api_spec_diff = K8sApiSpecDiff(args.lesser_ver, args.greater_ver)
    api_spec_diff = PrettySpecDiff(api_spec_diff.k8s_api_spec_diff)

    api_list_parser = ApisListParser(api_spec_diff.k8s_api_paths_old)
    api_list = [*api_list_parser.filter_api_core_groups(),
                *api_list_parser.filter_api_named_groups()]

    if args.yaml_path:
        YamlFileParser(args.yaml_path, api_list)

    if args.pretty_print:
        print(tabulate({"Api Groups Deprecated": api_list},
                       headers="keys", tablefmt="pretty"))


if __name__ == "__main__":
    main()

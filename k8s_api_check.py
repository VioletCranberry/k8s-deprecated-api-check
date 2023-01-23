import requests
import argparse
import logging
import sys
import re

from deepdiff import DeepDiff
from difflib import SequenceMatcher
from glob import glob


def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-lv", "--lesser_ver",
                        action="store",
                        type=str,
                        required=True,
                        help="lesser k8s versions (e.g. 1.21)")
    parser.add_argument("-gv", "--greater_ver",
                        action="store",
                        type=str,
                        required=True,
                        help="greater k8s versions (e.g. 1.22)")
    parser.add_argument("-ext", "--file_extensions",
                        nargs="+",
                        help="list of file extensions to parse",
                        required=False)
    parser.add_argument("-yp", "--yaml_path",
                        action="store",
                        type=str,
                        required=False,
                        help="path to directory to look for "
                             "deprecated APIs")
    parser.add_argument("-d", "--debug",
                        action="store_true",
                        required=False)
    return parser.parse_args()


class GitUtils:

    @staticmethod
    def load_k8s_api_spec(version: str):
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


class K8sApiSpecDiff:

    def __init__(self, k8s_lesser_ver: str, k8s_greater_ver: str):
        """
        :param k8s_lesser_ver:  lesser  k8s version (e.g. 1.21)
        :param k8s_greater_ver: greater k8s version (e.g. 1.22)
        """
        self.k8s_api_spec_old = GitUtils.load_k8s_api_spec(
            k8s_lesser_ver)
        self.k8s_api_spec_new = GitUtils.load_k8s_api_spec(
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
        logging.debug(f"generated api spec diff: {spec_diff}")
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

        self.k8s_api_paths_added = self.fetch_api_paths(
            self.deep_diff_req_key[1])
        self.k8s_api_paths_removed = self.fetch_api_paths(
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
        logging.debug(f"kubernetes APIs: {k8s_api_paths}")
        return k8s_api_paths

    def verify_diff_changes(self):
        """
        validate whether any changes between OpenApi specs exist
        """
        if any(diff_key not in self.k8s_api_spec_diff
               for diff_key in self.deep_diff_req_key):
            logging.fatal(f"no changes in OpenApi spec detected")
            sys.exit(1)


# This class provides utilities for working with kubernetes named API groups
class NamedAPIListParser:

    def __init__(self, api_path_list: list):
        """
        :param api_path_list: list of kubernetes APIs
        """
        self.api_path_list = api_path_list
        self.api_list = [api_path for api_path in self.api_path_list
                         if api_path.startswith("/apis")]

        self.api_groups = self.filter_api_groups()
        self.api_resource_types = self.filter_api_resource_types()
        self.named_api_data = self.generate_filtered_api_list()

    def filter_api_groups(self):
        """
        filter list of api groups in form of /apis/GROUP/VERSION
        """
        re_pattern = r"(?<=/apis/).+/.+\d"  # /apis/GROUP/VERSION
        api_groups = [match.group() for api_path
                      in self.api_list
                      if (match := re.search(re_pattern, api_path))]
        api_groups = sorted(set(api_groups))
        logging.debug(f"named api groups: {api_groups}")
        logging.info(f"total kubernetes named API groups: "
                     f"{len(api_groups)} APIs")
        return api_groups

    def filter_api_resource_types(self):
        """
        filter list of api group resource types in form of /apis/GROUP/VERSION/RESOURCETYPE
        """
        excluded_patterns = ["namespace", "name", "watch", "create", "update"]
        api_resource_types = []
        for api in self.api_list:
            for group in self.api_groups:
                re_pattern = rf"(?<=/apis/){group}/\w+(?!=/)"  # /apis/GROUP/VERSION/RESOURCETYPE
                match = re.search(re_pattern, api)
                if match and not any(pattern in match.group()
                                     for pattern in excluded_patterns):
                    api_resource_types.append(match.group())
        api_resource_types = sorted(set(api_resource_types))
        logging.debug(f"named api resources: {api_resource_types}")
        logging.info(f"total kubernetes named API resource types: "
                     f"{len(api_resource_types)} resources")
        return api_resource_types

    def generate_filtered_api_list(self):
        """
        generate list of dictionaries of the following format:
        [{'api_group': 'admissionregistration.k8s.io/v1beta1',
         'api_resource_types': ['mutatingwebhookconfigurations',
                                'validatingwebhookconfigurations']},
         {'api_group': 'apiextensions.k8s.io/v1beta1',
         'api_resource_types': ['customresourcedefinitions']}...]
        """
        filtered_list = []
        for api_group in self.api_groups:
            api_resource_types = [api_resource.split("/")[-1] for api_resource
                                  in self.api_resource_types
                                  if api_group in api_resource]
            filtered_list.append({"api_group": api_group,
                                  "api_resource_types": api_resource_types
                                  })
        logging.info(f"api list: {filtered_list}")
        return filtered_list


def search_api_groups_in_file(file_path: str):
    """
    locate all API groups in file
    :param file_path: path to file
    :return: all k8s api groups in file
    """
    re_pattern = re.compile(r"(?<=apiVersion: ).+")
    with open(file_path, "r") as tracked_file:
        groups = [match.group().strip("'").strip('"')
                  for line in tracked_file if
                  (match := re_pattern.search(line))]
        return groups


def search_api_resources_in_file(file_path: str):
    """
    locate all API kinds in file
    :param file_path: path to file
    :return: all k8s api kinds in file
    """
    re_pattern = re.compile(r"(?<=kind: )\w+")
    with open(file_path, "r") as tracked_file:
        resources = [match.group().strip("'").strip('"')
                     for line in tracked_file if
                     (match := re_pattern.search(line))]
        return resources


def is_strings_similar(str1: str, str2: str, threshold: float = 0.8):
    """
    api kind is singular while definition of RESOURCETYPE under
    /apis/GROUP/VERSION/RESOURCETYPE is plural: check strings equality
    based on the longest contiguous matching subsequence.
    """
    return SequenceMatcher(a=str1, b=str2).ratio() > threshold


# This class provides utilities to track kubernetes APIs in files under directory
class YamlFileParser:

    def __init__(self, dir_path: str, file_extensions: list, api_list: list):
        """
        :param dir_path: directory of files
        :param api_list: list of kubernetes apis to compare against
        """
        self.dir_path = dir_path
        self.file_extensions = file_extensions
        self.k8s_apis = api_list
        self.deprecated = False

        for file_path in self.get_files_to_track():
            deprecated_apis = self.get_deprecated_api_groups(file_path)
            if deprecated_apis:
                self.deprecated = True
                for api in deprecated_apis:
                    deprecated_kinds = self.get_deprecated_api_kinds(
                        file_path, api)
                    if deprecated_kinds:
                        self.deprecated = True

        if self.deprecated:
            sys.exit(1)

    def get_files_to_track(self):
        """
        locate files recursively
        :return: list of file paths
        """
        tracked_files = []
        file_extensions = set(self.file_extensions)
        for ext in file_extensions:
            _path = f"{self.dir_path}/**/{ext}"
            files = glob(_path, recursive=True)
            tracked_files.extend(files)
            logging.info(f"file extension [{ext}]: "
                         f"tracking {len(files)} files")
        tracked_files.sort()
        logging.debug(f"files: {tracked_files}")
        return tracked_files

    def get_deprecated_api_groups(self, file_path: str):
        """
        get deprecated API groups in file
        :param: file_path: file path
        """
        api_groups = [api["api_group"] for api in self.k8s_apis]
        deprecated = []
        for api in search_api_groups_in_file(file_path):
            if api in api_groups:
                logging.debug(f"deprecated api group "
                              f"[{api}] in file [{file_path}]")
                deprecated.append(api)
        return deprecated

    def get_deprecated_api_kinds(self, file_path: str, resource_group: str):
        """
        get deprecated API kinds in file based on API group
        :param: file_path: file path
        :param: resource_group: api group
        """
        api_group_data = next((item for item in self.k8s_apis
                               if item["api_group"] == resource_group), None)
        deprecated = []
        for api_kind in search_api_resources_in_file(file_path):
            for api_resource in api_group_data["api_resource_types"]:
                if is_strings_similar(api_kind.lower(), api_resource):
                    logging.warning(f"deprecated api kind [{api_kind}] "
                                    f"for deprecated api group [{resource_group}] in "
                                    f"file [{file_path}]")
                    deprecated.append(api_kind)
        return deprecated


def main():
    args = get_arguments()
    args.file_extensions = args.file_extensions if args.file_extensions else ["*.yaml", "*.yml", "*.tpl"]
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        format="%(asctime)s - "
                               "%(name)s - "
                               "%(levelname)s - "
                               "%(message)s")

    api_spec_diff = K8sApiSpecDiff(args.lesser_ver, args.greater_ver)
    api_spec_diff = PrettySpecDiff(api_spec_diff.k8s_api_spec_diff)

    api_list_removed = NamedAPIListParser(
        api_spec_diff.k8s_api_paths_removed)

    if args.yaml_path:
        YamlFileParser(args.yaml_path, args.file_extensions,
                       api_list_removed.named_api_data)


if __name__ == "__main__":
    main()

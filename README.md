### Problem:

Kubernetes is being developed and each version can deprecate some API groups that we need to track. 

Current open source tools maintain their own lists of deprecated API groups. We need to mitigate this self-maintenance human factor of these tools (as we really don’t know how devs are getting data, and why devs can’t do it automatically and within the script). We would like to avoid raising PRs for every missing component under hardcoded APIs of these tools. 

We need to iterate through all files, while current open source tools cannot parse `*.tpl` templates of helm charts and require `*.yaml` manifests to be generated ahead.


### Solution:

Kubernetes team maintains public OpenAPI specification and updates it after each release. We can simply compare JSON between two different kubernetes versions and look for changes. Walking through files and looking for matches if needed, without any need to connect to the cluster.
Example:
1. https://raw.githubusercontent.com/kubernetes/kubernetes/release-1.21/api/openapi-spec/swagger.json 
2. https://raw.githubusercontent.com/kubernetes/kubernetes/release-1.22/api/openapi-spec/swagger.json

### Installation (python 3.8+):
```
 cd scripts/k8s-api-check
 pip install -r requirements.txt
```

### Examples:
```

❯ python3 k8s_api_check.py --help                                                                 
usage: k8s_api_check.py [-h] -lv LESSER_VER -gv GREATER_VER [-ext FILE_EXTENSIONS [FILE_EXTENSIONS ...]] [-pp] [-yp YAML_PATH] [-d]

optional arguments:
  -h, --help            show this help message and exit
  -lv LESSER_VER, --lesser_ver LESSER_VER
                        lesser k8s versions (e.g. 1.21)
  -gv GREATER_VER, --greater_ver GREATER_VER
                        greater k8s versions (e.g. 1.22)
  -ext FILE_EXTENSIONS [FILE_EXTENSIONS ...], --file_extensions FILE_EXTENSIONS [FILE_EXTENSIONS ...]
                        list of file extensions to parse
  -pp, --pretty_print   print deprecated k8s API groups
  -yp YAML_PATH, --yaml_path YAML_PATH
                        path to directory to look for deprecated APIs
  -d, --debug


```

```
❯ python3 k8s_api_check.py -lv 1.21 -gv 1.22 -pp                                                  
2023-01-21 15:34:44,653 - INFO - fetching api spec for version 1.21
2023-01-21 15:34:44,816 - INFO - fetching api spec for version 1.22
2023-01-21 15:34:44,968 - INFO - key [paths]: validating OpenApi Swagger JSON
2023-01-21 15:34:44,969 - INFO - key [paths]: generating OpenApi Swagger JSON diff 
2023-01-21 15:34:46,185 - INFO - diff key [dictionary_item_added]: fetched 99 APIs
2023-01-21 15:34:46,185 - INFO - diff key [dictionary_item_removed]: fetched 105 APIs
2023-01-21 15:34:46,186 - INFO - kubernetes legacy API groups: filtered 0 APIs
2023-01-21 15:34:46,186 - INFO - kubernetes named API groups: filtered 12 APIs
+--------------------------------------+
|        Api Groups Deprecated         |
+--------------------------------------+
| admissionregistration.k8s.io/v1beta1 |
|     apiextensions.k8s.io/v1beta1     |
|    apiregistration.k8s.io/v1beta1    |
|    authentication.k8s.io/v1beta1     |
|     authorization.k8s.io/v1beta1     |
|     certificates.k8s.io/v1beta1      |
|     coordination.k8s.io/v1beta1      |
|          extensions/v1beta1          |
|      networking.k8s.io/v1beta1       |
|  rbac.authorization.k8s.io/v1beta1   |
|      scheduling.k8s.io/v1beta1       |
|        storage.k8s.io/v1beta1        |
+--------------------------------------+

```

```
❯ python3 k8s_api_check.py -lv 1.21 -gv 1.22 -yp ../../ --file_extensions '*.tpl' '*.yaml' '*.yml'
2023-01-21 15:33:56,924 - INFO - fetching api spec for version 1.21
2023-01-21 15:33:57,271 - INFO - fetching api spec for version 1.22
2023-01-21 15:33:57,621 - INFO - key [paths]: validating OpenApi Swagger JSON
2023-01-21 15:33:57,621 - INFO - key [paths]: generating OpenApi Swagger JSON diff 
2023-01-21 15:33:58,841 - INFO - diff key [dictionary_item_added]: fetched 99 APIs
2023-01-21 15:33:58,841 - INFO - diff key [dictionary_item_removed]: fetched 105 APIs
2023-01-21 15:33:58,841 - INFO - kubernetes legacy API groups: filtered 0 APIs
2023-01-21 15:33:58,842 - INFO - kubernetes named API groups: filtered 12 APIs
2023-01-21 15:33:59,174 - INFO - file extension [*.yml]: tracking 1 files
2023-01-21 15:33:59,391 - INFO - file extension [*.tpl]: tracking 16 files
2023-01-21 15:33:59,610 - INFO - file extension [*.yaml]: tracking 5623 files
2023-01-21 15:33:59,785 - WARNING - deprecated api [apiextensions.k8s.io/v1beta1] in file [../../elastic/base/apmservers.apm.k8s.elastic.co-customresourcedefinition.yaml]
2023-01-21 15:33:59,785 - WARNING - deprecated api [apiextensions.k8s.io/v1beta1] in file [../../elastic/base/beats.beat.k8s.elastic.co-customresourcedefinition.yaml]
...
❯ echo $?
1
```

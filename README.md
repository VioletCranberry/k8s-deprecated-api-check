### Description:

The only tool that:
1. generates a list of ALL deprecated api versions
2. maps deprecated api kinds to deprecated api groups automatically
3. written in Python which is easier to understand and expand
4. does not require self-maintaining a list of deprecated apis
5. does not hardcode evaluation rules
6. supports configurable types of file extensions (.tpl, .yml, .yaml, whatever else)
7. does not require cluster connection


### Installation (python 3.8+):
```
 cd scripts/k8s-api-check
 pip install -r requirements.txt
```

### Examples:
```

❯ python3 k8s_api_check.py --help
usage: k8s_api_check.py [-h] -lv LESSER_VER -gv GREATER_VER [-ext FILE_EXTENSIONS [FILE_EXTENSIONS ...]] [-yp YAML_PATH] [-d]

optional arguments:
  -h, --help            show this help message and exit
  -lv LESSER_VER, --lesser_ver LESSER_VER
                        lesser k8s versions (e.g. 1.21)
  -gv GREATER_VER, --greater_ver GREATER_VER
                        greater k8s versions (e.g. 1.22)
  -ext FILE_EXTENSIONS [FILE_EXTENSIONS ...], --file_extensions FILE_EXTENSIONS [FILE_EXTENSIONS ...]
                        list of file extensions to parse
  -yp YAML_PATH, --yaml_path YAML_PATH
                        path to directory to look for deprecated APIs
  -d, --debug

```

```
❯ python3 k8s_api_check.py -lv 1.21 -gv 1.22
2023-01-22 21:46:50,856 - root - INFO - fetching api spec for version 1.21
2023-01-22 21:46:51,029 - root - INFO - fetching api spec for version 1.22
2023-01-22 21:46:51,175 - root - INFO - key [paths]: validating OpenApi Swagger JSON
2023-01-22 21:46:51,175 - root - INFO - key [paths]: generating OpenApi Swagger JSON diff
2023-01-22 21:46:52,310 - root - INFO - diff key [dictionary_item_added]: fetched 99 APIs
2023-01-22 21:46:52,310 - root - INFO - diff key [dictionary_item_removed]: fetched 105 APIs
2023-01-22 21:46:52,311 - root - INFO - total kubernetes named API groups: 12 APIs
2023-01-22 21:46:52,313 - root - INFO - total kubernetes named API resource types: 22 resources
2023-01-22 21:46:52,313 - root - INFO - api list: [
{'api_group': 'admissionregistration.k8s.io/v1beta1', 'api_resource_types': ['mutatingwebhookconfigurations', 'validatingwebhookconfigurations']},
{'api_group': 'apiextensions.k8s.io/v1beta1', 'api_resource_types': ['customresourcedefinitions']},
{'api_group': 'apiregistration.k8s.io/v1beta1', 'api_resource_types': ['apiservices']},
{'api_group': 'authentication.k8s.io/v1beta1', 'api_resource_types': ['tokenreviews']},
{'api_group': 'authorization.k8s.io/v1beta1', 'api_resource_types': ['selfsubjectaccessreviews', 'selfsubjectrulesreviews', 'subjectaccessreviews', 'clusterrolebindings', 'clusterroles', 'rolebindings', 'roles']},
{'api_group': 'certificates.k8s.io/v1beta1', 'api_resource_types': ['certificatesigningrequests']},
{'api_group': 'coordination.k8s.io/v1beta1', 'api_resource_types': ['leases']},
{'api_group': 'extensions/v1beta1', 'api_resource_types': ['ingresses']},
{'api_group': 'networking.k8s.io/v1beta1', 'api_resource_types': ['ingressclasses', 'ingresses']},
{'api_group': 'rbac.authorization.k8s.io/v1beta1', 'api_resource_types': ['clusterrolebindings', 'clusterroles', 'rolebindings', 'roles']},
{'api_group': 'scheduling.k8s.io/v1beta1', 'api_resource_types': ['priorityclasses']},
{'api_group': 'storage.k8s.io/v1beta1', 'api_resource_types': ['csidrivers', 'csinodes', 'storageclasses', 'volumeattachments']}
]
❯ echo $?
0
```

```
❯ python3 k8s_api_check.py -lv 1.21 -gv 1.22 -yp ../../ --file_extensions '*.tpl' '*.yaml' '*.yml'
2023-01-22 21:46:42,836 - root - INFO - fetching api spec for version 1.21
2023-01-22 21:46:43,416 - root - INFO - fetching api spec for version 1.22
2023-01-22 21:46:43,960 - root - INFO - key [paths]: validating OpenApi Swagger JSON
2023-01-22 21:46:43,960 - root - INFO - key [paths]: generating OpenApi Swagger JSON diff
2023-01-22 21:46:45,099 - root - INFO - diff key [dictionary_item_added]: fetched 99 APIs
2023-01-22 21:46:45,099 - root - INFO - diff key [dictionary_item_removed]: fetched 105 APIs
2023-01-22 21:46:45,100 - root - INFO - total kubernetes named API groups: 12 APIs
2023-01-22 21:46:45,102 - root - INFO - total kubernetes named API resource types: 22 resources
2023-01-22 21:46:45,102 - root - INFO - api list: [{'api_group': 'admissionregistration.k8s.io/v1beta1', 'api_resource_types': ['mutatingwebhookconfigurations', 'validatingwebhookconfigurations']}, {'api_group': 'apiextensions.k8s.io/v1beta1', 'api_resource_types': ['customresourcedefinitions']}, {'api_group': 'apiregistration.k8s.io/v1beta1', 'api_resource_types': ['apiservices']}, {'api_group': 'authentication.k8s.io/v1beta1', 'api_resource_types': ['tokenreviews']}, {'api_group': 'authorization.k8s.io/v1beta1', 'api_resource_types': ['selfsubjectaccessreviews', 'selfsubjectrulesreviews', 'subjectaccessreviews', 'clusterrolebindings', 'clusterroles', 'rolebindings', 'roles']}, {'api_group': 'certificates.k8s.io/v1beta1', 'api_resource_types': ['certificatesigningrequests']}, {'api_group': 'coordination.k8s.io/v1beta1', 'api_resource_types': ['leases']}, {'api_group': 'extensions/v1beta1', 'api_resource_types': ['ingresses']}, {'api_group': 'networking.k8s.io/v1beta1', 'api_resource_types': ['ingressclasses', 'ingresses']}, {'api_group': 'rbac.authorization.k8s.io/v1beta1', 'api_resource_types': ['clusterrolebindings', 'clusterroles', 'rolebindings', 'roles']}, {'api_group': 'scheduling.k8s.io/v1beta1', 'api_resource_types': ['priorityclasses']}, {'api_group': 'storage.k8s.io/v1beta1', 'api_resource_types': ['csidrivers', 'csinodes', 'storageclasses', 'volumeattachments']}]
2023-01-22 21:46:45,316 - root - INFO - file extension [*.tpl]: tracking 16 files
2023-01-22 21:46:45,514 - root - INFO - file extension [*.yml]: tracking 1 files
2023-01-22 21:46:45,712 - root - INFO - file extension [*.yaml]: tracking 5623 files
2023-01-22 21:46:45,887 - root - WARNING - deprecated api kind [CustomResourceDefinition] for deprecated api group [apiextensions.k8s.io/v1beta1] in file [../../elastic/base/apmservers.apm.k8s.elastic.co-customresourcedefinition.yaml]
2023-01-22 21:46:45,888 - root - WARNING - deprecated api kind [CustomResourceDefinition] for deprecated api group [apiextensions.k8s.io/v1beta1] in file [../../elastic/base/beats.beat.k8s.elastic.co-customresourcedefinition.yaml]
2023-01-22 21:46:45,889 - root - WARNING - deprecated api kind [ValidatingWebhookConfiguration] for deprecated api group [admissionregistration.k8s.io/v1beta1] in file [../../elastic/base/elastic-webhook.k8s.elastic.co-validatingwebhookconfiguration.yaml]
...
❯ echo $?
1
```

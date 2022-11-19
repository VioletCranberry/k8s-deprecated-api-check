### Problems:

Kubernetes is being developed and each version can deprecate some API groups that we need to track. 

Current open source tools maintain their own lists of deprecated API groups. 
We need to mitigate this self-maintenance human factor of these tools (as we really don’t know how devs are getting data, and why devs can’t do it automatically and within the script). 
We would like to avoid raising PRs for every missing component under hardcoded APIs of these tools. 

We need to iterate through all files, while current open source tools cannot distinguish between tpl templates of helm charts or yaml manifests if walking through directories recursively. 


### Solution:

Kubernetes team maintains public OpenAPI specification and updates it after each release. 
We can simply compare JSON between two different kubernetes versions and look for changes. 
Walking through files and looking for matches if needed, without any need to connect to the cluster. 

Example: https://raw.githubusercontent.com/kubernetes/kubernetes/release-1.22/api/openapi-spec/swagger.json

### Installation (python 3.8+):
```
 pip install -r requirements.txt
```

### Examples:
```

❯ python3 k8s_api_check.py --help
usage: better.py [-h] -lv LESSER_VER -gv GREATER_VER [-pp] [-yp YAML_PATH] [-d]

optional arguments:
  -h, --help            show this help message and exit
  -lv LESSER_VER, --lesser_ver LESSER_VER
                        lesser k8s versions (e.g. 1.21)
  -gv GREATER_VER, --greater_ver GREATER_VER
                        greater k8s versions (e.g. 1.22)
  -pp, --pretty_print   print deprecated k8s API groups
  -yp YAML_PATH, --yaml_path YAML_PATH
                        path to directory to look for deprecated APIs
  -d, --debug

```

```
❯ python3 k8s_api_check.py -lv 1.21 -gv 1.22 -pp
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
❯  python3 k8s_api_check.py -lv 1.21 -gv 1.22 -yp ../../
2022-08-19 12:33:13,607 WARNING deprecated api [extensions/v1beta1] in file [../../ingress.yaml]
2022-08-19 12:33:13,618 WARNING deprecated api [apiextensions.k8s.io/v1beta1] in file [../../customresourcedefinition.yaml]
...
```

# Drain3
## Introduction

Drain is an online log parser that can parse logs into structured events in a streaming and timely manner. It employs a parse tree with fixed depth to guide the log group search process, which effectively avoids constructing a very deep and unbalanced tree.

Read more information about Drain from the following papers:

Pinjia He, Jieming Zhu, Zibin Zheng, and Michael R. Lyu. Drain: An Online Log Parsing Approach with Fixed Depth Tree, Proceedings of the 24th International Conference on Web Services (ICWS), 2017.


This code is upgrade of original Drain code from Python 2.7 to Python 3.6 or later and fixs for some minor bugs:
https://github.com/logpai/logparser/blob/master/logparser/Drain

### The main new features in this repository are:
- **persistence** - save drain state to Kafka or file
- **masking** - mask classified information so it will be hide in the template (for example: IP address)

### The input of Drain is a raw log and the output is a JSON with the following fields:
- `cluster_id`: the id of the cluster that the raw_log belong to, for example, A0008
- `cluster_count`: the total clusters seen till now
- `template_mined`: the last template of the above cluster_id

- templates can be changed, for example:
input: aa aa aa
output: @@{"cluster_id": "A0012", "cluster_count": 12, "template_mined": "aa aa aa"}
input: aa aa ab
output:  @@{"cluster_id":"A0012", "cluster_count": 12, "template_mined": "aa aa <\*>"}

## Masking
- masking - to use the masking please add the regular expression and the mask to the mask_conf.py file.
The masking list get a dict with the fields: 'regex_pattern', 'mask_with'
An example for masking IP address:

mask_conf.py:
 masking = [\
    {'regex_pattern':"((?<=[^A-Za-z0-9])|^)(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})((?=[^A-Za-z0-9])|$)",  'mask_with': "IP"}
]

The raw log: 
> my IP is 12.12.12.12
The output: 
{"cluster_id": "A0015", "cluster_count": 16, "template_mined": "my ip is <IP>"}

if the file mask_conf.py is empty, no mask is used


## Persistent:
The persistent method saves a snapshot of the drain3 state and can load it after restart.
The darain3 states include all the templates and the clusters_id that was identified till the snapshot time.
In the snapshot there is also the occurrence of any cluster_id.
An example of a snapshot:
{"clusters": [{"cluster_id": "A0001", "log_template_tokens": ["aa", "aa", "<\*>"], "py/object": "drain3_core.LogCluster", "size": 2}, {"cluster_id": "A0002", "log_template_tokens": ["My", "IP", "is", "<IP>"], "py/object": "drain3_core.LogCluster", "size": 1}]...

In this snapshot you can see a two clusters_id with the templates:
["aa", "aa", "<\*>"] - occur 2
["My", "IP", "is", "<IP>"] - occur 1


The snapshot is created in any of the following events:
- new_template - in any new template
- update_template - in any update of a template
- periodic - after X ("snapshot_interval_minutes") from teh last snapshot (this parameter is in the app_cong.py)


Drain3 supports two persistence methods:

- **Kafka** - The snapshot is saved in a topic that should be used only for the snapshots - the last message in this topic is the last snapshot that will be uploaded after restart.
For Kafka persistence, you need to provide: `topic_name` and `server_name`. see Kafka_persist example below

- **File** - The snapshot is saved in a file that restore only the last message, (during the persistent it creates a tmp file in the path directory)
For File persistence, you need to provide: `file_name`, `path_name`. see File_persist example below

## Examples

#example - ONLINE DRAIN 
connect to Drain using :
This is an example of using Drain with stdin - stdout
```python

import sys
import os
from drain3_main import LogParserMain

class LogParserOnline():
    def __init__(self, persistance_type, path_or_server, file_or_topic):
        self.log_parser = LogParserMain(persistance_type, path_or_server, file_or_topic)

    def start(self):
        self.log_parser.start()
        print("Ready")
        while True:
            log_line = input()
            cluster_json = self.log_parser.add_log_line(log_line)
            print(cluster_json)

```



#example KAFKA_persist
File persist call the in-memory drain example with KAFKA persist.
There is an option to read the topc/server from ENV varibels/
The defaults parameters are: server_name: " "localhost:9092", topic_name: "a"


```python
import os
from drain3_online import LogParserOnline

env_kafka_servers = "decorus_kafka_servers"
env_tenant_id = "decorus_tenant_id"
topic_name_prefix = "template_miner_snapshot_"

servers = os.environ.get(env_kafka_servers, "localhost:9092")
server_list = servers.split(",")
tenant_id = os.environ.get(env_tenant_id, "a")

topic = topic_name_prefix + tenant_id
print("Kafka servers = " + str(server_list) + "\nKafka topic = " + str(topic))
log_parser = LogParserOnline("KAFKA", server_list, topic) 
log_parser.start()

```

#Example File_persist
File persist call the in-memory drain example with file persist.
 The defaults parameters are:  path: "./examples/", file_name: "snapshot.txt"


```python 

import os
from drain3_online import LogParserOnline

persist_file_name = "snapshot.txt"
persist_path = "./examples"

log_parser = LogParserOnline("FILE", persist_path, persist_file_name) 
log_parser.start()

```



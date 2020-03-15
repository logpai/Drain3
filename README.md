# Drain3
## Introduction

Drain3 is an online log parser that can parse logs into structured events in a streaming and timely manner. It employs a parse tree with fixed depth to guide the log group search process, which effectively avoids constructing a very deep and unbalanced tree.

Drain3 continuously learns and automatically generates "log templates" from raw log entries. As an example for the input:

```
> 10:00 connect to 10.0.0.1
> 10:10 connect to 10.0.0.2
> 10:20 connect to 10.0.0.3
> 10:30 Hex number 0xDEADBEAF
> 10:30 Hex number 0x10000
> 10:40 executed cmd "print"
> 10:50 executed cmd "sleep"
```
Drain3 generates the following templates:

```
> {"cluster_id": "A0001", "cluster_count": 1, "template_mined": "<NUM>:<NUM> connect to <IP>"}
> {"cluster_id": "A0002", "cluster_count": 2, "template_mined": "<NUM>:<NUM> Hex number <HEX>"}
> {"cluster_id": "A0003", "cluster_count": 3, "template_mined": "<NUM>:<NUM> executed cmd <CMD>"}
```

Read more information about Drain from the following paper:

- Pinjia He, Jieming Zhu, Zibin Zheng, and Michael R. Lyu. Drain: An Online Log Parsing Approach with Fixed Depth Tree, Proceedings of the 24th International Conference on Web Services (ICWS), 2017.


This code is upgrade of original Drain code from Python 2.7 to Python 3.6 or later with fixes of some bugs and additional features:

>Note: *Original code can be found here: [https://github.com/logpai/logparser/blob/master/logparser/Drain](https://github.com/logpai/logparser/blob/master/logparser/Drain)*



### The main new features in this repository are:
- **persistence** - save drain state to Kafka or file
- **masking** - mask classified information so it will be hide in the template (for example: IP address)

### The input for Drain3 are **raw log** entries and the output is JSON with the following fields:
- `cluster_id`: id of the cluster that the raw_log belong to, for example, A0008
- `cluster_count`: total clusters instances count seen till now
- `template_mined`: the last template of above cluster_id

- templates are changed over time based on input, for example:

> input: aa aa aa
>
> output: @@{"cluster_id": "A0012", "cluster_count": 12, "template_mined": "aa aa aa"}
>
> input: aa aa ab
>
> output:  @@{"cluster_id":"A0012", "cluster_count": 12, "template_mined": "aa aa <\*>"}


**Explanation:** *Drain3 learned that the third token is a parameter*

## Configuration

Drain3 is configured using [configparser](https://docs.python.org/3.4/library/configparser.html) using file `drain3.ini` available parameters are:
- `[DEFAULT]/snapshot_poll_timeout_sec` - maximum timeout for restoring snapshot from Kafka (default 60)
- `[DEFAULT]/sim_th` - recognition threshold (default 0.4)
- `[DEFAULT]/masking` - parameters masking - in json format (default "")
- `[DEFAULT]/print_prefix` - prefix added to examples print commands (default "@@")
- `[DEFAULT]/snapshot_interval_minutes` - interval for new snapshots (default 1)

## Masking

This feature allows masking of specific parameters in the template to specific keywords. Use List of regular expression  
dictionaries in the configuration file with the format {'regex_pattern', 'mask_with'} to set custom masking

In order to mask IP address created the file `drain3.ini` :

```
[DEFAULT]
masking = [
    {"regex_pattern":"((?<=[^A-Za-z0-9])|^)(\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3})((?=[^A-Za-z0-9])|$)", "mask_with": "IP"},
    ]
```

Now, Drain3 recognizes IP addresses in templates, for example with input such as:
>  `IP is 12.12.12.12`
Drain3 output output:
> `{"cluster_id": "A0015", "cluster_count": 16, "template_mined": "my ip is <IP>"}`

Note: template parameters that do not match custom masking are output as <*>

## Persistent:
The persistent feature saves and loads a snapshot of drain3 state in json format. This feature adds restart resiliency
to drain allowing continuation of activity and knowledge cross restarts.

Drain3 state includes all the templates and clusters_id that were identified up until snapshot time.

The snapshot also persist number of occurrences per cluster, and the cluster_id.

An example of a snapshot:
```
{"clusters": [{"cluster_id": "A0001", "log_template_tokens": `["aa", "aa", "<\*>"]`, "py/object": "drain3_core.LogCluster", "size": 2}, {"cluster_id": "A0002", "log_template_tokens": `["My", "IP", "is", "<IP>"]`, "py/object": "drain3_core.LogCluster", "size": 1}]...
```

This example snapshot persist two clusters_id with the templates:

> `["aa", "aa", "<\*>"]` - occurs twice
>
>  `["My", "IP", "is", "<IP>"]` - occurs once

Snapshots are created in the following events:

- new_template - in any new template
- update_template - in any update of a template
- periodic - after X ("snapshot_interval_minutes") from teh last snapshot (this parameter is in the app_cong.py)


Drain3 supports two persistence methods:

- **Kafka** - The snapshot is saved in a topic used only for snapshots - the last message in this topic is the last snapshot that will be uploaded after restart.
For Kafka persistence, you need to provide: `topic_name` and `server_name`. see Kafka_persist example below

- **File** - The snapshot is saved in a file that restores only last message, (during the persistent it creates a tmp file in the path directory)
For File persistence, you need to provide: `file_name`, `path_name`. see File_persist example below

## Installation

drain3 is available from pypi. To install use `pip`:

```pip3 install drain3```


## Examples

### Example File_persist

Uses Drain from stdin/out and persist to a snapshot to file.

To experience with the example execute :

```
python examples/example_drain_online_with_file_persist.py
```

now enter several log lines using the command line. For example enter:

```
10:00 test1
10:10 test2
10:20 test2
10:30 test3
10:40 test1
```

stop execution (using ^c) 
Use `cat snapshot.txt` to explore drain snapshot file that was created.

### example KAFKA_persist

Uses Drain from stdin/out and persist to kafka.

To experience with the example execute :

```
python examples/example_drain_online_with_kafka_persist.py
```

follow same usage as in File_persist example

Use kafka tools to explore the snapshot in the topic `topic_demo_tenant_id`

### example masking

To experience with the example execute :
(Note: *an example drain3.ini file exists in the `examples` folder*)

```
cd examples
python example_drain_online_with_file_persist.py
```

now enter several log lines using the command line. For example enter:

```
10:00 connect to 10.0.0.1
10:10 connect to 10.0.0.2
10:20 connect to 10.0.0.3
10:30 Hex number 0xDEADBEAF
10:30 Hex number 0x10000
10:40 executed cmd "print"
10:50 executed cmd "sleep"

```








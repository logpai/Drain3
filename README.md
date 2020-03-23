# Drain3
## Introduction

Drain3 is an online log template miner that can extract templates (clusters) from a stream of log messages
in a timely manner. It employs a parse tree with fixed depth to guide the log group search process, 
which effectively avoids constructing a very deep and unbalanced tree.

Drain3 continuously learns on-the-fly and automatically extracts "log templates" from raw log entries. 

#### Example:
 
For the input:

```
connected to 10.0.0.1
connected to 10.0.0.2
connected to 10.0.0.3
Hex number 0xDEADBEAF
Hex number 0x10000
user davidoh logged in
user eranr logged in
```

Drain3 extracts the following templates:

```
A0001 (size 3): connected to <IP>
A0002 (size 2): Hex number <HEX>
A0003 (size 2): user <*> logged in
```

This project is an upgrade of the original [Drain](https://github.com/logpai/logparser/blob/master/logparser/Drain) 
project by LogPAI from Python 2.7 to Python 3.6 or later with some bug-fixes and additional features.

Read more information about Drain from the following paper:

- Pinjia He, Jieming Zhu, Zibin Zheng, and Michael R. Lyu. [Drain: An Online Log Parsing Approach with Fixed Depth Tree](http://jmzhu.logpai.com/pub/pjhe_icws2017.pdf), Proceedings of the 24th International Conference on Web Services (ICWS), 2017.


#### New features
 
- **Persistence**. Save and load Drain state into an [Apache Kafka](https://kafka.apache.org) topic or a file.
- **Streaming**. Support feeding Drain with messages one-be-one.
- **Masking**. Replace some message parts (e.g numbers, IPs, emails) with wildcards. This improves the accuracy of template mining.
- **Packaging**. As a pip package. 

#### Expected Input and Output

The input for Drain3 is the unstructured free-text portion log messages. It is recommended to extract 
structured headers like timestamp, hostname. severity, etc.. from log messages before passing to Drain3, 
in order to improve mining accuracy.  

The output is a dictionary with the following fields:
- `change_type`: indicates either if a new template was identified, an existing template was changed or message added to an existing cluster. 
- `cluster_id`: Sequential ID of the cluster that the log belongs to, for example, `A0008`
- `cluster_size`: The size (message count) of the cluster that the log belongs to
- `cluster_count`: Count clusters seen so far
- `template_mined`: the last template of above cluster_id

Templates may change over time based on input, for example:

```
aa aa aa
{"change_type": "cluster_created", "cluster_id": "A0001", "cluster_size": 1, "template_mined": "aa aa aa", "cluster_count": 1}

aa aa ab
{"change_type": "cluster_template_changed", "cluster_id": "A0001", "cluster_size": 2, "template_mined": "aa aa <*>", "cluster_count": 1}
```

**Explanation:** *Drain3 learned that the third token is a parameter*

## Configuration

Drain3 is configured using [configparser](https://docs.python.org/3.4/library/configparser.html) using file `drain3.ini` available parameters are:
- `[DEFAULT]/snapshot_poll_timeout_sec` - maximum timeout for restoring snapshot from Kafka (default 60)
- `[DEFAULT]/sim_th` - recognition threshold (default 0.4)
- `[DEFAULT]/masking` - parameters masking - in json format (default "")
- `[DEFAULT]/snapshot_interval_minutes` - interval for new snapshots (default 1)
- `[DEFAULT]/compress_state` - whether to compress the state before saving it. This can be useful when using Kafka persistence. 

## Masking

This feature allows masking of specific parameters in log message to specific keywords. Use a list of regular expression  
dictionaries in the configuration file with the format {'regex_pattern', 'mask_with'} to set custom masking.

In order to mask an IP address created the file `drain3.ini` :

```
[DEFAULT]
masking = [
    {"regex_pattern":"((?<=[^A-Za-z0-9])|^)(\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3})((?=[^A-Za-z0-9])|$)", "mask_with": "IP"},
    ]
```

Now, Drain3 recognizes IP addresses in templates, for example with input such as:
```
IP is 12.12.12.12
{"change_type": "cluster_created", "cluster_id": "A0013", "cluster_size": 1, "template_mined": "IP is <IP>", "cluster_count": 13}
```

Note: template parameters that do not match custom masking are output as <*>

## Persistence:
The persistence feature saves and loads a snapshot of Drain3 state in (compressed) json format. This feature adds restart resiliency
to Drain allowing continuation of activity and knowledge across restarts.

Drain3 state includes the search tree and all the clusters that were identified up until snapshot time.

The snapshot also persist number of occurrences per cluster, and the cluster_id.

An example of a snapshot:
```
{"clusters": [{"cluster_id": "A0001", "log_template_tokens": `["aa", "aa", "<\*>"]`, "py/object": "drain3_core.LogCluster", "size": 2}, {"cluster_id": "A0002", "log_template_tokens": `["My", "IP", "is", "<IP>"]`, "py/object": "drain3_core.LogCluster", "size": 1}]...
```

This example snapshot persist two clusters with the templates:

> `["aa", "aa", "<\*>"]` - occurs twice
>
>  `["My", "IP", "is", "<IP>"]` - occurs once

Snapshots are created in the following events:

- `cluster_created` - in any new template
- `cluster_template_changed` - in any update of a template
- `periodic` - after n minutes from the last snapshot. This is intended to save cluster sizes even if no new template was identified.  

Drain3 supports two persistence methods:

- **Kafka** - The snapshot is saved in a dedicated topic used only for snapshots - the last message in this topic 
is the last snapshot that will be loaded after restart.
For Kafka persistence, you need to provide: `topic_name` and `server_name`. 

- **File** - The snapshot is saved to a file.


## Installation

Drain3 is available from pypi. To install use `pip`:

```pip3 install drain3```


## Examples

Run from the root folder of the repository: 

```
python -m examples.drain_stdin_demo
```

Use Drain3 with input from stdin and persist to either Kafka / file / no persistence.

Enter several log lines using the command line. Press `q` to end execution.

Change `persistence_type` variable in the example to change persistence mode.

An example drain3.ini file with masking instructions exists in the `examples` folder.

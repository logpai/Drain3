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

A possible Drain3 use case in this blog post: [Use open source Drain3 log-template mining project to monitor for network outages](https://developer.ibm.com/blogs/how-mining-log-templates-can-help-ai-ops-in-cloud-scale-data-centers).


#### New features
 
- **Persistence**. Save and load Drain state into an [Apache Kafka](https://kafka.apache.org) topic, [Redis](https://redis.io/) or a file.
- **Streaming**. Support feeding Drain with messages one-be-one.
- **Masking**. Replace some message parts (e.g numbers, IPs, emails) with wildcards. This improves the accuracy of template mining.
- **Packaging**. As a pip package. 
- **Memory efficiency**. Decrease the memory footprint of internal data structures and introduce cache to control max memory consumed (thanks to @StanislawSwierc)

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

Drain3 is configured using [configparser](https://docs.python.org/3.4/library/configparser.html). 
Config filename is `drain3.ini` in working directory.   

Available parameters are:

- `[DRAIN]/sim_th` - similarity threshold (default 0.4)
- `[DRAIN]/depth` - depth of all leaf nodes (default 4)
- `[DRAIN]/max_children` - max number of children of an internal node (default 100)
- `[DRAIN]/max_clusters` - max number of tracked clusters (unlimited by default). When this number is reached, model starts replacing old clusters with a new ones according to the LRU cache eviction policy.
- `[DRAIN]/extra_delimiters` - delimiters to apply when splitting log message into words (in addition to whitespace) (default none).
    Format is a Python list e.g. `['_', ':']`.
- `[MASKING]/masking` - parameters masking - in json format (default "")
- `[SNAPSHOT]/snapshot_interval_minutes` - time interval for new snapshots (default 1)
- `[SNAPSHOT]/compress_state` - whether to compress the state before saving it. This can be useful when using Kafka persistence. 

## Masking

This feature allows masking of specific parameters in log message to specific keywords. Use a list of regular expression  
dictionaries in the configuration file with the format {'regex_pattern', 'mask_with'} to set custom masking.

In order to mask an IP address created the file `drain3.ini` :

```
[MASKING]
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

## Persistence
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

Drain3 currently supports 3 persistence modes:

- **Kafka** - The snapshot is saved in a dedicated topic used only for snapshots - the last message in this topic 
is the last snapshot that will be loaded after restart.
For Kafka persistence, you need to provide: `topic_name`. You may also provide other `kwargs` 
that are supported by `kafka.KafkaConsumer` and `kafka.Producer` e.g `bootstrap_servers` 
to change Kafka endpoint (default is `localhost:9092`). 

- **Redis** - The snapshot is saved to a key in Redis database (contributed by @matabares).

- **File** - The snapshot is saved to a file.

- **None** - No persistence.

Drain3 persistence modes can be easily extended to another medium / database by 
inheriting the [PersistenceHandler](drain3/persistence_handler.py) class.

## Memory efficiency
This feature limits the max memory used by the model. It is particularly important for large and possibly unbounded log streams. This feature is controlled by the `max_clusters​` parameter, which sets the max number of clusters/templates trarcked by the model. When the limit is reached, new templates start to replace the old ones according to the Least Recently Used (LRU) eviction policy. This makes the model adapt quickly to the most recent templates in the log stream. 


## Installation

Drain3 is available from [PyPI](https://pypi.org/project/drain3). To install use `pip`:

```
pip3 install drain3
```

Note: If you decide to use Kafka or Redis persistence, you should install relevant client library 
explicitly, since it is declared as an extra (optional) dependency, by either:

```
pip3 install kafka-python
```

```
pip3 install redis
```


## Examples

Run [examples/drain_stdin_demo.py](examples/drain_stdin_demo.py) from the root folder of the repository by: 

```
python -m examples.drain_stdin_demo
```

Use Drain3 with input from stdin and persist to either Kafka / file / no persistence.

Enter several log lines using the command line. Press `q` to end execution.

Change `persistence_type` variable in the example to change persistence mode.

An example drain3.ini file with masking instructions exists in the `examples` folder.

## Contributing 

Our project welcomes external contributions. Please refer to [CONTRIBUTING.md](CONTRIBUTING.md) for further details.

## Change Log

##### v0.9.0
* Decrease memory footprint of the main data structures.
* Added `max_clusters` option to limit the number of tracked clusters.
* Changed cluster identifier type from str to int
* Added more unit tests and CI

##### v0.8.6
* Added `extra_delimiters` configuration option to Drain  

##### v0.8.5
* Profiler improvements  

##### v0.8.4
* Masking speed improvement  

##### v0.8.3
* Fix: profiler state after load from snapshot  

##### v0.8.2
* Fixed snapshot backward compatibility to v0.7.9 

##### v0.8.1
* Bugfix in profiling configuration read

##### v0.8.0
* Added time profiling support (disabled by default) 
* Added cluster ID to snapshot reason log (credit: @boernd) 
* Minor Readability and documentation improvements in Drain

##### v0.7.9

* Fix: `KafkaPersistence` now accepts also `bootstrap_servers` as kwargs. 

##### v0.7.8 

* Using `kafka-python` package instead of `kafka` (newer).
* Added support for specifying additional configuration as `kwargs` in Kafka persistence handler.

##### v0.7.7
  
* Corrected default Drain config values.

##### v0.7.6
  
* Improvement in config file handling (Note: new sections were added instead of `DEFAULT` section)

##### v0.7.5
  
* Made Kafka and Redis optional requirements
 

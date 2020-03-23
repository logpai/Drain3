"""
Description : Example of using Drain3 with Kafka persistence
Author      : David Ohana, Moshik Hershcovitch, Eran Raichstein
Author_email: david.ohana@ibm.com, moshikh@il.ibm.com, eranra@il.ibm.com
License     : MIT
"""
import configparser
import json
import logging
import sys

from drain3 import TemplateMiner
from drain3.file_persistence import FilePersistence
from drain3.kafka_persistence import KafkaPersistence

# persistence_type = "KAFKA"
# persistence_type = "NONE"
persistence_type = "FILE"

config = configparser.ConfigParser()
config.read('drain3.ini')

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')

if persistence_type == "KAFKA":
    persistence = KafkaPersistence("localhost:9092", "drain3_state")
elif persistence_type == "FILE":
    persistence = FilePersistence("drain3_state.bin")
else:
    persistence = None

template_miner = TemplateMiner(persistence)
print(f"Drain3 started with '{persistence_type}' persistence, reading from std-in (input 'q' to finish)")
while True:
    log_line = input()
    if log_line == 'q':
        break
    cluster_dict = template_miner.add_log_message(log_line)
    cluster_json = json.dumps(cluster_dict)
    print(cluster_json)

print("Done. Clusters:")
for c in template_miner.drain.clusters:
    print(c)

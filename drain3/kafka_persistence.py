"""
Description : This file implements the persist/restore from Kafka
Author      : Moshik Hershcovitch 
Author_email: moshikh@il.ibm.com
License     : MIT
"""
import configparser

import jsonpickle
import kafka

# logger = logging.getLogger(__name__)
from drain3.persistence_handler import PersistenceHandler

config = configparser.ConfigParser()
config.read('drain3.ini')


class KafkaPersistence(PersistenceHandler):
    def __init__(self, server_list, topic):
        self.server_list = server_list
        self.topic = topic
        self.producer = kafka.KafkaProducer(bootstrap_servers=server_list)

    def save_state(self, state):
        self.producer.send(self.topic, value=state)

    def load_state(self):
        consumer = kafka.KafkaConsumer(bootstrap_servers=self.server_list)
        partition = kafka.TopicPartition(self.topic, 0)
        consumer.assign([partition])
        end_offsets = consumer.end_offsets([partition])
        end_offset = list(end_offsets.values())[0]
        if end_offset > 0:
            consumer.seek(partition, end_offset - 1)
            snapshot_poll_timeout_ms = config.get('DEFAULT', 'snapshot_poll_timeout_sec', fallback=60) * 1000
            records = consumer.poll(snapshot_poll_timeout_ms)
            if not records:
                raise RuntimeError(f"No message received from Kafka during restore even though end_offset>0")
            last_msg = records[partition][0]
            state = last_msg.value
        else:
            state = None

        consumer.close()
        return state

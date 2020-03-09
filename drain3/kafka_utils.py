"""
Description : This file implements the persist/restore from Kafka
Author      : Moshik Hershcovitch 
Author_email: moshikh@il.ibm.com
License     : MIT
"""
import base64
import sys
import zlib
import kafka
import app_config
import jsonpickle


def restore_from_kafka(parser, server_list, topic):
    consumer = kafka.KafkaConsumer(bootstrap_servers=server_list)
    consumer.subscribe(topic)
    partition = kafka.TopicPartition(topic, 0)
    end_offset = consumer.end_offsets([partition])
    end_offset = list(end_offset.values())[0]
    if end_offset > 0:
        print("start restore from Kafka")
        consumer.seek(partition, end_offset - 1)
        records = consumer.poll(app_config.snapshot_poll_timeout_sec * 1000)
        if not records:
            raise RuntimeError(f"No message received from Kafka during restore even though end_offset>0")
        last_msg_compress = records[partition][0]
        last_msg = zlib.decompress(base64.b64decode(last_msg_compress.value))
        parser = jsonpickle.loads(last_msg)

        # After loading from Kafka:the keys of "parser.root_node.key_to_child"
        # are string instead of int, we cast then to int
        keys = []
        for i in parser.root_node.key_to_child_node.keys():
            keys.append(i)
        for key in keys:
            parser.root_node.key_to_child_node[int(key)] = parser.root_node.key_to_child_node.pop(key)

        print("end restore, number of clusters " + str(len(parser.clusters)))
    consumer.close()
    return parser


def send_to_kafka(producer, log_parser_state_json, topic, reason):
    print("creating snapshot. reason:", reason)
    #    print ("write to Kafka: " + str(log_parser_state_json))
    log_parser_state_compress = base64.b64encode(zlib.compress(log_parser_state_json))
    producer.send(topic, value=log_parser_state_compress)

def kafka_producer(server_list):
    return kafka.KafkaProducer(bootstrap_servers=server_list)


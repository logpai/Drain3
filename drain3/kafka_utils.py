"""
Description : This file implements the persist/restore from Kafka
Author      : Moshik Hershcovitch 
Author_email: moshikh@il.ibm.com
License     : MIT
"""
import base64
import zlib
import kafka
import jsonpickle
import logging
import configparser

logger = logging.getLogger(__name__)
config = configparser.ConfigParser()
config.read('drain3.ini')


def restore_from_kafka(parser, server_list, topic):
    consumer = kafka.KafkaConsumer(bootstrap_servers=server_list)
    consumer.subscribe(topic)
    partition = kafka.TopicPartition(topic, 0)
    end_offset = consumer.end_offsets([partition])
    end_offset = list(end_offset.values())[0]
    if end_offset > 0:
        logger.info("start restore snapshot from Kafka topic: {0}".format(topic))
        consumer.seek(partition, end_offset - 1)
        records = consumer.poll(int(config.get('DEFAULT', 'snapshot_poll_timeout_sec', fallback=60)) * 1000)
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

        logger.info("end restore, number of clusters {0}".format(str(len(parser.clusters))))
    consumer.close()
    return parser


def send_to_kafka(producer, log_parser_state_json, topic, reason):
    logger.info("creating snapshot in kafka topic: {0} reason: {1}".format(topic, str(reason)))
    log_parser_state_compress = base64.b64encode(zlib.compress(log_parser_state_json))
    producer.send(topic, value=log_parser_state_compress)


def kafka_producer(server_list):
    return kafka.KafkaProducer(bootstrap_servers=server_list)

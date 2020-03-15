"""
Description : Example file to demonstrate Drain3   
Author      : Moshik Hershcovitch 
Author_email: moshikh@il.ibm.com
License     : MIT
"""

from drain3 import LogParserMain
import logging
import configparser

logger = logging.getLogger(__name__)
config = configparser.ConfigParser()
config.read('drain3.ini')


class LogParser:
    def __init__(self, persistence_type, path_or_server, file_or_topic):
        self.log_parser = LogParserMain(persistence_type, path_or_server, file_or_topic)

    def start(self):
        self.log_parser.start()
        print(config.get('DEFAULT', 'print_prefix', fallback="@@") + "Ready")
        while True:
            log_line = input()
            cluster_json = self.log_parser.add_log_line(log_line)
            print(config.get('DEFAULT', 'print_prefix', fallback="@@") + cluster_json)


kafka_server_list = "localhost:9092"
topic_name_prefix = "topic_"
tenant_id = "demo_tenant_id"

topic = topic_name_prefix + tenant_id
log_parser = LogParser("KAFKA", kafka_server_list, topic)
log_parser.start()

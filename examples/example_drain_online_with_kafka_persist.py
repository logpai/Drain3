"""
Description : Example file to demonstrate Drain3   
Author      : Moshik Hershcovitch 
Author_email: moshikh@il.ibm.com
License     : MIT
"""

import sys
import os
from drain3.app_config import print_prefix
from drain3 import LogParserMain

class LogParser():
    def __init__(self, persistance_type, path_or_server, file_or_topic):
        self.log_parser = LogParserMain(persistance_type, path_or_server, file_or_topic)

    def start(self):
        self.log_parser.start()
        print(print_prefix + "Ready")
        while True:
            log_line = input()
            cluster_json = self.log_parser.add_log_line(log_line)
            print(print_prefix + cluster_json)

kafka_server_list = "localhost:9092"
topic_name_prefix = "topic_"
tenant_id = "demo_tenant_id"

topic = topic_name_prefix + tenant_id
log_parser = LogParser("KAFKA", kafka_server_list, topic) 
log_parser.start()



"""
Description : This file implements an online wrapper example through stdin/stdout for Drain3  
Author      : Moshik Hershcovitch 
Author_email: moshikh@il.ibm.com
License     : MIT
"""

import sys
import os
print_prefix = "@@"
src_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(src_path))
sys.path.insert(0, src_path + "/../src")
from drain3_main import LogParserMain

class LogParserOnline():
    def __init__(self, persistance_type, path_or_server, file_or_topic):
        self.log_parser = LogParserMain(persistance_type, path_or_server, file_or_topic)

    def start(self):
        self.log_parser.start()
        print(print_prefix + "Ready")
        while True:
            log_line = input()
            cluster_json = self.log_parser.add_log_line(log_line)
            print(print_prefix + cluster_json)

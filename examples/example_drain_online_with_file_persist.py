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


persist_file_name = "snapshot.txt"
persist_path = "."

log_parser = LogParser("FILE", persist_path, persist_file_name)
log_parser.start()

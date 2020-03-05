"""
Description : This file implements wrapper of the Drain core algorithm - add persistent and recovery
Author      : Moshik Hershcovitch 
Author_email: moshikh@il.ibm.com
License     : MIT
"""

import json
import time
import jsonpickle
import app_config
from masking import NetworkLogMasker
from drain3_core import LogParserCore
import kafka_utils
import file_persist_utils


class LogParserMain():

    def __init__(self, persistance_type, path_or_server, file_or_topic):
        self.parser = LogParserCore(sim_th=app_config.sim_th)
        self.masker = NetworkLogMasker()
        self.start_time = None
        self.persistance_type = persistance_type  
        self.path_or_server = path_or_server
        self.file_or_topic = file_or_topic 
        self.handler = None


    def start(self):
        self.start_time = time.time()
        if (self.persistance_type == "KAFKA"):
            self.load_from_kafka();
            return
        if(self.persistance_type == "FILE"):
            self.load_from_file();
            return

    def load_from_kafka(self):
        self.handler = kafka_utils.kafka_producer(self.path_or_server)
        self.parser = kafka_utils.restore_from_kafka(self.parser, self.path_or_server, self.file_or_topic)

    def load_from_file(self):
        self.parser = file_persist_utils.restore_from_file(self.parser, self.path_or_server, self.file_or_topic)


    def do_snapshot(self, snapshot_reason):
        if(self.persistance_type == "KAFKA"):
            kafka_utils.send_to_kafka(self.handler, jsonpickle.dumps(self.parser).encode('utf-8'), self.file_or_topic, snapshot_reason)
            return 
        if(self.persistance_type == "FILE"):
            file_persist_utils.persist_to_file(jsonpickle.dumps(self.parser).encode('utf-8'), snapshot_reason, self.path_or_server, self.file_or_topic)
            return

    def snapshot_reason(self, parser_cluster_count, old_total_clusters, was_template_updated):
        snapshot_reason = ""
        diff_time = time.time() - self.start_time 
        if parser_cluster_count > old_total_clusters:
            snapshot_reason += "new template, "
        if was_template_updated:
            snapshot_reason += "updated template, "
        if diff_time >= app_config.snapshot_interval_minutes:
            snapshot_reason += "periodic, "
        return snapshot_reason


    def snapshot_handler(self, parser_cluster_count, cur_total_clusters, was_template_updated): 
            snapshot_reason = self.snapshot_reason(parser_cluster_count, cur_total_clusters, was_template_updated)
            if snapshot_reason != "":
                self.do_snapshot(snapshot_reason)
                self.start_time = time.time()

   
    def add_log_line(self, log_line):
        old_total_clusters = len(self.parser.clusters)
        masked_content = self.masker.mask(log_line)
        cluster_dict = {}
        (cluster_dict["cluster_id"], cluster_dict["cluster_count"], cluster_dict["template_mined"],
         was_template_updated) = self.parser.parse_line(masked_content)
        cluster_json = json.dumps(cluster_dict)
        if (self.persistance_type != ""):
            self.snapshot_handler(cluster_dict["cluster_count"], old_total_clusters, was_template_updated)
        print (cluster_json )
        return cluster_json


    





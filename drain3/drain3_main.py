"""
Description : This file implements wrapper of the Drain core algorithm - add persistent and recovery
Author      : Moshik Hershcovitch 
Author_email: moshikh@il.ibm.com
License     : MIT
"""

import json
import time
import jsonpickle
from drain3.masking import LogMasker
from drain3.drain3_core import LogParserCore
from drain3.file_persist_utils import persist_to_file, restore_from_file
from drain3.kafka_utils import kafka_producer, send_to_kafka, restore_from_kafka
import logging
import configparser

logger = logging.getLogger(__name__)
config = configparser.ConfigParser()
config.read('drain3.ini')


class LogParserMain:

    def __init__(self, persistence_type, path_or_server, file_or_topic):
        self.parser = LogParserCore(sim_th=float(config.get('DEFAULT', 'sim_th', fallback=0.4)))
        self.snapshot_interval_seconds = int(config.get('DEFAULT', 'snapshot_interval_minutes', fallback=1)) * 60
        self.masker = LogMasker()
        self.start_time = None
        self.persistence_type = persistence_type
        self.path_or_server = path_or_server
        self.file_or_topic = file_or_topic
        self.handler = None

    def start(self):
        self.start_time = time.time()
        if self.persistence_type == "KAFKA":
            self.load_from_kafka()
            return
        if self.persistence_type == "FILE":
            self.load_from_file()
            return

    def load_from_kafka(self):
        self.handler = kafka_producer(self.path_or_server)
        self.parser = restore_from_kafka(self.parser, self.path_or_server, self.file_or_topic)

    def load_from_file(self):
        self.parser = restore_from_file(self.parser, self.path_or_server, self.file_or_topic)
        pass

    def do_snapshot(self, snapshot_reason):
        if self.persistence_type == "KAFKA":
            send_to_kafka(self.handler, jsonpickle.dumps(self.parser).encode('utf-8'), self.file_or_topic,
                          snapshot_reason)
            return

        if self.persistence_type == "FILE":
            persist_to_file(jsonpickle.dumps(self.parser).encode('utf-8'), snapshot_reason, self.path_or_server,
                            self.file_or_topic)
            return

    def snapshot_reason(self, parser_cluster_count, old_total_clusters, was_template_updated):
        snapshot_reason = ""
        diff_time = time.time() - self.start_time
        if parser_cluster_count > old_total_clusters:
            snapshot_reason += "new template, "
        if was_template_updated:
            snapshot_reason += "updated template, "
        if diff_time >= self.snapshot_interval_seconds:
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
        if self.persistence_type != "":
            self.snapshot_handler(cluster_dict["cluster_count"], old_total_clusters, was_template_updated)
        logger.info("{0}".format(cluster_json))
        return cluster_json

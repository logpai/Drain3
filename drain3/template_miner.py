"""
Description : This file implements wrapper of the Drain core algorithm - add persistent and recovery
Author      : David Ohana, Moshik Hershcovitch, Eran Raichstein
Author_email: david.ohana@ibm.com, moshikh@il.ibm.com, eranra@il.ibm.com
License     : MIT
"""
import ast
import base64
import configparser
import logging
import time
import zlib

import jsonpickle

from drain3.drain import Drain
from drain3.masking import LogMasker
from drain3.persistence_handler import PersistenceHandler
from drain3.simple_profiler import SimpleProfiler, NullProfiler, Profiler

logger = logging.getLogger(__name__)

config_filename = 'drain3.ini'


class TemplateMiner:

    def __init__(self, persistence_handler: PersistenceHandler = None):
        logger.info("Starting Drain3 template miner")
        self.config = configparser.ConfigParser()
        self.config.read(config_filename)

        self.profiler: Profiler = NullProfiler()
        self.profiling_report_sec = self.config.getint('PROFILING', 'report_sec', fallback=60)
        if self.config.getboolean('PROFILING', 'enabled', fallback=False):
            self.profiler = SimpleProfiler()

        self.persistence_handler = persistence_handler
        self.snapshot_interval_seconds = self.config.getint('SNAPSHOT', 'snapshot_interval_minutes', fallback=5) * 60
        self.compress_state = self.config.getboolean('SNAPSHOT', 'compress_state', fallback=True)

        extra_delimiters = self.config.get('DRAIN', 'extra_delimiters', fallback="[]")
        extra_delimiters = ast.literal_eval(extra_delimiters)

        self.drain = Drain(
            sim_th=self.config.getfloat('DRAIN', 'sim_th', fallback=0.4),
            depth=self.config.getint('DRAIN', 'depth', fallback=4),
            max_children=self.config.getint('DRAIN', 'max_children', fallback=100),
            max_clusters=self.config.getint('DRAIN', 'max_clusters', fallback=None),
            extra_delimiters=extra_delimiters,
            profiler=self.profiler
        )
        self.masker = LogMasker(self.config)
        self.last_save_time = time.time()
        if persistence_handler is not None:
            self.load_state()

    def load_state(self):
        logger.info("Checking for saved state")

        state = self.persistence_handler.load_state()
        if state is None:
            logger.info("Saved state not found")
            return

        if self.compress_state:
            state = zlib.decompress(base64.b64decode(state))

        drain: Drain = jsonpickle.loads(state)

        # After loading, the keys of "parser.root_node.key_to_child" are string instead of int,
        # so we have to cast them to int
        keys = []
        for i in drain.root_node.key_to_child_node.keys():
            keys.append(i)
        for key in keys:
            drain.root_node.key_to_child_node[int(key)] = drain.root_node.key_to_child_node.pop(key)

        drain.profiler = self.profiler

        self.drain = drain
        logger.info("Restored {0} clusters with {1} messages".format(
            len(drain.clusters), drain.get_total_cluster_size()))

    def save_state(self, snapshot_reason):
        state = jsonpickle.dumps(self.drain).encode('utf-8')
        if self.compress_state:
            state = base64.b64encode(zlib.compress(state))

        logger.info(f"Saving state of {len(self.drain.clusters)} clusters "
                    f"with {self.drain.get_total_cluster_size()} messages, {len(state)} bytes, "
                    f"reason: {snapshot_reason}")
        self.persistence_handler.save_state(state)

    def get_snapshot_reason(self, change_type, cluster_id):
        if change_type != "none":
            return "{} ({})".format(change_type, cluster_id)

        diff_time_sec = time.time() - self.last_save_time
        if diff_time_sec >= self.snapshot_interval_seconds:
            return "periodic"

        return None

    def add_log_message(self, log_message: str):
        self.profiler.start_section("total")

        self.profiler.start_section("mask")
        masked_content = self.masker.mask(log_message)
        self.profiler.end_section()

        self.profiler.start_section("drain")
        cluster, change_type = self.drain.add_log_message(masked_content)
        self.profiler.end_section("drain")
        result = {
            "change_type": change_type,
            "cluster_id": cluster.cluster_id,
            "cluster_size": cluster.size,
            "template_mined": cluster.get_template(),
            "cluster_count": len(self.drain.clusters)
        }

        if self.persistence_handler is not None:
            self.profiler.start_section("save_state")
            snapshot_reason = self.get_snapshot_reason(change_type, cluster.cluster_id)
            if snapshot_reason:
                self.save_state(snapshot_reason)
                self.last_save_time = time.time()
            self.profiler.end_section()

        self.profiler.end_section("total")
        self.profiler.report(self.profiling_report_sec)
        return result

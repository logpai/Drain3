"""
Description : This file implements wrapper of the Drain core algorithm - add persistent and recovery
Author      : David Ohana, Moshik Hershcovitch, Eran Raichstein
Author_email: david.ohana@ibm.com, moshikh@il.ibm.com, eranra@il.ibm.com
License     : MIT
"""
import base64
import logging
import time
import zlib

import jsonpickle
from cachetools import LRUCache

from drain3.drain import Drain
from drain3.masking import LogMasker
from drain3.persistence_handler import PersistenceHandler
from drain3.simple_profiler import SimpleProfiler, NullProfiler, Profiler
from drain3.template_miner_config import TemplateMinerConfig

logger = logging.getLogger(__name__)

config_filename = 'drain3.ini'


class TemplateMiner:

    def __init__(self,
                 persistence_handler: PersistenceHandler = None,
                 config: TemplateMinerConfig = None):
        """
        Wrapper for Drain with persistence and masking support

        :param persistence_handler: The type of persistence to use. When None, no persistence is applied.
        :param config: Configuration object. When none, configuration is loaded from default .ini file (if exist)
        """
        logger.info("Starting Drain3 template miner")

        if config is None:
            logger.info(f"Loading configuration from {config_filename}")
            config = TemplateMinerConfig()
            config.load(config_filename)

        self.config = config

        self.profiler: Profiler = NullProfiler()
        if self.config.profiling_enabled:
            self.profiler = SimpleProfiler()

        self.persistence_handler = persistence_handler

        self.drain = Drain(
            sim_th=self.config.drain_sim_th,
            depth=self.config.drain_depth,
            max_children=self.config.drain_max_children,
            max_clusters=self.config.drain_max_clusters,
            extra_delimiters=self.config.drain_extra_delimiters,
            profiler=self.profiler
        )
        self.masker = LogMasker(self.config.masking_instructions)
        self.last_save_time = time.time()
        if persistence_handler is not None:
            self.load_state()

    def load_state(self):
        logger.info("Checking for saved state")

        state = self.persistence_handler.load_state()
        if state is None:
            logger.info("Saved state not found")
            return

        if self.config.snapshot_compress_state:
            state = zlib.decompress(base64.b64decode(state))

        drain: Drain = jsonpickle.loads(state, keys=True)

        # json-pickle encoded keys as string by default, so we have to convert those back to int
        # this is only relevant for backwards compatibility when loading a snapshot of drain <= v0.9.1
        # which did not use json-pickle's keys=true
        if len(drain.id_to_cluster) > 0 and isinstance(next(iter(drain.id_to_cluster.keys())), str):
            drain.id_to_cluster = {int(k): v for k, v in list(drain.id_to_cluster.items())}
            if self.config.drain_max_clusters:
                cache = LRUCache(maxsize=self.config.drain_max_clusters)
                cache.update(drain.id_to_cluster)
                drain.id_to_cluster = cache

        drain.profiler = self.profiler

        self.drain = drain
        logger.info("Restored {0} clusters with {1} messages".format(
            len(drain.clusters), drain.get_total_cluster_size()))

    def save_state(self, snapshot_reason):
        state = jsonpickle.dumps(self.drain, keys=True).encode('utf-8')
        if self.config.snapshot_compress_state:
            state = base64.b64encode(zlib.compress(state))

        logger.info(f"Saving state of {len(self.drain.clusters)} clusters "
                    f"with {self.drain.get_total_cluster_size()} messages, {len(state)} bytes, "
                    f"reason: {snapshot_reason}")
        self.persistence_handler.save_state(state)

    def get_snapshot_reason(self, change_type, cluster_id):
        if change_type != "none":
            return "{} ({})".format(change_type, cluster_id)

        diff_time_sec = time.time() - self.last_save_time
        if diff_time_sec >= self.config.snapshot_interval_minutes * 60:
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
        self.profiler.report(self.config.profiling_report_sec)
        return result

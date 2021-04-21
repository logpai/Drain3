"""
Description : This file implements wrapper of the Drain core algorithm - add persistent and recovery
Author      : David Ohana, Moshik Hershcovitch, Eran Raichstein
Author_email: david.ohana@ibm.com, moshikh@il.ibm.com, eranra@il.ibm.com
License     : MIT
"""
import base64
import logging
import re
import time

import jsonpickle
import zlib
from cachetools import LRUCache

from drain3.drain import Drain, LogCluster
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

        param_str = self.config.mask_prefix + "*" + self.config.mask_suffix
        self.drain = Drain(
            sim_th=self.config.drain_sim_th,
            depth=self.config.drain_depth,
            max_children=self.config.drain_max_children,
            max_clusters=self.config.drain_max_clusters,
            extra_delimiters=self.config.drain_extra_delimiters,
            profiler=self.profiler,
            param_str=param_str
        )
        self.masker = LogMasker(self.config.masking_instructions, self.config.mask_prefix, self.config.mask_suffix)
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

    def add_log_message(self, log_message: str) -> dict:
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

    def match(self, log_message: str) -> LogCluster:

        """
          Match against an already existing cluster. Match shall be perfect (sim_th=1.0).
          New cluster will not be created as a result of this call, nor any cluster modifications.
          :param log_message: log message to match
          :return: Matched cluster or None of no match found.
        """
        masked_content = self.masker.mask(log_message)
        matched_cluster = self.drain.match(masked_content)
        return matched_cluster

    def get_parameter_list(self, log_template: str, content: str):
        escaped_prefix = re.escape(self.config.mask_prefix)
        escaped_suffix = re.escape(self.config.mask_suffix)
        template_regex = re.sub(escaped_prefix + r".+?" + escaped_suffix, self.drain.param_str, log_template)
        if self.drain.param_str not in template_regex:
            return []
        template_regex = re.escape(template_regex)
        template_regex = re.sub(r'\\ +', r'\\s+', template_regex)
        template_regex = "^" + template_regex.replace(escaped_prefix + r"\*" + escaped_suffix, "(.*?)") + "$"

        for delimiter in self.config.drain_extra_delimiters:
            content = re.sub(delimiter, ' ', content)
        parameter_list = re.findall(template_regex, content)
        parameter_list = parameter_list[0] if parameter_list else ()
        parameter_list = list(parameter_list) if isinstance(parameter_list, tuple) else [parameter_list]

        def is_mask(p: str):
            return p.startswith(self.config.mask_prefix) and p.endswith(self.config.mask_suffix)

        parameter_list = [p for p in list(parameter_list) if not is_mask(p)]
        return parameter_list

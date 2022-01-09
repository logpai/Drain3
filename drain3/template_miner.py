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
import zlib
import random
from typing import Callable

import jsonpickle
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
            param_str=param_str,
            parametrize_numeric_tokens=self.config.parametrize_numeric_tokens
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

        loaded_drain: Drain = jsonpickle.loads(state, keys=True)

        # json-pickle encoded keys as string by default, so we have to convert those back to int
        # this is only relevant for backwards compatibility when loading a snapshot of drain <= v0.9.1
        # which did not use json-pickle's keys=true
        if len(loaded_drain.id_to_cluster) > 0 and isinstance(next(iter(loaded_drain.id_to_cluster.keys())), str):
            loaded_drain.id_to_cluster = {int(k): v for k, v in list(loaded_drain.id_to_cluster.items())}
            if self.config.drain_max_clusters:
                cache = LRUCache(maxsize=self.config.drain_max_clusters)
                cache.update(loaded_drain.id_to_cluster)
                loaded_drain.id_to_cluster = cache

        self.drain.id_to_cluster = loaded_drain.id_to_cluster
        self.drain.clusters_counter = loaded_drain.clusters_counter
        self.drain.root_node = loaded_drain.root_node

        logger.info("Restored {0} clusters built from {1} messages".format(
            len(loaded_drain.clusters), loaded_drain.get_total_cluster_size()))

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

    def match(self, log_message: str, full_search_strategy="never") -> LogCluster:
        """
        Mask log message and match against an already existing cluster.
        Match shall be perfect (sim_th=1.0).
        New cluster will not be created as a result of this call, nor any cluster modifications.

        :param log_message: log message to match
        :param full_search_strategy: when to perform full cluster search.
            (1) "never" is the fastest, will always perform a tree search [O(log(n)] but might produce
            false negatives (wrong mismatches) on some edge cases;
            (2) "fallback" will perform a linear search [O(n)] among all clusters with the same token count, but only in
            case tree search found no match.
            It should not have false negatives, however tree-search may find a non-optimal match with
            more wildcard parameters than necessary;
            (3) "always" is the slowest. It will select the best match among all known clusters, by always evaluating
            all clusters with the same token count, and selecting the cluster with perfect all token match and least
            count of wildcard matches.
        :return: Matched cluster or None if no match found.
        """

        masked_content = self.masker.mask(log_message)
        matched_cluster = self.drain.match(masked_content, full_search_strategy)
        return matched_cluster

    def get_parameter_list(self, log_template: str, content: str, provide_valid_mask: Callable[[str], str] = None) -> [str]:
        """
        Extract parameters from a log message according to a provided template.

        :param log_template: log template corresponding to the log message
        :param content: log message to extract parameters from
        :param provide_valid_mask: an optional function that provides a mask-value that does not interfere with any MaskingInstruction;
            This function is used to create temporary masks that are unique and
            will be called until it creates a mask-value that has not been used yet.
            To this end the mask-value of the current attempt is provided as input.
            The default function used in case no custom one is provided,
            will append characters from the mask-value until the created mask-value is unique.
        :return: A list of parameters present in the log message.
        """
        if not provide_valid_mask:
            def provide_valid_mask(old_mask):
                return old_mask + random.choice(old_mask)
        masking_parameters = {}
        escaped_prefix = re.escape(self.config.mask_prefix)
        escaped_suffix = re.escape(self.config.mask_suffix)
        masked_content = content
        for match in re.finditer(escaped_prefix + r"(.+?)" + escaped_suffix, masked_content):
            # Mark masks already present in the message as containing None as parameter.
            # This way they cannot be confused with any real parameters.
            masking_parameters[match.group(1)] = None
        for instruction in self.config.masking_instructions:
            if instruction.mask_with == "*":
                # Will not be able to differentiate between masks added by this instruction
                # and those added by Drain, so these will just need to be skipped.
                continue
            def mask_parameter(match):
                id = instruction.mask_with
                while id in masking_parameters.keys():
                    id = provide_valid_mask(id)
                masking_parameters[id] = match.group(0)
                return self.config.mask_prefix + id + self.config.mask_suffix
            # Replace parameter with a unique mask.
            masked_content = instruction.regex.sub(mask_parameter, masked_content)
        # Gather all mask-values and match them to the actual parameters.
        masking_parameter_list = (match.group(1) for match in re.finditer(escaped_prefix + r"(.+?)" + escaped_suffix, masked_content))
        masking_parameter_list = list(filter(lambda x: x is not None, (masking_parameters[id] for id in masking_parameter_list)))

        escaped_param_str = re.escape(self.drain.param_str)
        template_regex = re.escape(log_template)
        if escaped_param_str not in template_regex:
            return masking_parameter_list
        masking_parameter_iterator = iter(masking_parameter_list)
        # Replace masks in the template that are guaranteed to be generated by a MaskingInstruction
        # (aka. where the mask-value is not *) with the actual parameter for that mask.
        # The parameter is placed in a group so it can later be extracted easily.
        template_regex = re.sub(re.escape(escaped_prefix) + r"(?!\\[*]" + re.escape(escaped_suffix) + ").+?" + re.escape(escaped_suffix), lambda x: "(" + next(masking_parameter_iterator) + ")", template_regex)

        template_regex = re.sub(r"\\ +", r"\\s+", template_regex)
        template_regex = "^" + template_regex.replace(escaped_param_str, "(.*?)") + "$"

        for delimiter in self.config.drain_extra_delimiters:
            content = re.sub(delimiter, " ", content)
        parameter_match = re.match(template_regex, content)
        parameter_list = parameter_match.groups() if parameter_match else ()

        return list(parameter_list)

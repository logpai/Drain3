import ast
import configparser
import json
import logging

from drain3.masking import MaskingInstruction

logger = logging.getLogger(__name__)


class TemplateMinerConfig:
    def __init__(self):
        self.profiling_enabled = False
        self.profiling_report_sec = 60
        self.snapshot_interval_minutes = 5
        self.snapshot_compress_state = True
        self.drain_extra_delimiters = []
        self.drain_sim_th = 0.4
        self.drain_depth = 4
        self.drain_max_children = 100
        self.drain_max_clusters = None
        self.masking_instructions = []

    def load(self, config_filename: str):
        parser = configparser.ConfigParser()
        read_files = parser.read(config_filename)
        if len(read_files) == 0:
            logger.warning(f"config file not found: {config_filename}")

        section_profiling = 'PROFILING'
        section_snapshot = 'SNAPSHOT'
        section_drain = 'DRAIN'
        section_masking = 'MASKING'

        self.profiling_enabled = parser.getboolean(section_profiling, 'enabled',
                                                   fallback=self.profiling_enabled)
        self.profiling_report_sec = parser.getint(section_profiling, 'report_sec',
                                                  fallback=self.profiling_report_sec)

        self.snapshot_interval_minutes = parser.getint(section_snapshot, 'snapshot_interval_minutes',
                                                       fallback=self.snapshot_interval_minutes)
        self.snapshot_compress_state = parser.getboolean(section_snapshot, 'compress_state',
                                                         fallback=self.snapshot_compress_state)

        drain_extra_delimiters_str = parser.get(section_drain, 'extra_delimiters',
                                                fallback=str(self.drain_extra_delimiters))
        self.drain_extra_delimiters = ast.literal_eval(drain_extra_delimiters_str)

        self.drain_sim_th = parser.getfloat(section_drain, 'sim_th',
                                            fallback=self.drain_sim_th)
        self.drain_depth = parser.getint(section_drain, 'depth',
                                         fallback=self.drain_depth)
        self.drain_max_children = parser.getint(section_drain, 'max_children',
                                                fallback=self.drain_max_children)
        self.drain_max_clusters = parser.getint(section_drain, 'max_clusters',
                                                fallback=self.drain_max_clusters)

        masking_instructions_str = parser.get(section_masking, 'masking',
                                              fallback=str(self.masking_instructions))
        masking_instructions = []
        masking_list = json.loads(masking_instructions_str)
        for mi in masking_list:
            instruction = MaskingInstruction(mi['regex_pattern'], mi['mask_with'])
            masking_instructions.append(instruction)
        self.masking_instructions = masking_instructions

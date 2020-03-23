"""
Description : This file implements the persist/restore from Kafka
Author      : Moshik Hershcovitch
Author_email: moshikh@il.ibm.com
License     : MIT
"""
import configparser
import json
import logging
import re
from typing import List

logger = logging.getLogger(__name__)
config = configparser.ConfigParser()
config.read('drain3.ini')


class MaskingInstruction:
    def __init__(self, regex_pattern: str, mask_with: str):
        self.regex_pattern = regex_pattern
        self.mask_with = mask_with
        self.regex = re.compile(regex_pattern)
        self.mask_with_wrapped = "<" + mask_with + ">"


class RegexMasker:
    def __init__(self, masking_instructions: List[MaskingInstruction]):
        self.masking_instructions = masking_instructions

    def mask(self, content: str):
        for mi in self.masking_instructions:
            content = re.sub(mi.regex, mi.mask_with_wrapped, content)
        return content


# Some masking examples
# ---------------------
#
# masking_instances = [
#    MaskingInstruction(r'((?<=[^A-Za-z0-9])|^)(([0-9a-f]{2,}:){3,}([0-9a-f]{2,}))((?=[^A-Za-z0-9])|$)', "ID"),
#    MaskingInstruction(r'((?<=[^A-Za-z0-9])|^)(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})((?=[^A-Za-z0-9])|$)', "IP"),
#    MaskingInstruction(r'((?<=[^A-Za-z0-9])|^)([0-9a-f]{6,} ?){3,}((?=[^A-Za-z0-9])|$)', "SEQ"),
#    MaskingInstruction(r'((?<=[^A-Za-z0-9])|^)([0-9A-F]{4} ?){4,}((?=[^A-Za-z0-9])|$)', "SEQ"),
#
#    MaskingInstruction(r'((?<=[^A-Za-z0-9])|^)(0x[a-f0-9A-F]+)((?=[^A-Za-z0-9])|$)', "HEX"),
#    MaskingInstruction(r'((?<=[^A-Za-z0-9])|^)([\-\+]?\d+)((?=[^A-Za-z0-9])|$)', "NUM"),
#    MaskingInstruction(r'(?<=executed cmd )(".+?")', "CMD"),
# ]


class LogMasker:
    def __init__(self):
        masking_instances = []
        self.masker = None
        m = json.loads(config.get('DEFAULT', 'masking', fallback="[]"))
        for i in range(len(m)):
            logger.info("Adding custom mask {0} --> {1}".format(str(m[i]['mask_with']), str(m[i]['regex_pattern'])))
            masking_instances.append(MaskingInstruction(m[i]['regex_pattern'], m[i]['mask_with']))
        self.masker = RegexMasker(masking_instances)

    def mask(self, content: str):
        if self.masker is not None:
            return self.masker.mask(content)
        else:
            return content

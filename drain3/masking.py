"""
Description : This file implements the persist/restore from Kafka
Author      : Moshik Hershcovitch
Author_email: moshikh@il.ibm.com
License     : MIT
"""
import logging
import re
from typing import List

logger = logging.getLogger(__name__)


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
            # content = re.sub(mi.regex, mi.mask_with_wrapped, content)
            content = mi.regex.sub(mi.mask_with_wrapped, content)
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
    def __init__(self, masking_instructions: List[MaskingInstruction]):
        self.masker = RegexMasker(masking_instructions)

    def mask(self, content: str):
        if self.masker is not None:
            return self.masker.mask(content)
        else:
            return content

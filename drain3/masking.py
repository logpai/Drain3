# SPDX-License-Identifier: MIT

import abc
import re
from typing import cast, Collection, Dict, List


class AbstractMaskingInstruction(abc.ABC):

    def __init__(self, mask_with: str):
        self.mask_with = mask_with

    @abc.abstractmethod
    def mask(self, content: str, mask_prefix: str, mask_suffix: str) -> str:
        """
        Mask content according to this instruction and return the result.

        :param content: text to apply masking to
        :param mask_prefix: the prefix of any masks inserted
        :param mask_suffix: the suffix of any masks inserted
        """
        pass


class MaskingInstruction(AbstractMaskingInstruction):

    def __init__(self, pattern: str, mask_with: str):
        super().__init__(mask_with)
        self.regex = re.compile(pattern)

    @property
    def pattern(self) -> str:
        return self.regex.pattern

    def mask(self, content: str, mask_prefix: str, mask_suffix: str) -> str:
        mask = mask_prefix + self.mask_with + mask_suffix
        return self.regex.sub(mask, content)


# Alias for `MaskingInstruction`.
RegexMaskingInstruction = MaskingInstruction


class LogMasker:

    def __init__(self, masking_instructions: Collection[AbstractMaskingInstruction],
                 mask_prefix: str, mask_suffix: str):
        self.mask_prefix = mask_prefix
        self.mask_suffix = mask_suffix
        self.masking_instructions = masking_instructions
        mask_name_to_instructions: Dict[str, List[AbstractMaskingInstruction]] = {}
        for mi in self.masking_instructions:
            mask_name_to_instructions.setdefault(mi.mask_with, [])
            mask_name_to_instructions[mi.mask_with].append(mi)
        self.mask_name_to_instructions = mask_name_to_instructions

    def mask(self, content: str) -> str:
        for mi in self.masking_instructions:
            content = mi.mask(content, self.mask_prefix, self.mask_suffix)
        return content

    @property
    def mask_names(self) -> Collection[str]:
        return self.mask_name_to_instructions.keys()

    def instructions_by_mask_name(self, mask_name: str) -> Collection[AbstractMaskingInstruction]:
        return cast(Collection[AbstractMaskingInstruction], self.mask_name_to_instructions.get(mask_name, []))

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

import re
from typing import List
import mask_conf
import os

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


class NetworkLogMasker:
    def __init__(self):
        masking_insts = []
        self.masker = None     
        if os.path.exists("mask_conf.py") and os.path.getsize("mask_conf.py") > 0:
            m = mask_conf.masking 
            for i in range(len(m)):   
                masking_insts.append(MaskingInstruction(m[i]['regex_pattern'], m[i]['mask_with']))
#        masking_insts = [
#            MaskingInstruction(r'((?<=[^A-Za-z0-9])|^)(([0-9a-f]{2,}:){3,}([0-9a-f]{2,}))((?=[^A-Za-z0-9])|$)', "ID"),
#            MaskingInstruction(r'((?<=[^A-Za-z0-9])|^)(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})((?=[^A-Za-z0-9])|$)', "IP"),
#            MaskingInstruction(r'((?<=[^A-Za-z0-9])|^)([0-9a-f]{6,} ?){3,}((?=[^A-Za-z0-9])|$)', "SEQ"),
#            MaskingInstruction(r'((?<=[^A-Za-z0-9])|^)([0-9A-F]{4} ?){4,}((?=[^A-Za-z0-9])|$)', "SEQ"),
#
#            MaskingInstruction(r'((?<=[^A-Za-z0-9])|^)(0x[a-f0-9A-F]+)((?=[^A-Za-z0-9])|$)', "HEX"),
#            MaskingInstruction(r'((?<=[^A-Za-z0-9])|^)([\-\+]?\d+)((?=[^A-Za-z0-9])|$)', "NUM"),
#            MaskingInstruction(r'(?<=executed cmd )(".+?")', "CMD"),
#        ]
            self.masker = RegexMasker(masking_insts)

    def mask(self, content: str):
        if self.masker is not None:     
            return self.masker.mask(content)
        else:
            return content

 

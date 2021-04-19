import unittest

from drain3.masking import MaskingInstruction, RegexMasker


class MaskingTest(unittest.TestCase):
    def test(self):
        s = "D9 test 999 888 1A ccc 3"
        mi = MaskingInstruction(r'((?<=[^A-Za-z0-9])|^)([\-\+]?\d+)((?=[^A-Za-z0-9])|$)', "NUM")
        rm = RegexMasker([mi], "<!", "!>")
        masked = rm.mask(s)
        self.assertEqual("D9 test <!NUM!> <!NUM!> 1A ccc <!NUM!>", masked)

# SPDX-License-Identifier: MIT

import unittest

from drain3.masking import MaskingInstruction, LogMasker


class MaskingTest(unittest.TestCase):

    def test_instructions_by_mask_name(self):
        instructions = []
        a = MaskingInstruction(r"a", "1")
        instructions.append(a)
        b = MaskingInstruction(r"b", "1")
        instructions.append(b)
        c = MaskingInstruction(r"c", "2")
        instructions.append(c)
        d = MaskingInstruction(r"d", "3")
        instructions.append(d)
        x = MaskingInstruction(r"x", "something else")
        instructions.append(x)
        y = MaskingInstruction(r"y", "something else")
        instructions.append(y)
        masker = LogMasker(instructions, "", "")
        self.assertCountEqual(["1", "2", "3", "something else"], masker.mask_names)
        self.assertCountEqual([a, b], masker.instructions_by_mask_name("1"))
        self.assertCountEqual([c], masker.instructions_by_mask_name("2"))
        self.assertCountEqual([d], masker.instructions_by_mask_name("3"))
        self.assertCountEqual([x, y], masker.instructions_by_mask_name("something else"))

    def test_mask(self):
        s = "D9 test 999 888 1A ccc 3"
        mi = MaskingInstruction(r"((?<=[^A-Za-z0-9])|^)([\-\+]?\d+)((?=[^A-Za-z0-9])|$)", "NUM")
        masker = LogMasker([mi], "<!", "!>")
        masked = masker.mask(s)
        self.assertEqual("D9 test <!NUM!> <!NUM!> 1A ccc <!NUM!>", masked)

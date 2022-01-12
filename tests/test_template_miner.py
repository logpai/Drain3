# SPDX-License-Identifier: MIT

import io
import logging
import sys
import unittest
from os.path import dirname

from drain3 import TemplateMiner
from drain3.masking import MaskingInstruction
from drain3.memory_buffer_persistence import MemoryBufferPersistence
from drain3.template_miner_config import TemplateMinerConfig


class TemplateMinerTest(unittest.TestCase):
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')

    def test_load_config(self):
        config = TemplateMinerConfig()
        config.load(dirname(__file__) + "/drain3_test.ini")
        self.assertEqual(1024, config.drain_max_clusters)
        self.assertListEqual(["_"], config.drain_extra_delimiters)
        self.assertEqual(7, len(config.masking_instructions))

    def test_save_load_snapshot_unlimited_clusters(self):
        self.save_load_snapshot(None)

    def test_save_load_snapshot_limited_clusters(self):
        self.save_load_snapshot(10)

    def save_load_snapshot(self, max_clusters):
        persistence = MemoryBufferPersistence()

        config = TemplateMinerConfig()
        config.drain_max_clusters = max_clusters
        template_miner1 = TemplateMiner(persistence, config)
        print(template_miner1.add_log_message("hello"))
        print(template_miner1.add_log_message("hello ABC"))
        print(template_miner1.add_log_message("hello BCD"))
        print(template_miner1.add_log_message("hello XYZ"))
        print(template_miner1.add_log_message("goodbye XYZ"))

        template_miner2 = TemplateMiner(persistence, config)

        self.assertListEqual(list(template_miner1.drain.id_to_cluster.keys()),
                             list(template_miner2.drain.id_to_cluster.keys()))

        self.assertListEqual(list(template_miner1.drain.root_node.key_to_child_node.keys()),
                             list(template_miner2.drain.root_node.key_to_child_node.keys()))

        def get_tree_lines(template_miner):
            sio = io.StringIO()
            template_miner.drain.print_tree(sio)
            sio.seek(0)
            return sio.readlines()

        self.assertListEqual(get_tree_lines(template_miner1),
                             get_tree_lines(template_miner2))

        print(template_miner2.add_log_message("hello yyy"))
        print(template_miner2.add_log_message("goodbye ABC"))

    def test_extract_parameters(self):
        config = TemplateMinerConfig()
        mi = MaskingInstruction("((?<=[^A-Za-z0-9])|^)([\\-\\+]?\\d+)((?=[^A-Za-z0-9])|$)", "NUM")
        config.masking_instructions.append(mi)
        mi = MaskingInstruction(r"multiple words", "WORDS")
        config.masking_instructions.append(mi)
        config.mask_prefix = "[:"
        config.mask_suffix = ":]"
        template_miner = TemplateMiner(None, config)

        def add_and_test(msg, expected_params, exact_matching=False):
            print(f"msg: {msg}")
            res = template_miner.add_log_message(msg)
            print(f"result: {res}")
            extracted_parameters = template_miner.extract_parameters(
                res["template_mined"], msg, exact_matching=exact_matching)
            self.assertIsNotNone(extracted_parameters)
            params = [parameter.value for parameter in extracted_parameters]
            print(f"params: {params}")
            self.assertListEqual(params, expected_params)

        add_and_test("hello", [])
        add_and_test("hello ABC", [])
        add_and_test("hello BCD", ["BCD"])
        add_and_test("hello    BCD", ["BCD"])
        add_and_test("hello\tBCD", ["BCD"])
        add_and_test("request took 123 ms", ["123"])
        add_and_test("file saved [test.xml]", [])
        add_and_test("new order received: [:xyz:]", [])
        add_and_test("order type: new, order priority:3", ["3"])
        add_and_test("order type: changed, order priority:5", ["changed,", "5"])
        add_and_test("sometimes one needs multiple words", ["multiple words"], True)
        add_and_test("sometimes one needs not", ["not"], True)
        add_and_test("sometimes one needs multiple words", ["multiple words"], True)

    def test_extract_parameters_direct(self):
        config = TemplateMinerConfig()
        mi = MaskingInstruction(r"hdfs://[\w.:@-]*((/[\w.~%+-]+)+/?)?", "hdfs_uri")
        config.masking_instructions.append(mi)
        mi = MaskingInstruction(r"(?P<quote>[\"'`]).*?(?P=quote)", "quoted_string")
        config.masking_instructions.append(mi)
        mi = MaskingInstruction(r"((?P<p_0>[*_])\2{0,2}).*?\1", "markdown_emph")
        config.masking_instructions.append(mi)
        mi = MaskingInstruction(r"multiple \*word\* pattern", "*words*")
        config.masking_instructions.append(mi)
        mi = MaskingInstruction(r"some \S+ \S+ pattern", "*words*")
        config.masking_instructions.append(mi)
        mi = MaskingInstruction(r"(\d{1,3}\.){3}\d{1,3}", "ip")
        config.masking_instructions.append(mi)
        mi = MaskingInstruction(r"(?P<number>\d+)\.\d+", "float")
        config.masking_instructions.append(mi)
        mi = MaskingInstruction(r"0[xX][a-fA-F0-9]+", "integer")
        config.masking_instructions.append(mi)
        mi = MaskingInstruction(r"(?P<number>\d+)", "integer")
        config.masking_instructions.append(mi)
        mi = MaskingInstruction(r"HelloWorld", "*")
        config.masking_instructions.append(mi)
        mi = MaskingInstruction(r"MaskPrefix", "<")
        config.masking_instructions.append(mi)
        template_miner = TemplateMiner(None, config)

        test_vectors = [
            (
                "<hdfs_uri>:<integer>+<integer>",
                "hdfs://msra-sa-41:9000/pageinput2.txt:671088640+134217728",
                ["hdfs://msra-sa-41:9000/pageinput2.txt", "671088640", "134217728"],
                ["hdfs_uri", "integer", "integer"]
            ),
            (
                "Hello <quoted_string>",
                "Hello 'World'",
                ["'World'"],
                ["quoted_string"]
            ),
            (
                "<quoted_string><quoted_string>",
                """'This "should"'`do no breakin'`""",
                ["""'This "should"'""", "`do no breakin'`"],
                ["quoted_string", "quoted_string"]
            ),
            (
                "This is <markdown_emph> <markdown_emph>!.",
                "This is ___very___ *important*!.",
                ["___very___", "*important*"],
                ["markdown_emph", "markdown_emph"]
            ),
            (
                "<float>.<*>",
                "0.15.Test",
                ["0.15", "Test"],
                ["float", "*"]
            ),
            (
                "<ip>:<integer>",
                "192.0.0.1:5000",
                ["192.0.0.1", "5000"],
                ["ip", "integer"]
            ),
            (
                "<ip>:<integer>:<integer>",
                "192.0.0.1:5000:123",
                ["192.0.0.1", "5000", "123"],
                ["ip", "integer", "integer"]
            ),
            (
                "<float>.<*>.<float>",
                "0.15.Test.0.2",
                ["0.15", "Test", "0.2"],
                ["float", "*", "float"]
            ),
            (
                "<float> <float>",
                "0.15 10.16",
                ["0.15", "10.16"],
                ["float", "float"]
            ),
            (
                "<*words*>@<integer>",
                "some other cool pattern@0xe1f",
                ["some other cool pattern", "0xe1f"],
                ["*words*", "integer"]
            ),
            (
                "Another test with <*words*> that includes <integer><integer> and <integer> <*> <integer>",
                "Another test with some other 0Xadded pattern that includes 500xc0ffee and 0X4 times 5",
                ["some other 0Xadded pattern", "50", "0xc0ffee", "0X4", "times", "5"],
                ["*words*", "integer", "integer", "integer", "*", "integer"]
            ),
            (
                "some <*words*> <*words*>",
                "some multiple *word* pattern some confusing *word* pattern",
                ["multiple *word* pattern", "some confusing *word* pattern"],
                ["*words*", "*words*"]
            ),
            (
                "<*words*> <*>",
                "multiple *word* pattern <*words*>",
                ["multiple *word* pattern", "<*words*>"],
                ["*words*", "*"]
            ),
            (
                "<*> <*>",
                "HelloWorld Test",
                ["HelloWorld", "Test"],
                ["*", "*"]
            ),
            (
                "<*> <*>",
                "HelloWorld <anything>",
                ["HelloWorld", "<anything>"],
                ["*", "*"]
            ),
            (
                "<*><integer>",
                "HelloWorld1",
                ["HelloWorld", "1"],
                ["*", "integer"]
            ),
            (
                "<*> works <*>",
                "This works as-expected",
                ["This", "as-expected"],
                ["*", "*"]
            ),
            (
                "<memory:<integer>>",
                "<memory:8>",
                ["8"],
                ["integer"]
            ),
            (
                "<memory:<integer> <core:<float>>>",
                "<memory:8 <core:0.5>>",
                ["8", "0.5"],
                ["integer", "float"]
            ),
            (
                "<*> <memory:<<integer> <core:<float>>>",
                "New: <memory:<8 <core:0.5>>",
                ["New:", "8", "0.5"],
                ["*", "integer", "float"]
            ),
            (
                "<<>",
                "MaskPrefix",
                ["MaskPrefix"],
                ["<"]
            ),
            (
                "<<<>>",
                "<MaskPrefix>",
                ["MaskPrefix"],
                ["<"]
            ),
            (
                "There are no parameters here.",
                "There are no parameters here.",
                [],
                []
            ),
            (
                "<float> <float>",
                "0.15 10.16 3.19",
                None,
                None
            ),
            (
                "<float> <float>",
                "0.15 10.16 test 3.19",
                None,
                None
            ),
            (
                "<memory:<<integer> <core:<float>>>",
                "<memory:8 <core:0.5>>",
                None,
                None
            ),
            (
                "<<>",
                "<<>",
                None,
                None
            ),
            (
                "<*words*> <*words*>",
                "0.15 0.15",
                None,
                None
            ),
        ]

        for template, content, expected_parameters, expected_mask_names in test_vectors:
            with self.subTest(template=template, content=content, expected_parameters=expected_parameters):
                extracted_parameters = template_miner.extract_parameters(template, content, exact_matching=True)
                if expected_parameters is None:
                    self.assertIsNone(extracted_parameters)
                else:
                    self.assertIsNotNone(extracted_parameters)
                    self.assertListEqual([parameter.value for parameter in extracted_parameters],
                                         expected_parameters)
                    self.assertListEqual([parameter.mask_name for parameter in extracted_parameters],
                                         expected_mask_names)

    def test_match_only(self):
        config = TemplateMinerConfig()
        config.drain_extra_delimiters = ["_"]
        mi = MaskingInstruction("((?<=[^A-Za-z0-9])|^)([\\-\\+]?\\d+)((?=[^A-Za-z0-9])|$)", "NUM")
        config.masking_instructions.append(mi)
        tm = TemplateMiner(None, config)

        res = tm.add_log_message("aa aa aa")
        print(res)

        res = tm.add_log_message("aa aa bb")
        print(res)

        res = tm.add_log_message("xx yy zz")
        print(res)

        res = tm.add_log_message("rrr qqq 123")
        print(res)

        c = tm.match("aa   aa tt")
        self.assertEqual(1, c.cluster_id)

        c = tm.match("aa aa 12")
        self.assertEqual(1, c.cluster_id)

        c = tm.match("xx yy   zz")
        self.assertEqual(2, c.cluster_id)

        c = tm.match("xx yy rr")
        self.assertIsNone(c)

        c = tm.match("nothing")
        self.assertIsNone(c)

        c = tm.match("rrr qqq   456   ")
        self.assertEqual(3, c.cluster_id)

        c = tm.match("rrr qqq 555.2")
        self.assertIsNone(c)

        c = tm.match("rrr qqq num")
        self.assertIsNone(c)

    def test_match_strategies(self):
        miner = TemplateMiner()
        print(miner.add_log_message("training4Model start"))
        print(miner.add_log_message("loadModel start"))
        print(miner.add_log_message("loadModel stop"))
        print(miner.add_log_message("this is a test"))
        miner.drain.print_tree()
        self.assertIsNotNone(miner.match("loadModel start", full_search_strategy="fallback"))
        self.assertIsNotNone(miner.match("loadModel start", full_search_strategy="always"))
        self.assertIsNone(miner.match("loadModel start", full_search_strategy="never"))
        print(miner.add_log_message("loadModel start"))
        self.assertIsNotNone(miner.match("loadModel start", full_search_strategy="fallback"))
        self.assertIsNotNone(miner.match("loadModel start", full_search_strategy="always"))
        self.assertIsNotNone(miner.match("loadModel start", full_search_strategy="never"))

        config = TemplateMinerConfig()
        config.parametrize_numeric_tokens = False
        miner = TemplateMiner(config=config)
        print(miner.add_log_message("training4Model start"))
        print(miner.add_log_message("loadModel start"))
        print(miner.add_log_message("loadModel stop"))
        print(miner.add_log_message("this is a test"))
        self.assertIsNotNone(miner.match("loadModel start", full_search_strategy="fallback"))
        self.assertIsNotNone(miner.match("loadModel start", full_search_strategy="always"))
        self.assertIsNotNone(miner.match("loadModel start", full_search_strategy="never"))

        self.assertIsNone(miner.match("", full_search_strategy="never"))
        self.assertIsNone(miner.match("", full_search_strategy="always"))
        self.assertIsNone(miner.match("", full_search_strategy="fallback"))

        print(miner.add_log_message(""))
        self.assertIsNotNone(miner.match("", full_search_strategy="never"))
        self.assertIsNotNone(miner.match("", full_search_strategy="always"))
        self.assertIsNotNone(miner.match("", full_search_strategy="fallback"))

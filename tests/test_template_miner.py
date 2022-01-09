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

    def test_get_param_list(self):
        config = TemplateMinerConfig()
        mi = MaskingInstruction("((?<=[^A-Za-z0-9])|^)([\\-\\+]?\\d+)((?=[^A-Za-z0-9])|$)", "NUM")
        config.masking_instructions.append(mi)
        config.mask_prefix = "[:"
        config.mask_suffix = ":]"
        template_miner = TemplateMiner(None, config)

        def add_and_test(msg, expected_params):
            print(f"msg: {msg}")
            res = template_miner.add_log_message(msg)
            print(f"result: {res}")
            params = template_miner.get_parameter_list(res["template_mined"], msg)
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

    def test_get_param_list_direct(self):
        template_miner = TemplateMiner()
        template = "<hdfs_uri>:<number>+<number>"
        content = "hdfs://msra-sa-41:9000/pageinput2.txt:671088640+134217728"
        params = template_miner.get_parameter_list(template, content)
        expected_params = ["hdfs://msra-sa-41:9000/pageinput2.txt", "671088640", "134217728"]
        self.assertListEqual(params, expected_params)

        template = "<float>.<*>"
        content = "0.15.Test"
        params = template_miner.get_parameter_list(template, content)
        expected_params = ["0.15", "Test"]
        self.assertListEqual(params, expected_params)

        template = "<ip>:<port>"
        content = "192.0.0.1:5000"
        params = template_miner.get_parameter_list(template, content)
        expected_params = ["192.0.0.1", "5000"]
        self.assertListEqual(params, expected_params)

        template = "<ip>:<port>:<num>"
        content = "192.0.0.1:5000:123"
        params = template_miner.get_parameter_list(template, content)
        expected_params = ["192.0.0.1", "5000", "123"]
        self.assertListEqual(params, expected_params)

        # commented test below fails because current approach satisfies every mask by any non-whitespace sequence
        # this means extra characters may be captured by the greedy match as in the example below
        # todo: fix
        # possible fixes:
        # 1. capture exact mask regex
        # 2. retain parameters while masking in both LogMasker and Drain core, preserving order.
        # for more details see GitHub issue #49

        # template = "<float>.<*>.<float>"
        # content = "0.15.Test.0.2"
        # params = template_miner.get_parameter_list(template, content)
        # expected_params = ["0.15", "Test", "0.2"]
        # self.assertListEqual(params, expected_params)

        template = "<float> <float>"
        content = "0.15 10.16"
        params = template_miner.get_parameter_list(template, content)
        expected_params = ["0.15", "10.16"]
        self.assertListEqual(params, expected_params)

        # template does not match content (next two cases)
        # it should not even be possible to get such a template if template is produced using TemplateMiner
        template = "<float> <float>"
        content = "0.15 10.16 3.19"
        params = template_miner.get_parameter_list(template, content)
        expected_params = []
        self.assertListEqual(params, expected_params)

        template = "<float> <float>"
        content = "0.15 10.16 test 3.19"
        params = template_miner.get_parameter_list(template, content)
        expected_params = []
        self.assertListEqual(params, expected_params)

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

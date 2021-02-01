import io
import logging
import sys
import unittest

from drain3 import TemplateMiner
from drain3.memory_buffer_persistence import MemoryBufferPersistence
from drain3.template_miner_config import TemplateMinerConfig


class TemplateMinerTest(unittest.TestCase):
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')

    def test_load_config(self):
        config = TemplateMinerConfig()
        config.load("drain3_test.ini")
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

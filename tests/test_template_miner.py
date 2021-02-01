import io
import logging
import sys
import unittest

from drain3 import TemplateMiner
from drain3.memory_buffer_persistence import MemoryBufferPersistence


class TemplateMinerTest(unittest.TestCase):

    def test_save_load_snapshot(self):
        logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')

        persistence = MemoryBufferPersistence()

        template_miner1 = TemplateMiner(persistence)
        template_miner1.add_log_message("hello")
        template_miner1.add_log_message("hello ABC")
        template_miner1.add_log_message("hello BCD")
        template_miner1.add_log_message("hello XYZ")
        template_miner1.add_log_message("goodbye XYZ")

        template_miner2 = TemplateMiner(persistence)

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

        template_miner2.add_log_message("goodbye ABC")

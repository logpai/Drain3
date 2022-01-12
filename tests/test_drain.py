# SPDX-License-Identifier: MIT

import unittest

from drain3.drain import Drain, LogCluster


class DrainTest(unittest.TestCase):

    def test_add_shorter_than_depth_message(self):
        model = Drain(depth=4)
        res = model.add_log_message("word")
        print(res[1])
        print(res[0])
        self.assertEqual(res[1], "cluster_created")

        res = model.add_log_message("word")
        print(res[1])
        print(res[0])
        self.assertEqual(res[1], "none")

        res = model.add_log_message("otherword")
        print(res[1])
        print(res[0])
        self.assertEqual(res[1], "cluster_created")

        self.assertEqual(2, len(model.id_to_cluster))

    def test_add_log_message(self):
        model = Drain()
        entries = str.splitlines(
            """
            Dec 10 07:07:38 LabSZ sshd[24206]: input_userauth_request: invalid user test9 [preauth]
            Dec 10 07:08:28 LabSZ sshd[24208]: input_userauth_request: invalid user webmaster [preauth]
            Dec 10 09:12:32 LabSZ sshd[24490]: Failed password for invalid user ftpuser from 0.0.0.0 port 62891 ssh2
            Dec 10 09:12:35 LabSZ sshd[24492]: Failed password for invalid user pi from 0.0.0.0 port 49289 ssh2
            Dec 10 09:12:44 LabSZ sshd[24501]: Failed password for invalid user ftpuser from 0.0.0.0 port 60836 ssh2
            Dec 10 07:28:03 LabSZ sshd[24245]: input_userauth_request: invalid user pgadmin [preauth]
            """
        )
        expected = str.splitlines(
            """
            Dec 10 07:07:38 LabSZ sshd[24206]: input_userauth_request: invalid user test9 [preauth]
            Dec 10 <*> LabSZ <*> input_userauth_request: invalid user <*> [preauth]
            Dec 10 09:12:32 LabSZ sshd[24490]: Failed password for invalid user ftpuser from 0.0.0.0 port 62891 ssh2
            Dec 10 <*> LabSZ <*> Failed password for invalid user <*> from 0.0.0.0 port <*> ssh2
            Dec 10 <*> LabSZ <*> Failed password for invalid user <*> from 0.0.0.0 port <*> ssh2
            Dec 10 <*> LabSZ <*> input_userauth_request: invalid user <*> [preauth]
            """
        )
        actual = []

        for entry in entries:
            cluster, change_type = model.add_log_message(entry)
            actual.append(cluster.get_template())

        self.assertListEqual(list(map(str.strip, expected)), actual)
        self.assertEqual(8, model.get_total_cluster_size())

    def test_add_log_message_sim_75(self):
        """When `sim_th` is set to 75% then only certain log entries match.

        In this test similarity threshold is set to 75% which makes the model
        less aggressive in grouping entries into clusters. In particular, it
        only finds clusters for "Failed password" entries.
        """
        model = Drain(
            depth=4,
            sim_th=0.75,
            max_children=100,
        )
        entries = str.splitlines(
            """
            Dec 10 07:07:38 LabSZ sshd[24206]: input_userauth_request: invalid user test9 [preauth]
            Dec 10 07:08:28 LabSZ sshd[24208]: input_userauth_request: invalid user webmaster [preauth]
            Dec 10 09:12:32 LabSZ sshd[24490]: Failed password for invalid user ftpuser from 0.0.0.0 port 62891 ssh2
            Dec 10 09:12:35 LabSZ sshd[24492]: Failed password for invalid user pi from 0.0.0.0 port 49289 ssh2
            Dec 10 09:12:44 LabSZ sshd[24501]: Failed password for invalid user ftpuser from 0.0.0.0 port 60836 ssh2
            Dec 10 07:28:03 LabSZ sshd[24245]: input_userauth_request: invalid user pgadmin [preauth]
            """
        )
        expected = str.splitlines(
            """
            Dec 10 07:07:38 LabSZ sshd[24206]: input_userauth_request: invalid user test9 [preauth]
            Dec 10 07:08:28 LabSZ sshd[24208]: input_userauth_request: invalid user webmaster [preauth]
            Dec 10 09:12:32 LabSZ sshd[24490]: Failed password for invalid user ftpuser from 0.0.0.0 port 62891 ssh2
            Dec 10 <*> LabSZ <*> Failed password for invalid user <*> from 0.0.0.0 port <*> ssh2
            Dec 10 <*> LabSZ <*> Failed password for invalid user <*> from 0.0.0.0 port <*> ssh2
            Dec 10 07:28:03 LabSZ sshd[24245]: input_userauth_request: invalid user pgadmin [preauth]
            """
        )
        actual = []

        for entry in entries:
            cluster, change_type = model.add_log_message(entry)
            actual.append(cluster.get_template())

        self.assertListEqual(list(map(str.strip, expected)), actual)
        self.assertEqual(8, model.get_total_cluster_size())

    def test_max_clusters(self):
        """Verify model respects the max_clusters option.
        
        Key difference between this and other tests is that with `max_clusters`
        set to 1 model is capable of keeping track of a single cluster at a
        time. Consequently, when log stream switched form the A format to the B
        and back model doesn't recognize it and returnes a new template with no
        slots.
        """
        model = Drain(max_clusters=1)
        entries = str.splitlines(
            """
            A format 1
            A format 2
            B format 1
            B format 2
            A format 3
            """
        )
        expected = str.splitlines(
            """
            A format 1
            A format <*>
            B format 1
            B format <*>
            A format 3
            """
        )
        actual = []

        for entry in entries:
            cluster, change_type = model.add_log_message(entry)
            actual.append(cluster.get_template())

        self.assertListEqual(list(map(str.strip, expected)), actual)
        self.assertEqual(1, model.get_total_cluster_size())

    def test_max_clusters_lru_multiple_leaf_nodes(self):
        """When all templates end up in different nodes and the max number of
        clusters is reached, then clusters are removed according to the lru
        policy.
        """
        model = Drain(max_clusters=2, depth=4, param_str="*")
        entries = [
            "A A A",
            "A A B",
            "B A A",
            "B A B",
            "C A A",
            "C A B",
            "B A A",
            "A A A",
        ]
        expected = [
            # lru: []
            "A A A",
            # lru: ["A A A"]
            "A A *",
            # lru: ["A A *"]
            "B A A",
            # lru: ["B A A", "A A *"]
            "B A *",
            # lru: ["B A *", "A A *"]
            "C A A",
            # lru: ["C A A", "B A *"]
            "C A *",
            # lru: ["C A *", "B A *"]
            "B A *",
            # Message "B A A" was normalized because the template "B A *" is
            # still present in the cache.
            # lru: ["B A *", "C A *"]
            "A A A",
            # Message "A A A" was not normalized because the template "C A A"
            # pushed out the template "A A *" from the cache.
            # lru: ["A A A", "C A *"]
        ]
        actual = []

        for entry in entries:
            cluster, _ = model.add_log_message(entry)
            actual.append(cluster.get_template())

        self.assertListEqual(list(map(str.strip, expected)), actual)
        self.assertEqual(4, model.get_total_cluster_size())

    def test_max_clusters_lru_single_leaf_node(self):
        """When all templates end up in the same leaf node and the max number of
        clusters is reached, then clusters are removed according to the lru
        policy.
        """
        model = Drain(max_clusters=2, depth=4, param_str="*")
        entries = [
            "A A A",
            "A A B",
            "A B A",
            "A B B",
            "A C A",
            "A C B",
            "A B A",
            "A A A",
        ]
        expected = [
            # lru: []
            "A A A",
            # lru: ["A A A"]
            "A A *",
            # lru: ["A A *"]
            "A B A",
            # lru: ["B A A", "A A *"]
            "A B *",
            # lru: ["B A *", "A A *"]
            "A C A",
            # lru: ["C A A", "B A *"]
            "A C *",
            # lru: ["C A *", "B A *"]
            "A B *",
            # Message "B A A" was normalized because the template "B A *" is
            # still present in the cache.
            # lru: ["B A *", "C A *"]
            "A A A",
            # Message "A A A" was not normalized because the template "C A A"
            # pushed out the template "A A *" from the cache.
            # lru: ["A A A", "C A *"]
        ]
        actual = []

        for entry in entries:
            cluster, _ = model.add_log_message(entry)
            actual.append(cluster.get_template())

        self.assertListEqual(list(map(str.strip, expected)), actual)
        # self.assertEqual(5, model.get_total_cluster_size())

    def test_match_only(self):
        model = Drain()
        res = model.add_log_message("aa aa aa")
        print(res[0])

        res = model.add_log_message("aa aa bb")
        print(res[0])

        res = model.add_log_message("aa aa cc")
        print(res[0])

        res = model.add_log_message("xx yy zz")
        print(res[0])

        c: LogCluster = model.match("aa aa tt")
        self.assertEqual(1, c.cluster_id)

        c: LogCluster = model.match("xx yy zz")
        self.assertEqual(2, c.cluster_id)

        c: LogCluster = model.match("xx yy rr")
        self.assertIsNone(c)

        c: LogCluster = model.match("nothing")
        self.assertIsNone(c)


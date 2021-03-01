import unittest

from drain3.drain import Drain


class DrainTest(unittest.TestCase):
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

    def test_max_clusters_lru(self):
        """When max number of clusters is reached, then clusters are removed
        according to the lru policy.
        """
        model = Drain(max_clusters=3, depth=3)
        entries = [
            "A A foramt 1",
            "A A foramt 2",
            "A B format 1",
            "A B format 2",
            "B format 1",
            "B format 2",
            "A A foramt 3",
            "C foramt 1",
            "A B format 3",
        ]
        expected = [
            "A A foramt 1",  # LRU = ["A"]
            "A A foramt <*>",  # LRU = ["A"]
            # Use "A A" prefix to make sure both "A" and "A A" clusters end up
            # in the same leaf node. This is a setup for an interesting edge
            # case.
            "A B format 1",  # LRU = ["AA", "A"]
            "A B format <*>",  # LRU = ["AA", "A"]
            "B format 1",  # LRU = ["B", "A A", "A"]
            "B format <*>",  # LRU = ["B", "A A", "A"]
            "A A foramt <*>",  # LRU = ["A", "B", "A A"]
            "C foramt 1",  # LRU = ["C", "A", "B"]
            # Cluster "A A" should have been removed in the previous step, thus,
            # it should be recognized as a new cluster with no slots.
            "A B format 3",  # LRU = ["A A', "C", "A"]
        ]
        actual = []

        for entry in entries:
            cluster, _ = model.add_log_message(entry)
            actual.append(cluster.get_template())

        self.assertListEqual(list(map(str.strip, expected)), actual)
        self.assertEqual(5, model.get_total_cluster_size())

    def test_one_token_message(self):
        model = Drain()
        cluster, change_type = model.add_log_message("oneTokenMessage")
        self.assertEqual("cluster_created", change_type, "1st check")
        cluster, change_type = model.add_log_message("oneTokenMessage")
        self.assertEqual("none", change_type, "2nd check")

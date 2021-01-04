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
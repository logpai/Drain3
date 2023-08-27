# SPDX-License-Identifier: MIT
# This file implements the Drain algorithm for log parsing.
# Based on https://github.com/logpai/logparser/blob/master/logparser/Drain/Drain.py by LogPAI team

from typing import Optional, Sequence, Tuple

from drain3.drain import DrainBase, LogCluster, Node


class JaccardDrain(DrainBase):
    """
    add a new matching pattern to the log cluster.
    Cancels log message length as  first token.
    Drain that uses Jaccard similarity to match log messages.
    """

    def tree_search(self,
                    root_node: Node,
                    tokens: Sequence[str],
                    sim_th: float,
                    include_params: bool) -> Optional[LogCluster]:
        # at first level, children are grouped by token (The first word in tokens)
        token_count = len(tokens)
        # cur_node = root_node.key_to_child_node.get(str(token_count))

        if not tokens:
            token_first = ""
            cur_node = root_node.key_to_child_node.get(token_first)
        else:
            token_first = tokens[0]
            cur_node = root_node.key_to_child_node.get(token_first)

        # no template with same token count yet
        if cur_node is None:
            return None

        # handle case of empty log string - return the single cluster in that group
        if token_count == 0:
            return self.id_to_cluster.get(cur_node.cluster_ids[0])

        # find the leaf node for this log - a path of nodes matching the first N tokens (N=tree depth)
        cur_node_depth = 1  # first level is 1 <root>

        for token in tokens[1:]:
            # at max depth
            if cur_node_depth >= self.max_node_depth:
                break

            # this is last token
            # It starts with the second word, so the sentence length -1
            if cur_node_depth == token_count - 1:
                break

            key_to_child_node = cur_node.key_to_child_node
            cur_node = key_to_child_node.get(token)

            if cur_node is None:  # no exact next token exist, try wildcard node
                cur_node = key_to_child_node.get(self.param_str)
            if cur_node is None:  # no wildcard node exist
                return None

            cur_node_depth += 1

        # get best match among all clusters with same prefix, or None if no match is above sim_th
        cluster = self.fast_match(cur_node.cluster_ids, tokens, sim_th, include_params)

        return cluster

    def add_seq_to_prefix_tree(self, root_node: Node, cluster: LogCluster) -> None:
        token_count = len(cluster.log_template_tokens)
        # Determine if the string is empty
        if not cluster.log_template_tokens:
            token_first = ""
        else:
            token_first = cluster.log_template_tokens[0]
        if token_first not in root_node.key_to_child_node:
            first_layer_node = Node()
            root_node.key_to_child_node[token_first] = first_layer_node
        else:
            first_layer_node = root_node.key_to_child_node[token_first]

        cur_node = first_layer_node

        # handle case of empty log string
        if token_count == 0:
            cur_node.cluster_ids = [cluster.cluster_id]
            return

        # test_add_shorter_than_depth_message : only one word add into current node
        if token_count == 1:
            # clean up stale clusters before adding a new one.
            new_cluster_ids = []
            for cluster_id in cur_node.cluster_ids:
                if cluster_id in self.id_to_cluster:
                    new_cluster_ids.append(cluster_id)
            new_cluster_ids.append(cluster.cluster_id)
            cur_node.cluster_ids = new_cluster_ids

        current_depth = 1
        for token in cluster.log_template_tokens[1:]:
            # if at max depth or this is last token in template - add current log cluster to the leaf node
            # It starts with the second word, so the sentence length -1
            if current_depth >= self.max_node_depth or current_depth >= token_count - 1:
                # clean up stale clusters before adding a new one.
                new_cluster_ids = []
                for cluster_id in cur_node.cluster_ids:
                    if cluster_id in self.id_to_cluster:
                        new_cluster_ids.append(cluster_id)
                new_cluster_ids.append(cluster.cluster_id)
                cur_node.cluster_ids = new_cluster_ids
                break

            # if token not matched in this layer of existing tree.
            if token not in cur_node.key_to_child_node:
                if self.parametrize_numeric_tokens and self.has_numbers(token):
                    if self.param_str not in cur_node.key_to_child_node:
                        new_node = Node()
                        cur_node.key_to_child_node[self.param_str] = new_node
                        cur_node = new_node
                    else:
                        cur_node = cur_node.key_to_child_node[self.param_str]

                else:
                    if self.param_str in cur_node.key_to_child_node:
                        if len(cur_node.key_to_child_node) < self.max_children:
                            new_node = Node()
                            cur_node.key_to_child_node[token] = new_node
                            cur_node = new_node
                        else:
                            cur_node = cur_node.key_to_child_node[self.param_str]
                    else:
                        if len(cur_node.key_to_child_node) + 1 < self.max_children:
                            new_node = Node()
                            cur_node.key_to_child_node[token] = new_node
                            cur_node = new_node
                        elif len(cur_node.key_to_child_node) + 1 == self.max_children:
                            new_node = Node()
                            cur_node.key_to_child_node[self.param_str] = new_node
                            cur_node = new_node
                        else:
                            cur_node = cur_node.key_to_child_node[self.param_str]

            # if the token is matched
            else:
                cur_node = cur_node.key_to_child_node[token]

            current_depth += 1

    # seq1 is a template, seq2 is the log to match
    def get_seq_distance(self, seq1: Sequence[str], seq2: Sequence[str], include_params: bool) -> Tuple[float, int]:
        # Jaccard index, It is used to measure the similarity of two sets.
        # The closer its value is to 1, the more common members the two sets have, and the higher the similarity.

        # sequences are empty - full match
        if len(seq1) == 0:
            return 1.0, 0

        param_count = 0

        for token1 in seq1:
            if token1 == self.param_str:
                param_count += 1

        # If the token and the data have the same length, and there are param_str in the token
        if len(seq1) == len(seq2) and param_count > 0:
            # seq2 removes the param_str position
            seq2 = [x for i, x in enumerate(seq2) if seq1[i] != self.param_str]

        # If there are param_str, they are removed from the coefficient calculation
        if include_params:
            seq1 = [x for x in seq1 if x != self.param_str]

        # Calculate the Jaccard coefficient
        ret_val = len(set(seq1) & set(seq2)) / len(set(seq1) | set(seq2))

        # Jaccard coefficient calculated under the same conditions has a low simSep value
        # So gain is applied to the calculated value (The test case test_add_log_message_sim_75)
        ret_val = ret_val * 1.3 if ret_val * 1.3 < 1 else 1

        return ret_val, param_count

    # seq1:tonkens->list seq2:template->tuple
    def create_template(self, seq1: Sequence[str], seq2: Sequence[str]) -> Sequence[str]:

        inter_set = set(seq1) & set(seq2)

        # test_max_clusters_lru_multiple_leaf_nodes
        # Update param_str at different positions with the same length
        if len(seq1) == len(seq2):
            ret_val = list(seq2)
            for i, (token1, token2) in enumerate(zip(seq1, seq2)):
                if token1 != token2:
                    ret_val[i] = self.param_str
        # param_str is updated at the new position with different length
        else:
            # Take the template with long length
            ret_val = list(seq1) if len(seq1) > len(seq2) else list(seq2)
            for i, token in enumerate(ret_val):
                if token not in inter_set:
                    ret_val[i] = self.param_str

        return ret_val

    def match(self, content: str, full_search_strategy: str = "never") -> Optional[LogCluster]:

        assert full_search_strategy in ["always", "never", "fallback"]

        # Because the template length and data are not equal in length, Jaccard distance required_sim_th != 1
        required_sim_th = 0.8
        content_tokens = self.get_content_as_tokens(content)

        def full_search() -> Optional[LogCluster]:
            all_ids = self.get_clusters_ids_for_seq_len(content_tokens[0])
            cluster = self.fast_match(all_ids, content_tokens, required_sim_th, include_params=True)
            return cluster

        if full_search_strategy == "always":
            return full_search()

        match_cluster = self.tree_search(self.root_node, content_tokens, required_sim_th, include_params=True)
        if match_cluster is not None:
            return match_cluster

        if full_search_strategy == "never":
            return None

        return full_search()


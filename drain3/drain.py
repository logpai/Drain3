"""
Description : This file implements the Drain algorithm for log parsing
Author      : LogPAI team
Modified by : david.ohana@ibm.com, moshikh@il.ibm.com
License     : MIT
"""

param_str = '<*>'


class LogCluster:
    def __init__(self, log_template_tokens: list, cluster_id):
        self.log_template_tokens = log_template_tokens
        self.cluster_id = cluster_id
        self.size = 1

    def get_template(self):
        return ' '.join(self.log_template_tokens)

    def __str__(self):
        return f"{self.cluster_id} (size {self.size}): {self.get_template()}"


class Node:
    def __init__(self, key, depth):
        self.depth = depth
        self.key = key
        self.key_to_child_node = {}
        self.clusters = []


class Drain:

    def __init__(self, depth=4, sim_th=0.4, max_children=100):
        """
        Attributes
        ----------
            depth : depth of all leaf nodes
            sim_th : similarity threshold
            max_children : max number of children of an internal node
        """
        self.depth = depth - 2
        self.sim_th = sim_th
        self.max_children = max_children
        self.root_node = Node("(ROOT)", 0)
        self.clusters = []

    @staticmethod
    def has_numbers(s):
        return any(char.isdigit() for char in s)

    def tree_search(self, root_node: Node, tokens):

        token_count = len(tokens)
        parent_node = root_node.key_to_child_node.get(token_count)

        # no template with same token count yet
        if parent_node is None:
            return None

        # handle case of empty log string
        if token_count == 0:
            return parent_node.clusters[0]

        cluster = None
        current_depth = 1
        for token in tokens:
            at_max_depth = current_depth == self.depth
            is_last_token = current_depth == token_count

            if at_max_depth or is_last_token:
                break

            key_to_child_node = parent_node.key_to_child_node
            if token in key_to_child_node:
                parent_node = key_to_child_node[token]
            elif param_str in key_to_child_node:
                parent_node = key_to_child_node[param_str]
            else:
                return cluster
            current_depth += 1

        cluster = self.fast_match(parent_node.clusters, tokens)

        return cluster

    def add_seq_to_prefix_tree(self, root_node, cluster: LogCluster):
        token_count = len(cluster.log_template_tokens)
        if token_count not in root_node.key_to_child_node:
            first_layer_node = Node(key=token_count, depth=1)
            root_node.key_to_child_node[token_count] = first_layer_node
        else:
            first_layer_node = root_node.key_to_child_node[token_count]

        parent_node = first_layer_node

        # handle case of empty log string
        if len(cluster.log_template_tokens) == 0:
            parent_node.clusters.append(cluster)
            return

        current_depth = 1
        for token in cluster.log_template_tokens:

            # Add current log cluster to the leaf node
            at_max_depth = current_depth == self.depth
            is_last_token = current_depth == token_count
            if at_max_depth or is_last_token:
                parent_node.clusters.append(cluster)
                break

            # If token not matched in this layer of existing tree.
            if token not in parent_node.key_to_child_node:
                if not self.has_numbers(token):
                    if param_str in parent_node.key_to_child_node:
                        if len(parent_node.key_to_child_node) < self.max_children:
                            new_node = Node(key=token, depth=current_depth + 1)
                            parent_node.key_to_child_node[token] = new_node
                            parent_node = new_node
                        else:
                            parent_node = parent_node.key_to_child_node[param_str]
                    else:
                        if len(parent_node.key_to_child_node) + 1 < self.max_children:
                            new_node = Node(key=token, depth=current_depth + 1)
                            parent_node.key_to_child_node[token] = new_node
                            parent_node = new_node
                        elif len(parent_node.key_to_child_node) + 1 == self.max_children:
                            new_node = Node(key=param_str, depth=current_depth + 1)
                            parent_node.key_to_child_node[param_str] = new_node
                            parent_node = new_node
                        else:
                            parent_node = parent_node.key_to_child_node[param_str]

                else:
                    if param_str not in parent_node.key_to_child_node:
                        new_node = Node(key=param_str, depth=current_depth + 1)
                        parent_node.key_to_child_node[param_str] = new_node
                        parent_node = new_node
                    else:
                        parent_node = parent_node.key_to_child_node[param_str]

            # If the token is matched
            else:
                parent_node = parent_node.key_to_child_node[token]

            current_depth += 1

    # seq1 is template
    @staticmethod
    def get_seq_distance(seq1, seq2):
        assert len(seq1) == len(seq2)
        sim_tokens = 0
        param_count = 0

        for token1, token2 in zip(seq1, seq2):
            if token1 == param_str:
                param_count += 1
                continue
            if token1 == token2:
                sim_tokens += 1

        ret_val = float(sim_tokens) / len(seq1)

        return ret_val, param_count

    def fast_match(self, cluster_list: list, tokens):
        match_cluster = None

        max_sim = -1
        max_param_count = -1
        max_cluster = None

        for cluster in cluster_list:
            cur_sim, param_count = self.get_seq_distance(cluster.log_template_tokens, tokens)
            if cur_sim > max_sim or (cur_sim == max_sim and param_count > max_param_count):
                max_sim = cur_sim
                max_param_count = param_count
                max_cluster = cluster

        if max_sim >= self.sim_th:
            match_cluster = max_cluster

        return match_cluster

    @staticmethod
    def get_template(seq1, seq2):
        assert len(seq1) == len(seq2)
        ret_val = []

        i = 0
        for word in seq1:
            if word == seq2[i]:
                ret_val.append(word)
            else:
                ret_val.append(param_str)

            i += 1

        return ret_val

    def print_tree(self):
        self.print_node(self.root_node, 0)

    def print_node(self, node, depth):
        out_str = ''
        for i in range(depth):
            out_str += '\t'

        if node.depth == 0:
            out_str += 'Root'
        elif node.depth == 1:
            out_str += '<' + str(node.key) + '>'
        else:
            out_str += node.key

        print(out_str)

        if node.depth == self.depth:
            return 1
        for child in node.key_to_child_node:
            self.print_node(node.key_to_child_node[child], depth + 1)

    @staticmethod
    def num_to_cluster_id(num):
        cluster_id = "A{:04d}".format(num)
        return cluster_id

    def add_log_message(self, content: str):
        content = content.strip()
        content_tokens = content.split()
        match_cluster = self.tree_search(self.root_node, content_tokens)

        # Match no existing log cluster
        if match_cluster is None:
            cluster_num = len(self.clusters) + 1
            cluster_id = self.num_to_cluster_id(cluster_num)
            match_cluster = LogCluster(content_tokens, cluster_id)
            self.clusters.append(match_cluster)
            self.add_seq_to_prefix_tree(self.root_node, match_cluster)
            update_type = "cluster_created"

        # Add the new log message to the existing cluster
        else:
            new_template_tokens = self.get_template(content_tokens, match_cluster.log_template_tokens)
            if ' '.join(new_template_tokens) != ' '.join(match_cluster.log_template_tokens):
                match_cluster.log_template_tokens = new_template_tokens
                update_type = "cluster_template_changed"
            else:
                update_type = "none"
            match_cluster.size += 1

        return match_cluster, update_type

    def get_total_cluster_size(self):
        size = 0
        for c in self.clusters:
            size += c.size
        return size

"""
Description : This file implements the persist/restore from file 
Author      : Moshik Hershcovitch 
Author_email: moshikh@il.ibm.com
License     : MIT
"""

import jsonpickle
import os

def restore_from_file(parser, path, file_name):
    my_file = path +"/" + file_name
    if os.path.exists(my_file) and os.path.getsize(my_file) > 0:
        handler = open(my_file, "rb")
        print("start restore from file")
        msg = handler.readline()
        parser = jsonpickle.loads(msg)
        keys = []
        for i in parser.root_node.key_to_child_node.keys():
            keys.append(i)
        for key in keys:
            parser.root_node.key_to_child_node[int(key)] = parser.root_node.key_to_child_node.pop(key)
        print("end restore, number of clusters " + str(len(parser.clusters)))

        handler.close()
        if (os.path.exists(path + "/tmp")):
           os.remove(path + "/tmp") 
    return parser


def persist_to_file(log_parser_state_json, reason, path, file_name):
    print("creating snapshot. reason:", reason)
    handler = open(path + "/tmp", "wb")
    handler.write(log_parser_state_json)
    handler.close() 
    os.rename(path + "/tmp", path + "/" + file_name)
    


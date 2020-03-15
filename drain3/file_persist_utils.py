"""
Description : This file implements the persist/restore from file 
Author      : Moshik Hershcovitch 
Author_email: moshikh@il.ibm.com
License     : MIT
"""

import jsonpickle
import os
import logging
import configparser

logger = logging.getLogger(__name__)
config = configparser.ConfigParser()
config.read('drain3.ini')


def restore_from_file(parser, path, file_name):
    my_file = path + "/" + file_name
    if os.path.exists(my_file) and os.path.getsize(my_file) > 0:
        handler = open(my_file, "rb")
        logger.info("start restore snapshot from file : {0}".format(file_name))
        msg = handler.readline()
        parser = jsonpickle.loads(msg)
        keys = []
        for i in parser.root_node.key_to_child_node.keys():
            keys.append(i)
        for key in keys:
            parser.root_node.key_to_child_node[int(key)] = parser.root_node.key_to_child_node.pop(key)
        logger.info("end restore, number of clusters {0}".format(str(len(parser.clusters))))
        handler.close()
        if os.path.exists(path + "/tmp"):
            os.remove(path + "/tmp")
    return parser


def persist_to_file(log_parser_state_json, reason, path, file_name):
    logger.info("creating snapshot to file: {0} reason: {1}".format(file_name, str(reason)))
    handler = open(path + "/tmp", "wb")
    handler.write(log_parser_state_json)
    handler.close() 
    os.rename(path + "/tmp", path + "/" + file_name)
    


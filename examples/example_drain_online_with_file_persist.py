import os
from drain3_online import LogParserOnline

persist_file_name = "snapshot.txt"
persist_path = "./examples"

log_parser = LogParserOnline("FILE", persist_path, persist_file_name) 
log_parser.start()



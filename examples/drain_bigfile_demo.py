"""
Description : Example of using Drain3 to process a real world file
Author      : David Ohana
Author_email: david.ohana@ibm.com
License     : MIT
"""
import json
import logging
import os
import subprocess
import sys
import time

from drain3 import TemplateMiner

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')

in_gz_file = "SSH.tar.gz"
in_log_file = "SSH.log"
if not os.path.isfile(in_log_file):
    logger.info(f"Downloading file {in_gz_file}")
    p = subprocess.Popen(f"curl https://zenodo.org/record/3227177/files/{in_gz_file} --output {in_gz_file}", shell=True)
    p.wait()
    logger.info(f"Extracting file {in_gz_file}")
    p = subprocess.Popen(f"tar -xvzf {in_gz_file}", shell=True)
    p.wait()

template_miner = TemplateMiner()

line_count = 0
start_time = time.time()
batch_size = 10000
with open(in_log_file) as f:
    for line in f:
        line = line.rstrip()
        line = line.partition(": ")[2]
        result = template_miner.add_log_message(line)
        line_count += 1
        if line_count % batch_size == 0:
            time_took = time.time() - start_time
            rate = batch_size / time_took
            logger.info(f"Processing line: {line_count}, rate {rate:.1f} lines/sec, "
                        f"{len(template_miner.drain.clusters)} clusters so far.")
            start_time = time.time()
        if result["change_type"] != "none":
            result_json = json.dumps(result)
            logger.info("Input:  " + line)
            logger.info("Result: " + result_json)

logger.info("---- Done processing file ---")
logger.info("Clusters:")
sorted_clusters = sorted(template_miner.drain.clusters, key=lambda it: it.size, reverse=True)
for cluster in sorted_clusters:
    logger.info(cluster)

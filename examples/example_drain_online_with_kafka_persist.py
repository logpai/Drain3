import os
from drain3_online import LogParserOnline

env_kafka_servers = "decorus_kafka_servers"
env_tenant_id = "decorus_tenant_id"
topic_name_prefix = "template_miner_snapshot_"

servers = os.environ.get(env_kafka_servers, "localhost:9092")
server_list = servers.split(",")
tenant_id = os.environ.get(env_tenant_id, "a1")
#if tenant_id is None:
#   raise RuntimeError(f"env variable: '{app_config.env_decorus_tenant_id}' does not exist")

topic = topic_name_prefix + tenant_id
print("Kafka servers = " + str(server_list) + "\nKafka topic = " + str(topic))
log_parser = LogParserOnline("KAFKA", server_list, topic) 
log_parser.start()



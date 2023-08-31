# SPDX-License-Identifier: MIT

from typing import Any, cast, Optional

import kafka  # type: ignore[import]

from drain3.persistence_handler import PersistenceHandler


class KafkaPersistence(PersistenceHandler):

    def __init__(self, topic: str, snapshot_poll_timeout_sec: int = 60, **kafka_client_options: Any) -> None:
        self.topic = topic
        self.kafka_client_options = kafka_client_options
        self.producer = kafka.KafkaProducer(**self.kafka_client_options)
        self.snapshot_poll_timeout_sec = snapshot_poll_timeout_sec

    def save_state(self, state: bytes) -> None:
        self.producer.send(self.topic, value=state)

    def load_state(self) -> Optional[bytes]:
        consumer = kafka.KafkaConsumer(**self.kafka_client_options)
        partition = kafka.TopicPartition(self.topic, 0)
        consumer.assign([partition])
        end_offsets = consumer.end_offsets([partition])
        end_offset = list(end_offsets.values())[0]
        if end_offset > 0:
            consumer.seek(partition, end_offset - 1)
            snapshot_poll_timeout_ms = self.snapshot_poll_timeout_sec * 1000
            records = consumer.poll(snapshot_poll_timeout_ms)
            if not records:
                raise RuntimeError(f"No message received from Kafka during restore even though end_offset>0")
            last_msg = records[partition][0]
            state = cast(bytes, last_msg.value)
        else:
            state = None

        consumer.close()
        return state

# SPDX-License-Identifier: MIT

from typing import Optional, Union

import redis

from drain3.persistence_handler import PersistenceHandler


class RedisPersistence(PersistenceHandler):
    def __init__(self,
                 redis_host: str,
                 redis_port: int,
                 redis_db: int,
                 redis_pass: Optional[str],
                 is_ssl: bool,
                 redis_key: Union[bytes, str, memoryview]) -> None:
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self.redis_pass = redis_pass
        self.is_ssl = is_ssl
        self.redis_key = redis_key
        self.r = redis.Redis(host=self.redis_host,
                             port=self.redis_port,
                             db=self.redis_db,
                             password=self.redis_pass,
                             ssl=self.is_ssl)

    def save_state(self, state: bytes) -> None:
        self.r.set(self.redis_key, state)

    def load_state(self) -> Optional[bytes]:
        return self.r.get(self.redis_key)

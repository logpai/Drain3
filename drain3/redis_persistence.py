# SPDX-License-Identifier: MIT

import redis

from drain3.persistence_handler import PersistenceHandler


class RedisPersistence(PersistenceHandler):
    def __init__(self, redis_host, redis_port, redis_db, redis_pass, is_ssl, redis_key):
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

    def save_state(self, state):
        self.r.set(self.redis_key, state)

    def load_state(self):
        return self.r.get(self.redis_key)

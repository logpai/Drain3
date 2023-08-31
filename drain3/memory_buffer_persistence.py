# SPDX-License-Identifier: MIT

from typing import Optional

from drain3.persistence_handler import PersistenceHandler


class MemoryBufferPersistence(PersistenceHandler):
    def __init__(self) -> None:
        self.state: Optional[bytes] = None

    def save_state(self, state: bytes) -> None:
        self.state = state

    def load_state(self) -> Optional[bytes]:
        return self.state
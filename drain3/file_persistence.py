# SPDX-License-Identifier: MIT

import os
import pathlib
from typing import Optional

from drain3.persistence_handler import PersistenceHandler


class FilePersistence(PersistenceHandler):
    def __init__(self, file_path: str) -> None:
        self.file_path = file_path

    def save_state(self, state: bytes) -> None:
        pathlib.Path(self.file_path).write_bytes(state)

    def load_state(self) -> Optional[bytes]:
        if not os.path.exists(self.file_path):
            return None

        return pathlib.Path(self.file_path).read_bytes()

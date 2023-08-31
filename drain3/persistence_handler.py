# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod
from typing import Optional


class PersistenceHandler(ABC):

    @abstractmethod
    def save_state(self, state: bytes) -> None:
        pass

    @abstractmethod
    def load_state(self) -> Optional[bytes]:
        pass

# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod


class PersistenceHandler(ABC):

    @abstractmethod
    def save_state(self, state):
        pass

    @abstractmethod
    def load_state(self):
        pass

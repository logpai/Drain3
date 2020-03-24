"""
Description : This file implements an abstract class for implementing a Drain3 persistence handler
Author      : David Ohana
Author_email: david.ohana@ibm.com
License     : MIT
"""
from abc import ABC, abstractmethod


class PersistenceHandler(ABC):

    @abstractmethod
    def save_state(self, state):
        pass

    @abstractmethod
    def load_state(self):
        pass

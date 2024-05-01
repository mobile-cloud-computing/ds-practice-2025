import logging
import random


class NodeState:
    def __init__(self, node):
        self.node = node
        self.logger = logging.getLogger(f'{self.__class__.__name__}')

    def handle_vote_request(self, message):
        raise NotImplementedError

    def handle_append_entries(self, message):
        raise NotImplementedError

    def handle_timeout(self):
        raise NotImplementedError

    @staticmethod
    def _random_timeout():
        return random.uniform(150, 300) / 1000.0

    @staticmethod
    def _static_timeout():
        return 0.5

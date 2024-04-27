import random
import threading

from states.follower import Follower

class Node:
    def __init__(self, node_id, nodes):
        self.node_id = node_id
        self.nodes = nodes

        self.log = []

        self.commit_index = 0
        self.current_term = 0

        self.state = Follower(self)

        self.timer = threading.Timer(self._random_timeout(), self.start_election)

    @staticmethod
    def _random_timeout():
        return random.uniform(150, 300) / 1000.0

    def become(self, role):
        self.timer.cancel()
        self.state = role(self)
        self.timer = threading.Timer(self._random_timeout(), self.handle_timeout)
        self.timer.start()

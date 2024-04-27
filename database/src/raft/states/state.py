class NodeState:
    def __init__(self, node):
        self.node = node

    def handle_message(self, message):
        raise NotImplementedError

    def _receive_heartbeat(self):
        raise NotImplementedError

    def handle_timeout(self):
        raise NotImplementedError
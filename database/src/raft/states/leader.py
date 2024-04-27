from state import NodeState


class Leader(NodeState):
    def handle_message(self, message):
        # handle leader-specific messages
        pass

    def send_heartbeats(self):
        # logic to send heartbeats to followers
        pass
from state import NodeState


class Candidate(NodeState):
    def __init__(self, node):
        super().__init__(node)
        self.start_election()

    def handle_message(self, message):
        # handle candidate-specific messages
        pass

    def start_election(self):
        self.node.current_term += 1
        # election logic
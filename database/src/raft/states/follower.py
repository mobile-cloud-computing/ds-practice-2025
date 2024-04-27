from state import NodeState
from canditate import Candidate


class Follower(NodeState):
    def handle_message(self, message):
        if message.type == 'AppendEntries':
            self.node.reset_election_timer()

        elif message.type == 'Timeout':
            self.node.change_state(Candidate)

    def handle_timeout(self):
        self.node.become(Candidate)
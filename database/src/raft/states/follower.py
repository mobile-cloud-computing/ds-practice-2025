from .canditate import Candidate
from .state import NodeState

from ..proto import raft_pb2


class Follower(NodeState):

    def handle_vote_request(self, message):
        self.logger.info(f"Node {self.node.node_id} received RequestVote RPC with term {message.term}")

        if message.term < self.node.term:
            return raft_pb2.RequestVoteResponse(term=self.node.term, granted=False)

        elif message.term > self.node.term:
            self.node.term = message.term
            self.node.voted_for = None

        if self.node.voted_for is not None and self.node.voted_for != message.candidate_id:
            return raft_pb2.RequestVoteResponse(term=self.node.term, granted=False)

        if message.last_log_term < self.node.get_last_log_term() or (
                message.last_log_term == self.node.get_last_log_term() and message.last_log_index < self.node.get_last_log_index()):
            return raft_pb2.RequestVoteResponse(term=self.node.term, granted=False)

        self.node.voted_for = message.candidate_id
        return raft_pb2.RequestVoteResponse(term=self.node.term, granted=True)

    def handle_timeout(self):
        self.logger.info('Follower timeout, transitioning to Candidate')
        self.node.change_state(Candidate)

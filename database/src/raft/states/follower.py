from .state import NodeState

from ..proto import raft_pb2


class Follower(NodeState):

    def timeout(self):
        return self._random_timeout()

    def handle_vote_request(self, message):
        self.logger.info(f"Node {self.node.node_id} received RequestVote RPC with term {message.term}")

        if message.term < self.node.term:
            return raft_pb2.RequestVoteResponse(term=self.node.term, granted=False)

        elif message.term > self.node.term:
            self.node.term = message.term
            self.node.voted_for = None
            self.node.change_state(Follower)

        if self.node.voted_for is not None and self.node.voted_for != message.candidate_id:
            return raft_pb2.RequestVoteResponse(term=self.node.term, granted=False)

        if message.last_log_term < self.get_last_log_term() or (
                message.last_log_term == self.get_last_log_term() and message.last_log_index < self.get_last_log_index()):
            return raft_pb2.RequestVoteResponse(term=self.node.term, granted=False)

        self.node.voted_for = message.candidate_id
        return raft_pb2.RequestVoteResponse(term=self.node.term, granted=True)

    def handle_append_entries(self, message):
        self.logger.debug(
            f"Received AppendEntries RPC term: {message.term} from {message.leader_id} with {message.entries}, prev_index: {message.previous_log_index} and prev_term: {message.previous_log_term}")

        if message.term < self.node.term:
            self.logger.debug(f"Responded with False")
            return raft_pb2.AppendEntriesResponse(term=self.node.term, success=False)

        if message.term > self.node.term:
            self.node.term = message.term
            self.node.voted_for = None
            self.node.change_state(Follower)

        # if self.get_last_log_index() <= message.previous_log_index or self.node.log[message.previous_log_index][
        #     'term'] != message.previous_log_term:
        #     self.logger.debug(f"Responded with False (log)")
        #     return raft_pb2.AppendEntriesResponse(term=self.node.term, success=False)

        if message.entries:
            # TODO: Handle appending entries to log
            pass

        if message.commit_index > self.node.commit_index:
            self.node.commit_index = min(message.commit_index, len(self.node.log) - 1)

        self.logger.debug(f"Responded with True")
        self.node.reset_timer()
        return raft_pb2.AppendEntriesResponse(term=self.node.term, success=True)

    def handle_timeout(self):
        self.logger.info('Follower timeout, transitioning to Candidate')
        from .candidate import Candidate
        self.node.change_state(Candidate)

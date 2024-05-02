import concurrent.futures
import threading

from .state import NodeState
from ..proto import raft_pb2


class Candidate(NodeState):
    def __init__(self, node):
        super().__init__(node)
        self.node.voted_for = None
        self.node.cancel_timer()
        self._start_election()

    def timeout(self):
        return self._random_timeout()

    def handle_timeout(self):
        self.logger.info('Candidate timeout, starting new election')
        self.node.change_state(Candidate)

    def handle_vote_request(self, message):
        """Handle RequestVote gRPC messages from other candidates."""

        self.logger.debug(f"Node {self.node.node_id} received RequestVote RPC with term {message.term}")

        if message.term < self.node.term:
            return raft_pb2.RequestVoteResponse(term=self.get_last_log_term(), granted=False)

        if message.term > self.node.term:
            self.node.term = message.term
            self.node.voted_for = None
            from .follower import Follower
            self.node.change_state(Follower)

        if self.node.voted_for is not None and self.node.voted_for != message.candidate_id:
            return raft_pb2.RequestVoteResponse(term=self.get_last_log_term(), granted=False)

        if message.last_log_term < self.get_last_log_term() or (
                message.last_log_term == self.get_last_log_term() and message.last_log_index < self.get_last_log_index()):
            return raft_pb2.RequestVoteResponse(term=self.node.term, granted=False)

        self.node.voted_for = message.candidate_id
        from .follower import Follower
        self.node.change_state(Follower)
        return raft_pb2.RequestVoteResponse(term=self.node.term, granted=True)

    def handle_append_entries(self, message):
        self.logger.debug(
            f"Candidate (term: {self.node.term}) received AppendEntries RPC {message.term} from {message.leader_id} with {message.entries}, prev_index: {message.previous_log_index} and prev_term: {message.previous_log_term}")

        if message.term < self.node.term:
            return raft_pb2.AppendEntriesResponse(term=self.node.term, success=False)

        if message.term >= self.node.term:
            self.node.term = message.term
            self.node.voted_for = None
            from .follower import Follower
            self.node.change_state(Follower)

        # TODO: Missing log, entries and commit index handling.
        self.node.reset_timer()
        return raft_pb2.AppendEntriesResponse(term=self.node.term, success=True)

    def _start_election(self):
        self.logger.info(f'Node {self.node.node_id} starting election term {self.node.term}.')
        self.node.term += 1
        self.node.voted_for = self.node.node_id

        self.votes_received = 1

        self.node.cancel_timer()
        self.node.timer = threading.Timer(self._random_timeout(), self._on_election_timeout)
        self.node.timer.start()

        # TODO: Important! This also sends a vote request to itself, if self.node.peers has itself listed.
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.node.peers)) as executor:
            futures = {executor.submit(self.node.send_message, peer, raft_pb2.RequestVoteRequest(
                term=self.node.term,
                candidate_id=self.node.node_id,
                last_log_index=self.get_last_log_index(),
                last_log_term=self.get_last_log_term()
            )): peer for peer in self.node.peers}

            for future in concurrent.futures.as_completed(futures):
                peer = futures[future]
                try:
                    response = future.result()
                    if response is not None and response.granted:
                        self.node.logger.debug(f"Received vote from {peer}")
                        self.votes_received += 1

                except Exception as exc:
                    self.node.logger.debug(f'Vote request to {peer} generated an exception: {exc}')

    def _on_election_timeout(self):
        peer_count = len(self.node.peers) + 1
        majority = (peer_count // 2) + 1

        self.logger.debug(f"Election timeout reached with {self.votes_received}/{majority} votes")

        if self.votes_received < majority:
            self.logger.info(
                f"Node {self.node.node_id} election term {self.node.term} failed with {self.votes_received}/{majority} votes, restarting election.")
            self.handle_timeout()

        else:
            from .leader import Leader
            self.node.change_state(Leader)

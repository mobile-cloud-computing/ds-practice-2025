import concurrent.futures
import threading

from .leader import Leader
from .state import NodeState
from ..proto import raft_pb2


class Candidate(NodeState):
    def __init__(self, node):
        super().__init__(node)
        self.node.voted_for = None
        self.node.cancel_timer()
        self._start_election()

    def handle_timeout(self):
        self.logger.info('Candidate timeout, starting new election')
        self.node.change_state(Candidate)

    def handle_vote_request(self, message):
        self.logger.info(f"Node {self.node.node_id} received RequestVote RPC with term {message.term}")

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
                last_log_index=self.node.get_last_log_index(),
                last_log_term=self.node.get_last_log_term()
            )): peer for peer in self.node.peers}

            for future in concurrent.futures.as_completed(futures):
                peer = futures[future]
                try:
                    response = future.result()
                    if response is not None and response.granted:
                        self.node.logger.debug(f"Received vote from {peer}")
                        self.votes_received += 1
                        
                except Exception as exc:
                    self.node.logger.error(f'Vote request to {peer} generated an exception: {exc}')

    def _on_election_timeout(self):
        peer_count = len(self.node.peers) + 1
        majority = (peer_count // 2) + 1

        self.logger.debug(f"Election timeout reached with {self.votes_received}/{majority} votes")

        if self.votes_received < majority:
            self.logger.info(
                f"Node {self.node.node_id} election term {self.node.term} failed with {self.votes_received}/{majority} votes, restarting election.")
            self.handle_timeout()

        else:
            self.node.change_state(Leader)

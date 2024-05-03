import concurrent.futures
import threading

from .state import NodeState
from ..proto import raft_pb2


class Candidate(NodeState):
    def __init__(self, node):
        super().__init__(node)
        # self.node.voted_for = None
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

        # TODO: This is a very big bandaid around thread timing issues.
        if not isinstance(self.node.state, Candidate):
            self.logger.debug("Node is no longer a candidate, ignoring vote request.")
            return

        # Update term if the incoming term is higher and reset state
        if message.term > self.node.term:
            self.logger.debug(f"Request term {message.term} higher than mine {self.node.term}. Changing to follower.")
            self.node.term = message.term
            self.node.voted_for = None
            self.node.leader_id = None
            from .follower import Follower
            self.node.change_state(Follower)

            return self.node.state.handle_vote_request(message)

        # Reject if the incoming term is lower
        if message.term < self.node.term:
            self.logger.debug(
                f"Rejecting RequestVote RPC from outdated term {message.term} node {message.candidate_id}. Current term is {self.node.term}.")
            return raft_pb2.RequestVoteResponse(term=self.node.term, granted=False)

        # Check log freshness
        if (message.last_log_term < self.get_last_log_term() or
                (
                        message.last_log_term == self.get_last_log_term() and message.last_log_index < self.get_last_log_index())):
            self.logger.debug(
                f"Rejecting RequestVote RPC from {message.candidate_id} due to log freshness. Term: {message.last_log_term} < {self.get_last_log_term()}. Index: {message.last_log_index} < {self.get_last_log_index()}")
            return raft_pb2.RequestVoteResponse(term=self.node.term, granted=False)

        # Vote granting conditions
        if self.node.voted_for is None or self.node.voted_for == message.candidate_id:
            self.logger.debug(f"Granting vote to {message.candidate_id}")
            self.node.voted_for = message.candidate_id
            self.node.reset_timer()
            return raft_pb2.RequestVoteResponse(term=self.node.term, granted=True)

        self.logger.debug(f"Node has voted for {self.node.voted_for} already.")
        return raft_pb2.RequestVoteResponse(term=self.node.term, granted=False)

    def handle_append_entries(self, message):
        self.logger.debug(
            f"Received AppendEntries RPC term: {message.term} from {message.leader_id} with {message.entries}, prev_index: {message.previous_log_index} and prev_term: {message.previous_log_term}")

        # Reply false if term < currentTerm (§5.1)
        if message.term < self.node.term:
            self.logger.debug(
                f"Rejecting AppendEntries RPC from outdated term {message.term}. Current term is {self.node.term}.")
            return raft_pb2.AppendEntriesResponse(term=self.node.term, success=False)

        self.node.leader_id = message.leader_id
        self.node.reset_timer()

        # If RPC request or response contains term T > currentTerm:
        #   set currentTerm = T, convert to follower (§5.1)
        if message.term > self.node.term:
            self.logger.debug(f"Request term {message.term} higher than mine {self.node.term}")
            self.node.term = message.term
            self.node.voted_for = None
            from .follower import Follower
            self.node.change_state(Follower)

            return self.node.state.handle_append_entries(message)

        # If an existing entry conflicts with a new one (same index but different terms), delete the existing entry and all that
        # follow it (§5.3).
        if self.get_last_log_index() > message.previous_log_index and self.node.log[message.previous_log_index][
            'term'] != message.previous_log_term:
            # This handles a case where local log is bigger than remote, in which case the local log should be truncated.
            self.logger.debug(
                f"Log inconsistency detected at local/remote index {self.get_last_log_index()}/{message.previous_log_index}. Truncating log and rejecting AppendEntries.")
            self.node.log = self.node.log[:message.previous_log_index]
            return raft_pb2.AppendEntriesResponse(term=self.node.term, success=False)
        elif self.get_last_log_index() < message.previous_log_index:
            # This handles a case where local log is much smaller than remote, in which case the remote tracker should be notified to reduce the counts.
            self.logger.debug(
                f"Log inconsistency detected at local/remote index {self.get_last_log_index()}/{message.previous_log_index}. Truncating log and rejecting AppendEntries.")
            return raft_pb2.AppendEntriesResponse(term=self.node.term, success=False)

        # Append any new entries not already in the log.
        if message.entries:
            self.logger.debug(f"Appending {len(message.entries)} to local log.")
            self.node.log.extend(self._convert_log_entries(message.entries))

        # If leaderCommit > commitIndex, set commitIndex = min(leaderCommit, index of last new entry)
        if message.commit_index > self.node.commit_index:
            self.node.commit_index = min(message.commit_index, len(self.node.log) - 1)
            self.logger.debug(
                f"Commit index updated to {self.node.commit_index} based on leader's commit index {message.commit_index}.")

        self.logger.debug(
            f"AppendEntries RPC processed successfully. Commit index is now {self.node.commit_index}, last_log_term ({self.get_last_log_term()}), last_log_index ({self.get_last_log_index()}).")

        # TODO: State machine commit.

        return raft_pb2.AppendEntriesResponse(term=self.node.term, success=True)

    def append_log(self, command):
        if self.node.leader_id:
            return self.node.forward_to_leader(command)

        else:
            return raft_pb2.RaftClientStatus(error=True, leader_id=self.node.leader_id,
                                             message="Election in progress, try again later.")

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

        # TODO: This is a very big bandaid around thread timing issues.
        if not isinstance(self.node.state, Candidate):
            self.logger.debug("Node is no longer a candidate, ignoring election timeout.")
            return

        if self.votes_received < majority:
            self.logger.info(
                f"Node {self.node.node_id} election term {self.node.term} failed with {self.votes_received}/{majority} votes, restarting election.")
            self.handle_timeout()

        else:
            from .leader import Leader
            self.node.change_state(Leader)

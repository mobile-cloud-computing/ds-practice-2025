import concurrent.futures
from .state import NodeState
from ..proto import raft_pb2


class Leader(NodeState):
    def __init__(self, node):
        super().__init__(node)
        self._append_entries()

    def timeout(self):
        return self._static_timeout()

    def handle_append_entries(self, request):
        """
        Handle incoming AppendEntries RPCs at the leader. Leaders typically don't expect to receive these,
        but they may if there is a network partition or misconfiguration.
        """
        # Check the term of the incoming request to see if it's from a newer leader
        if request.term > self.node.term:
            self.logger.info(
                f"Received AppendEntries with higher term ({request.term}) than current ({self.node.term}). Stepping down to follower.")
            self.node.term = request.term
            self.node.voted_for = None
            from .follower import Follower
            self.node.change_state(Follower)
            return raft_pb2.AppendEntriesResponse(term=self.node.term, success=True)

        # If the terms match, it might just be a duplicated message; respond accordingly
        elif request.term == self.node.term:
            self.logger.warning(
                "Received AppendEntries from another leader with the same term. Responding failure to clarify leadership.")
            return raft_pb2.AppendEntriesResponse(term=self.node.term, success=False)

        # If the term is older, simply reject the request
        else:
            return raft_pb2.AppendEntriesResponse(term=self.node.term, success=False)

    def handle_vote_request(self, request):
        """
        Handles incoming RequestVote RPCs at the leader. Leaders might grant votes if they encounter
        a candidate with a higher term.
        """
        # If the request comes from a candidate with a higher term, step down and consider the vote
        if request.term > self.node.term:
            self.logger.info(
                f"Received RequestVote with higher term ({request.term}) than current ({self.node.term}). Stepping down to follower and granting vote.")
            self.node.term = request.term
            self.node.voted_for = request.candidate_id
            from .follower import Follower
            self.node.change_state(Follower)
            return raft_pb2.RequestVoteResponse(term=self.node.term, granted=True)

        # Otherwise, do not grant vote
        return raft_pb2.RequestVoteResponse(term=self.node.term, granted=False)

    def handle_timeout(self):
        self._append_entries()
        self.node.reset_timer()

    def _append_entries(self, entries=None):
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.node.peers)) as executor:
            message = raft_pb2.AppendEntriesRequest(
                term=self.node.term,
                leader_id=self.node.node_id,
                previous_log_index=self.get_last_log_index(),
                entries=entries or [],
                previous_log_term=self.get_last_log_term(),
                commit_index=self.node.commit_index
            )

            futures = {executor.submit(self.node.send_message, peer, message): peer for peer in self.node.peers}

        successful_responses = 0
        for future in concurrent.futures.as_completed(futures):
            peer = futures[future]
            try:
                response = future.result()
                if response and response.success:
                    successful_responses += 1
                    self.logger.debug(f"Successfully replicated entry to {peer} (term {self.node.term}).")
                else:
                    print(response.term, response.success)
                    self.logger.warning(f"Failed to replicate entry to {peer}. Response: {response}")

            except Exception as e:
                self.logger.error(f"RPC call failed for {peer} with error: {e}")

        if successful_responses > len(self.node.peers) // 2:
            if entries:
                if self.get_last_log_index() > self.node.commit_index:
                    self.node.commit_index = self.get_last_log_index()
                    self.logger.info(
                        f"Entries successfully replicated to majority; commit index updated to {self.node.commit_index}.")

        else:
            self.logger.warning("Failed to achieve majority replication for new entries.")

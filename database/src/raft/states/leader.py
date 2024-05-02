import concurrent.futures

from .state import NodeState
from ..proto import raft_pb2


class Leader(NodeState):
    def __init__(self, node):
        super().__init__(node)

        # Track log consistency of the peers
        self.next_index = {peer: len(node.log) for peer in node.peers}
        self.match_index = {peer: 0 for peer in node.peers}

        self._append_entries()

    def timeout(self):
        return self._static_timeout()

    def handle_append_entries(self, message):
        """
        Handle incoming AppendEntries RPCs at the leader. Leaders typically don't expect to receive these,
        but they may if there is a network partition or misconfiguration.
        """
        # Check the term of the incoming request to see if it's from a newer leader
        if message.term > self.node.term:
            self.logger.info(
                f"Received AppendEntries with higher term ({message.term}) than current ({self.node.term}). Stepping down to follower.")
            self.node.term = message.term
            self.node.voted_for = None
            from .follower import Follower
            self.node.change_state(Follower)
            return raft_pb2.AppendEntriesResponse(term=self.node.term, success=True)

        # If the terms match, it might just be a duplicated message; respond accordingly
        elif message.term == self.node.term:
            self.logger.warning(
                "Received AppendEntries from another leader with the same term. Responding failure to clarify leadership.")
            return raft_pb2.AppendEntriesResponse(term=self.node.term, success=False)

        # If the term is older, simply reject the request
        else:
            return raft_pb2.AppendEntriesResponse(term=self.node.term, success=False)

    def handle_vote_request(self, message):
        """
        Handles incoming RequestVote RPCs at the leader. Leaders might grant votes if they encounter
        a candidate with a higher term.
        """
        # If the request comes from a candidate with a higher term, step down and consider the vote
        if message.term > self.node.term:
            self.logger.info(
                f"Received RequestVote with higher term ({message.term}) than current ({self.node.term}). Stepping down to follower and granting vote.")
            self.node.term = message.term
            self.node.voted_for = message.candidate_id
            from .follower import Follower
            self.node.change_state(Follower)

            return self.node.state.handle_vote_request(message)

        # Otherwise, do not grant vote
        return raft_pb2.RequestVoteResponse(term=self.node.term, granted=False)

    def handle_timeout(self):
        # TODO: This is a very big bandaid around thread timing issues.
        if not isinstance(self.node.state, Leader):
            self.logger.debug("Node is no longer a Leader, ignoring election timeout.")
            return

        self._append_entries()
        self.node.reset_timer()

    def _append_entries(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.node.peers)) as executor:
            futures = {}
            for peer in self.node.peers:
                next_idx = self.next_index[peer]
                prev_log_index = next_idx - 1
                prev_log_term = self.node.log[prev_log_index]['term'] if prev_log_index >= 0 else 0
                entries = [raft_pb2.LogEntry(term=entry['term'], command=raft_pb2.Command(operation=entry['command']['operation'],
                                                                                          key=entry['command']['key'],
                                                                                          value=entry['command']['value'])) for entry in
                           self.node.log[next_idx:]] if next_idx < len(self.node.log) else []

                self.logger.debug(
                    f"AppendEntries to peer {peer} with message parameters - {self.node.term} {self.node.node_id} {prev_log_index} {prev_log_term} {entries} {self.node.commit_index}")

                message = raft_pb2.AppendEntriesRequest(
                    term=self.node.term,
                    leader_id=self.node.node_id,
                    previous_log_index=prev_log_index,
                    previous_log_term=prev_log_term,
                    entries=entries,
                    commit_index=self.node.commit_index
                )

                futures[executor.submit(self.node.send_message, peer, message)] = peer

                for future in concurrent.futures.as_completed(futures):
                    peer = futures[future]
                    try:
                        response = future.result()
                        if response and response.success:
                            self.next_index[peer] = max(self.next_index[peer], len(entries) + prev_log_index + 1)
                            self.match_index[peer] = self.next_index[peer] - 1
                        else:
                            self.next_index[peer] -= 1
                    except Exception as e:
                        self.node.logger.error(f"RPC call failed for {peer} with error: {e}")

                # if len(entries) > 0:
                all_match_indices = list(self.match_index.values())
                all_match_indices.append(len(self.node.log) - 1)  # Include the leader's last index
                new_commit_index = self._find_majority_match(all_match_indices)
                if new_commit_index > self.node.commit_index:
                    self.node.commit_index = new_commit_index
                    self.logger.info(f"Commit index updated to {self.node.commit_index}")

    def _find_majority_match(self, indices):
        # Find the highest log index replicated on the majority of servers
        sorted_indices = sorted(indices, reverse=True)
        majority_index = sorted_indices[len(sorted_indices) // 2]
        return majority_index

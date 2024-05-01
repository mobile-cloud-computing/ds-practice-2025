import logging
import random
import sys
import threading

import grpc

from .proto import raft_pb2_grpc, raft_pb2
from .states.follower import Follower

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')


class Node:
    def __init__(self, node_id, peers):
        self.node_id = node_id
        self.peers = peers

        self.logger = logging.getLogger('Node')

        self.log = []
        self.log_lock = threading.RLock()

        self.commit_index = 0
        self.term = 0
        self.voted_for = None

        self.state = Follower(self)

        self.timer = threading.Timer(self._random_timeout(), self.state.handle_timeout)
        self.timer.start()

        self.lock = threading.Lock()
        self.stop_requested = threading.Event()

        self.logger.info(f"Starting Raft node {self.node_id} with peers {self.peers}")

    @staticmethod
    def _random_timeout():
        """Return a random timeout between 150 and 300 ms."""
        return random.uniform(150, 300) / 1000.0

    @staticmethod
    def _static_timeout():
        """Return a random timeout between 150 and 300 ms."""
        return 0.5

    def change_state(self, new_state):
        """Change the state to another state class."""
        if self.stop_requested.is_set():
            self.logger.info("Stop request has been given, stopping..")
            sys.exit(1)

        with self.lock:
            self.cancel_timer()

            self.logger.info(f"Changing {self.state.__class__.__name__} state to {new_state.__name__}")

            self.state = new_state(self)
            self.timer = threading.Timer(self._random_timeout(), self.state.handle_timeout)
            self.timer.start()

    def reset_timer(self):
        """Restart the timeout timer."""
        if self.stop_requested.is_set():
            self.logger.info("Stop request has been given, stopping..")
            sys.exit(1)

        with self.lock:
            self.cancel_timer()

            self.timer = threading.Timer(self._random_timeout(), self.state.handle_timeout)
            self.timer.start()

            self.logger.debug(f"Timer reset by {self.state.__class__.__name__}")

    def cancel_timer(self):
        """Cancel timeout timers if set."""
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None

    def send_message(self, peer, message):
        """Send a message to a peer using gRPC."""
        with grpc.insecure_channel(f'{peer}') as channel:
            stub = raft_pb2_grpc.RaftStub(channel)

            try:
                if isinstance(message, raft_pb2.RequestVoteRequest):
                    response = stub.RequestVote(message, self._static_timeout())
                elif isinstance(message, raft_pb2.AppendEntriesRequest):
                    response = stub.AppendEntries(message, self._static_timeout())
                else:
                    self.logger.fatal("Unknown message type.")
                    sys.exit(1)

            except grpc.RpcError as e:
                self.logger.warning(f"Failed sending message to {peer}: {e}")
                return None

            return response

    def get_last_log_index(self):
        """Retrieve the index of the last entry in the log."""
        with self.log_lock:
            return len(self.log) if len(self.log) != 0 else -1

    def get_last_log_term(self):
        """Retrieve the term of the last entry in the log."""
        with self.log_lock:
            return self.log[-1]['term'] if len(self.log) != 0 else 0

    # TODO: Maybe convert this to a node state? E.g. state: shutdown
    def terminate(self, server, signum):
        self.logger.info(f"Signal {signum} received, stopping node")
        self.stop_requested.set()
        server.stop(5)

from concurrent import futures

import grpc

from raft.proto import raft_pb2
from raft.proto.raft_pb2_grpc import RaftServicer, add_RaftServicer_to_server
from raft.states.follower import Follower


class RaftDebugService(RaftServicer):
    def __init__(self):
        self.node = Follower(self)

    def AppendEntries(self, request, context):
        # Delegates to the state's specific method
        print(request, context)
        return raft_pb2.RequestVoteResponse()

    def RequestVote(self, request, context):
        # Delegates to the state's specific method
        print(request, context)
        return raft_pb2.RequestVoteResponse(term=0, granted=True)


if __name__ == "__main__":
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    add_RaftServicer_to_server(RaftDebugService(), server)

    server.add_insecure_port('0.0.0.0:50061')
    server.start()
    server.wait_for_termination()

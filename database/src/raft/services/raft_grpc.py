import signal
from concurrent import futures

import grpc

from ..node import Node
from ..proto.raft_pb2_grpc import RaftServicer, add_RaftServicer_to_server


class RaftService(RaftServicer):
    def __init__(self, node_id, nodes, server):
        self.node = Node(node_id, nodes)

        signal.signal(signal.SIGTERM, lambda signum, frame: self.node.terminate(server, signum))
        signal.signal(signal.SIGINT, lambda signum, frame: self.node.terminate(server, signum))

    def AppendEntries(self, request, context):
        return self.node.state.handle_append_entries(request)

    def RequestVote(self, request, context):
        return self.node.state.handle_vote_request(request)

    # Trigger with: grpcurl -proto raft.proto -import-path raft/proto/ -d '{}' -plaintext (hostname).local:50062 raft.Raft/StateMachineInfo
    def StateMachineInfo(self, request, context):
        return self.node.state_machine_info()

    def WriteCommand(self, request, context):
        return self.node.write_command(request)


def _start_raft(node_id, nodes, port=50060):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    serv = RaftService(node_id, nodes, server)
    add_RaftServicer_to_server(serv, server)

    server.add_insecure_port(f'0.0.0.0:{port}')
    server.start()
    server.wait_for_termination()

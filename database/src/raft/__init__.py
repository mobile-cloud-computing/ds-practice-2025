from .node import Node
from .services.raft_grpc import _start_raft


def start(node_id, nodes, port):
    return _start_raft(node_id, nodes, port)

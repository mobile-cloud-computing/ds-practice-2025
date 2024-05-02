import socket

import raft

if __name__ == '__main__':
    node_id = "run"
    nodes = ["localhost:50061"]

    node = raft.start(node_id, nodes, "50062")

import os

import raft

if __name__ == '__main__':
    node_id = os.getenv('NODE_ID')
    nodes = os.getenv('NODES').split(',')
    port = "50060"

    node = raft.start(node_id, nodes, port)

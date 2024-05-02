import os

import raft

if __name__ == '__main__':
    node_id = os.getenv('NODE_ID')
    peers = os.getenv('PEERS').split(',')
    port = "50060"

    node = raft.start(node_id, peers, port)
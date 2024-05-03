import sys
from pathlib import Path

current_dir = Path(__file__).parent.absolute()
app_dir = current_dir.parent.parent
sys.path.insert(0, str(app_dir))

import signal
from concurrent import futures

import grpc

from ..node import Node
from ..proto.raft_pb2_grpc import RaftServicer, add_RaftServicer_to_server
from ..proto.raft_pb2 import *
from ..utils.logger import logger
import threading



logs = logger.get_module_logger("DATABASE")

class RaftService(RaftServicer):
    def __init__(self, node_id, nodes, server):
        self.node = Node(node_id, nodes)
        self.commit_lock = threading.Lock()
        self.commit_data = None


        signal.signal(signal.SIGTERM, lambda signum, frame: self.node.terminate(server, signum))
        signal.signal(signal.SIGINT, lambda signum, frame: self.node.terminate(server, signum))

    def AppendEntries(self, request, context):
        return self.node.state.handle_append_entries(request)

    def RequestVote(self, request, context):
        return self.node.state.handle_vote_request(request)

    # Trigger with: grpcurl -proto raft.proto -import-path raft/proto/ -d '{}' -plaintext (hostname).local:50062 raft.Raft/StateMachineInfo
    def StateMachineInfo(self, request, context):
        return self.node.state_machine_info()

    # Trigger with: grpcurl -proto raft.proto -import-path raft/proto/ -d '{"operation": "set", "key": "asd", "value": "value5"}' -plaintext (hostname).local:50062 raft.Raft/WriteCommand
    def WriteCommand(self, request, context):
        return self.node.write_command(request)

    def Request_Commit(self, request, context):
        logs.info("Request Commit triggered for id: %s", request.id)
        response = Response()
        if self.commit_lock.locked():
            response.status = False
            response.message = "Not ready to commit. Preoccupied with id" + str(self.commit_data)
        else:
            self.commit_lock.acquire()
            response.status = True
            response.message = "Ready to commit"
            self.commit_data = request.id

        return response
        
    def Commit(self, request: Commit_Message, context):
        logs.info("Commit triggered for id: %s", request.id)
        response = Response()

        if request.rollback:
            response.message = "Rolled back successfully"
            response.status = True
            self.commit_data = None
            self.commit_lock.release()
            return response 

        if request.id == self.commit_data:
            try:
                response.message = "Committed successfully"
                response.status = True
                self.commit_data = None
                self.commit_lock.release()
            except Exception as e:
                logs.error("Error during committing: %s", e)
                response.message = "Committing failed: " + str(e)
                response.status = False
        else:
            response.message = "Committing failed. Preoccupied with id" + str(self.commit_data)
            response.status = False 
        return response    


def _start_raft(node_id, nodes, port=50060):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    serv = RaftService(node_id, nodes, server)
    add_RaftServicer_to_server(serv, server)

    server.add_insecure_port(f'0.0.0.0:{port}')
    server.start()
    server.wait_for_termination()

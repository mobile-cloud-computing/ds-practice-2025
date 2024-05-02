import sys
from pathlib import Path
import os
import raft 

current_dir = Path(__file__).parent.absolute()
app_dir = current_dir.parent.parent
sys.path.insert(0, str(app_dir))
cache = {}



from utils.logger import logger
import grpc
from concurrent import futures
from utils.pb.database.database_pb2_grpc import *
from utils.vector_clock.vector_clock import VectorClock

logs = logger.get_module_logger("DB")

   # fraud_detection_grpc.add_HelloServiceServicer_to_server(HelloService(), server)
   # fraud_detection_grpc.add_FraudServiceServicer_to_server(FraudService(), server)



class DatabaseService(DatabaseServicer):
    def Read(self, request, context):
        logs.log("Read operation triggered")
    def Write(self, request, context):
        logs.log("Write operation triggered")
def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor())
    add_DatabaseServicer_to_server(DatabaseService(), server)
    port = "50054"
    server.add_insecure_port("[::]:" + port)
    server.start()
    logs.info(f"Server started. Listening on port {port}.")
    server.wait_for_termination()


if __name__ == '__main__':
    node_id = os.getenv('NODE_ID')
    peers = os.getenv('PEERS').split(',')
    port = "50060"

    node = raft.start(node_id, peers, port)

import sys
import os
import time
import threading
import grpc
from concurrent import futures
import logging

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
root_path = os.path.abspath(os.path.join(FILE, '../../..'))

sys.path.insert(0, os.path.join(root_path, 'utils/pb/executor'))
import executor_pb2 as executor_pb2
import executor_pb2_grpc as executor_grpc

sys.path.insert(0, os.path.join(root_path, 'utils/pb/order_queue'))
import order_queue_pb2 as order_queue
import order_queue_pb2_grpc as order_queue_grpc

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [Exec-%(name)s] %(message)s")
logger = logging.getLogger(__name__)
class ExecutorService(executor_grpc.ExecutorServiceServicer):
    def __init__(self, executor_id, known_ids, queue_host):
        self.id = int(executor_id)
        self.known_ids = [int(i) for i in known_ids.split(',')]
        self.queue_host = queue_host
        self.leader_id = None
        self.is_leader = False
        
        logger.name = str(self.id)
        logger.info(f"Initialized Executor {self.id}. Peers: {self.known_ids}")

    # --- gRPC Server Methods for Bully Algorithm ---
    def Election(self, request, context):
        """Responds to election messages from lower-ID nodes."""
        logger.info(f"Received ELECTION from {request.sender_id}")
        # If someone with a lower ID started an election, we answer OK and start our own
        if request.sender_id < self.id:
            threading.Thread(target=self.start_election).start()
        return executor_pb2.ElectionResponse(ok=True)

    def Coordinator(self, request, context):
        """Accepts the new leader."""
        self.leader_id = request.leader_id
        self.is_leader = (self.id == self.leader_id)
        logger.info(f"Node {request.leader_id} is the new COORDINATOR.")
        return executor_pb2.CoordinatorResponse(ok=True)

    def Heartbeat(self, request, context):
        """Simple health check response."""
        return executor_pb2.HeartbeatResponse(is_alive=True)

    # --- Active Logic ---
    def start_election(self):
        """Implements the Bully Algorithm election process."""
        logger.info("Starting ELECTION...")
        higher_nodes = [node for node in self.known_ids if node > self.id]
        
        if not higher_nodes:
            self.become_leader()
            return

        answers = 0
        for node_id in higher_nodes:
            try:
                # Assuming executors are available on internal network names like executor_1:50055
                with grpc.insecure_channel(f'executor_{node_id}:50055') as channel:
                    stub = executor_grpc.ExecutorServiceStub(channel)
                    response = stub.Election(executor_pb2.ElectionRequest(sender_id=self.id), timeout=2)
                    if response.ok:
                        answers += 1
            except grpc.RpcError:
                pass # Node is down
        
        if answers == 0:
            self.become_leader()
        else:
            logger.info("Higher node responded. Waiting for COORDINATOR message.")

    def become_leader(self):
        self.is_leader = True
        self.leader_id = self.id
        logger.info(f"*** I AM THE NEW LEADER ***")
        
        # Broadcast victory to all lower nodes
        lower_nodes = [node for node in self.known_ids if node < self.id]
        for node_id in lower_nodes:
            try:
                with grpc.insecure_channel(f'executor_{node_id}:50055') as channel:
                    stub = executor_grpc.ExecutorServiceStub(channel)
                    stub.Coordinator(executor_pb2.CoordinatorRequest(leader_id=self.id), timeout=2)
            except grpc.RpcError:
                pass

    def run_worker(self):
        """Background thread to process queue (if leader) or check health (if follower)."""
        # Initial election on startup
        time.sleep(2) # Wait for network to establish
        self.start_election()
        
        while True:
            time.sleep(5)
            if self.is_leader:
                self.process_queue()
            else:
                self.check_leader_health()

    def process_queue(self):
        """Dequeue and execute orders (Mutual Exclusion achieved by being the sole leader)."""
        try:
            with grpc.insecure_channel(self.queue_host) as channel:
                stub = order_queue_grpc.OrderQueueServiceStub(channel)
                response = stub.Dequeue(order_queue.DequeueRequest())
                if response.has_order:
                    logger.info(f">>> Executing Order: {response.order_id} <<<")
                    # Here you would actually do the stock updates, payment, etc.
        except grpc.RpcError as e:
            logger.error(f"Failed to connect to queue: {e}")

    def check_leader_health(self):
        if self.leader_id is None or self.leader_id == self.id:
            return
            
        try:
            with grpc.insecure_channel(f'executor_{self.leader_id}:50055') as channel:
                stub = executor_grpc.ExecutorServiceStub(channel)
                stub.Heartbeat(executor_pb2.HeartbeatRequest(leader_id=self.leader_id), timeout=2)
        except grpc.RpcError:
            logger.warning(f"Leader {self.leader_id} is down! Initiating election.")
            self.leader_id = None
            self.start_election()

def serve():
    executor_id = os.getenv("EXECUTOR_ID", "1")
    known_ids = os.getenv("KNOWN_IDS", "")
    queue_host = os.getenv("QUEUE_HOST", "order_queue:50054")

    service = ExecutorService(executor_id, known_ids, queue_host)
    
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    executor_grpc.add_ExecutorServiceServicer_to_server(service, server)
    server.add_insecure_port("[::]:50055") # Internal port for Bully communication
    server.start()
    
    # Start the active background thread
    threading.Thread(target=service.run_worker, daemon=True).start()
    
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
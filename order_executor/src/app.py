import os
import sys
import logging
import threading
import time
import grpc
from concurrent import futures
from google.protobuf.empty_pb2 import Empty

thread_pool = futures.ThreadPoolExecutor()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure gRPC stub path
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
order_executor_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/order_executor'))
sys.path.insert(0, order_executor_grpc_path)
order_queue_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/order_queue'))
sys.path.insert(0, order_queue_grpc_path)

import order_executor_pb2 as ox_pb2
import order_executor_pb2_grpc as ox_grpc
import order_queue_pb2 as oq_pb2
import order_queue_pb2_grpc as oq_grpc

### Threading ###
class WorkerThread(threading.Thread):
    def __init__(self, target, args=()):
        super().__init__()
        self._target = target
        self._args = args
        self.result = None

    def run(self):
        self.result = self._target(*self._args)

class OrderExecutorService(ox_grpc.OrderExecutorServiceServicer):
    """
    Order Executor Service:
    This replicated service uses a token ring for leader election to ensure only one executor processes an order.
    """

    def __init__(self):
        # Use EXECUTOR_ID to uniquely identify this instance.
        self.id = int(os.getenv("EXECUTOR_ID", "1"))
        replica_count = int(os.getenv("ORDER_EXECUTOR_REPLICAS", "1"))
        self.predecessor = self.id - 1 if self.id > 1 else replica_count
        self.successor = self.id + 1 if self.id < replica_count else 1

        def initiate_token_ring():
            time.sleep(5)  # Wait to ensure all replicas are up
            self.SendToken(Empty(), None)

        if self.id == 1:
            print(f"[OrderExecutor] Executor {self.id} initiating token ring.")
            thread_pool.submit(initiate_token_ring)

    @staticmethod
    def _executor_address(executor_id: int, with_port=False) -> str:
        return f"order_executor-{executor_id}" + (":50060" if with_port else "")

    def SendToken(self, request, context):
        print(f"[OrderExecutor] Executor {self.id} checking for new orders")
        with grpc.insecure_channel("order_queue:50054") as channel:
            stub = oq_grpc.OrderQueueServiceStub(channel)
            response: oq_pb2.OptionalOrder = stub.DequeueOrder(Empty())
        if not response.HasField("order"):
            logger.info(f"[OrderExecutor] Executor {self.id}: No orders available.")
            time.sleep(2)  # Delay to avoid excessive polling
        else:
            thread_pool.submit(self._simulate_order_processing, response.order)
        thread_pool.submit(self._pass_token)
        return Empty()

    def _pass_token(self):
        """
        Pass the token to the next executor in the token ring.
        It ensures continuous processing of orders in a distributed system.
        """
        logger.info(f"[OrderExecutor] Passing token from executor {self.id} to executor {self.successor}")
        with grpc.insecure_channel(self._executor_address(self.successor, with_port=True)) as channel:
            stub = ox_grpc.OrderExecutorServiceStub(channel)
            stub.SendToken(Empty())

def serve():
    server = grpc.server(thread_pool)
    ox_grpc.add_OrderExecutorServiceServicer_to_server(OrderExecutorService(), server)
    port = "50060"
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"[OrderExecutor] Server listening on port {port}")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()

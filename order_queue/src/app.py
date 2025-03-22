import time
import os
import sys
import logging
import threading
import grpc
from concurrent import futures
from google.protobuf.empty_pb2 import Empty

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure gRPC stub path
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
order_queue_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/order_queue'))
sys.path.insert(0, order_queue_grpc_path)

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

class OrderEntry:
    def __init__(self, order_data: oq_pb2.OrderData):
        self.order_data = order_data
        self.item_count = sum(item.quantity for item in order_data.items)
        self.enqueue_time = time.perf_counter()

    def __lt__(self, other):
        return self.item_count < other.item_count


class OrderQueueService(oq_grpc.OrderQueueServiceServicer):
    """
    Order Queue Service:
    This service enqueues orders using a priority mechanism and dequeues the highest priority order.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.queue = []

    @staticmethod
    def calculate_priority(order_data: oq_pb2.OrderData):
        """
        It is for calculating proirity based on total item quantity."
        """
        return sum(item.quantity for item in order_data.items)

    def EnqueueOrder(self, request: oq_pb2.OrderData, context):
        """
        Add a new order to the queue with priority.
        """
        with self._lock:
            entry = OrderEntry(request)
            self.queue.append(entry)
            self.queue.sort()  # sort the queue based on __lt__
            logger.info(f"[OrderQueue] Enqueued order {request.orderId} with priority {entry.item_count}")
        return Empty()

    def DequeueOrder(self, request: Empty, context):
        """
        Retrieve and remove the highest priority order from the queue.
        """
        with self._lock:
            if not self.queue:
                logger.info("[OrderQueue] Dequeue requested but queue is empty.")
                return oq_pb2.OptionalOrder()
            entry = self.queue.pop(0)
            elapsed = time.perf_counter() - entry.enqueue_time
            logger.info(f"[OrderQueue] Dequeued order {entry.order_data.orderId} after waiting {elapsed:.2f}s")
            return oq_pb2.OptionalOrder(order=entry.order_data)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    oq_grpc.add_OrderQueueServiceServicer_to_server(OrderQueueService(), server)
    port = "50054"
    server.add_insecure_port("[::]:" + port)
    server.start()
    logger.info(f"[OrderQueue] Server up and running on port {port}")
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
import sys
import os
import threading
import queue
import grpc
from concurrent import futures
import logging

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
root_path = os.path.abspath(os.path.join(FILE, '../../..'))

sys.path.insert(0, os.path.join(root_path, 'utils/pb/order_queue'))
import order_queue_pb2 as order_queue
import order_queue_pb2_grpc as order_queue_grpc

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

class OrderQueueService(order_queue_grpc.OrderQueueServiceServicer):
    def __init__(self):
        self.lock = threading.Lock()
        # Using PriorityQueue for bonus points. 
        # Python's PriorityQueue sorts lowest-first. 
        self.queue = queue.PriorityQueue()

    def Enqueue(self, request, context):
        with self.lock:
            # Tuple: (priority, order_id). Lower priority number = executed first.
            self.queue.put((request.priority, request.order_id))
            logger.info(f"Enqueued Order {request.order_id} with priority {request.priority}")
        return order_queue.EnqueueResponse(success=True)

    def Dequeue(self, request, context):
        with self.lock:
            if not self.queue.empty():
                priority, order_id = self.queue.get()
                logger.info(f"Dequeued Order {order_id} (Priority: {priority})")
                return order_queue.DequeueResponse(order_id=order_id, has_order=True)
            else:
                return order_queue.DequeueResponse(order_id="", has_order=False)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    order_queue_grpc.add_OrderQueueServiceServicer_to_server(OrderQueueService(), server)
    server.add_insecure_port("[::]:50054")
    server.start()
    logger.info("Order Queue Service started on port 50054.")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
import sys
import os
import threading

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
utils_path = os.path.abspath(os.path.join(FILE, '../../../utils/'))
sys.path.insert(0, utils_path)

import pb.services.order_details_pb2 as order_details_pb2

import pb.services.order_queue_pb2 as order_queue
import pb.services.order_queue_pb2_grpc as order_queue_grpc

import grpc
from concurrent import futures

from log_utils.logger import setup_logger
logger = setup_logger("OrderQueueService")


class OrderQueueService(order_queue_grpc.OrderQueueService):

    _lock = threading.Lock()
    _order_details = []

    def Enqueue(self, request, context):
        order_id = request.order_id
        with self._lock:
            self._order_details.append(request)
            logger.info(f"Enqueued order with ID: {order_id}")
        return order_details_pb2.StatusMessage(
            success = True,
            order_id = order_id
        )
    
    def Dequeue(self, request, context):
        with self._lock:
            if not self._order_details:
                logger.info("Dequeue called but order queue is empty")
                return order_details_pb2.InputOrderDetails()  # Return empty details if queue is empty
            order_details = self._order_details.pop(0)
            logger.info(f"Dequeued order with ID: {order_details.order_id}")
        return order_details

def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor())
    # Add HelloService
    order_queue_grpc.add_OrderQueueServiceServicer_to_server(OrderQueueService(), server)
    # Listen on port 50054
    port = "50054"
    server.add_insecure_port("[::]:" + port)
    # Start the server
    server.start()
    logger.info("Server started. Listening on port 50054.")
    # Keep thread alive
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
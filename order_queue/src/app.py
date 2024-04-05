import sys
import os
from datetime import datetime
import queue

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
utils_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb'))
sys.path.insert(0, utils_path)

from order_queue import order_queue_pb2 as order_queue
from order_queue import order_queue_pb2_grpc as order_queue_grpc

import grpc
from concurrent import futures

# Transaction flow check by order id.
order_id_from_orchestrator = ""
    
class OrderQueueService(order_queue_grpc.OrderQueueServiceServicer):
    def __init__(self):
        # The Order Queue
        self.order_queue = queue.PriorityQueue()

    def Enqueue(self, request, context):
        self.order_queue.put((request.order.priority, request.order))
        print(f"Enqueued order with id:{request.order.orderId} and priority: {request.order.priority}")
        print(f"Queue size: {self.order_queue.qsize()}")
        print("Elements in Queue Now:")
        print(self.order_queue.queue)  
        print("QUEUE LIST DONE\n")
        return order_queue.EnqueueResponse(success=True)

    def Dequeue(self, request, context):
        if not self.order_queue.empty():
            _, order = self.order_queue.get()
            print(f"Dequeued Succesfully. Queue size: {self.order_queue.qsize()}")
            return order_queue.DequeueResponse(order=order, success=True)
        return order_queue.DequeueResponse(success=False)

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
    print("Server started. Listening on port 50054.")
    # Keep thread alive
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
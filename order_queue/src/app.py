import os
import sys
import threading
from collections import deque
from concurrent import futures

FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")

queue_grpc_path = os.path.abspath(
    os.path.join(FILE, "../../../utils/pb/order_queue")
)
sys.path.insert(0, queue_grpc_path)

import grpc
import order_queue_pb2 as order_queue
import order_queue_pb2_grpc as order_queue_grpc


orders = deque()
queue_lock = threading.Lock()


class OrderQueueService(order_queue_grpc.OrderQueueServiceServicer):
    def Enqueue(self, request, context):
        with queue_lock:
            orders.append(request.order)

        print(
            f"[QUEUE] action=enqueue order={request.order.order_id} "
            f"size={len(orders)}"
        )
        return order_queue.QueueResponse(
            success=True,
            message="Order enqueued."
        )

    def Dequeue(self, request, context):
        with queue_lock:
            if not orders:
                return order_queue.DequeueResponse(
                    success=False,
                    message="Queue is empty."
                )
            order = orders.popleft()

        print(
            f"[QUEUE] action=dequeue order={order.order_id} "
            f"executor={request.executor_id} size={len(orders)}"
        )
        return order_queue.DequeueResponse(
            success=True,
            message="Order dequeued.",
            order=order
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    order_queue_grpc.add_OrderQueueServiceServicer_to_server(
        OrderQueueService(), server
    )
    port = "50054"
    server.add_insecure_port("[::]:" + port)
    server.start()
    print(f"Order queue server started. Listening on port {port}.")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
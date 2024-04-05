import os
import sys

FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")

config_path = os.path.abspath(
    os.path.join(FILE, "../../../utils/config")
)
sys.path.insert(0, config_path)
import log_configurator

relative_modules_path = os.path.abspath(
    os.path.join(FILE, "../../../order_mq/src")
)
sys.path.insert(0, relative_modules_path)
from store import _PRIORITY_MQ

utils_path = os.path.abspath(os.path.join(FILE, "../../../utils/pb/order_mq"))
sys.path.insert(0, utils_path)
# ruff : noqa: E402
from concurrent import futures

import order_mq_pb2 as order_mq
import order_mq_pb2_grpc as order_mq_grpc
import grpc

log_configurator.configure("/app/logs/order_mq.info.log", "/app/logs/order_mq.error.log")

class OrderMqService(order_mq_grpc.OrderMqServiceServicer):
    def HealthCheck(self, request, context):
        return order_mq.HealthCheckResponse(status="Healthy")
    
    def EnqueueOrder(self, request, context):
        _PRIORITY_MQ.put(request)
        return order_mq.EnqueueOrderResponse(status="Order enqueued")
    
    def DequeueOrder(self, request, context):
        order = _PRIORITY_MQ.get()
        return order_mq.DequeueOrderResponse(order_id=order.order_id, order_data=order.order_data)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    order_mq_grpc.add_OrderMqServiceServicer_to_server(
        OrderMqService(), server
    )
    port = "9000"
    server.add_insecure_port("[::]:" + port)
    server.start()
    print(f"Server started. Listening on port {port}.")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()

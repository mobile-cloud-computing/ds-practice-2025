import os
import sys

FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
utils_path = os.path.abspath(os.path.join(FILE, "../pb/order_mq"))
print("\n\n\n")
print(utils_path)
print("\n\n\n")
sys.path.insert(0, utils_path)

# ruff : noqa: E402
# import utils.pb.order_mq.order_mq_pb2 as order_mq
# import utils.pb.order_mq.order_mq_pb2_grpc as order_mq_grpc
import order_mq_pb2 as order_mq
import order_mq_pb2_grpc as order_mq_grpc

import grpc

_ORDER_MQ_SERVICE = "order_mq:9000"


def health_check():
    with grpc.insecure_channel(_ORDER_MQ_SERVICE) as channel:
        stub = order_mq_grpc.OrderMqServiceStub(channel)
        response = stub.HealthCheck(order_mq.HealthCheckRequest())
    return response.status


def enqueue_order(order):
    with grpc.insecure_channel(_ORDER_MQ_SERVICE) as channel:
        stub = order_mq_grpc.OrderMqServiceStub(channel)
        response = stub.EnqueueOrder(order_mq.EnqueueOrderRequest(**order))
    return response


def dequeue_order():
    with grpc.insecure_channel(_ORDER_MQ_SERVICE) as channel:
        stub = order_mq_grpc.OrderMqServiceStub(channel)
        response = stub.DequeueOrder(order_mq.DequeueOrderRequest())
    return response

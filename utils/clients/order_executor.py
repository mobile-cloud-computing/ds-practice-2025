import os
import sys

import grpc

FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
utils_path = os.path.abspath(os.path.join(FILE, "../pb/order_mq"))
sys.path.insert(0, utils_path)

# ruff : noqa: E402
import order_executor_pb2 as order_executor
import order_executor_pb2_grpc as order_executor_grpc

def health_check(executor_addr):
    with grpc.insecure_channel(executor_addr) as channel:
        stub = order_executor_grpc.OrderExecutorServiceStub(channel)
        response = stub.HealthCheck(order_executor.HealthCheckRequest())
    return response.status

def execute_order(executor_addr, order):
    with grpc.insecure_channel(executor_addr) as channel:
        stub = order_executor_grpc.OrderExecutorServiceStub(channel)
        response = stub.ExecuteOrder(order_executor.ExecuteOrderRequest(**order))
    return response

def vote_request(executor_addr, request):
    with grpc.insecure_channel(executor_addr) as channel:
        stub = order_executor_grpc.OrderExecutorServiceStub(channel)
        response = stub.VoteRequest(order_executor.VoteRequest(**request))
    return response
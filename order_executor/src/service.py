import os
import sys

FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")

relative_modules_path = os.path.abspath(
    os.path.join(FILE, "../../../order_executor/src")
)
sys.path.insert(0, relative_modules_path)
from state import handle_vote_request

utils_path = os.path.abspath(os.path.join(FILE, "../../../utils/pb/order_executor"))
sys.path.insert(0, utils_path)

import order_executor_pb2 as order_executor
import order_executor_pb2_grpc as order_executor_grpc
import grpc

class OrderExecutorService(order_executor_grpc.OrderExecutorServiceServicer):

    def HealthCheck(self, request, context):
        return order_executor.HealthCheckResponse(status="Healthy")
    
    def ExecuteOrder(self, request, context):
        return order_executor.ExecuteOrderResponse(status="Order executed successfully")
    
    def Vote(self, request, context):
        response = order_executor.VoteResponse()
        response.vote_granted = handle_vote_request(request)
        response.term = request.term
        return response

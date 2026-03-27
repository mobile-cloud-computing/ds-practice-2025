import sys
import os

def init_grpc_pathes():
    FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
    utils_path = os.path.abspath(os.path.join(FILE, '../../'))
    print(f"utils_path: {utils_path}")
    sys.path.insert(0, utils_path)
    
    FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
    order_path = os.path.abspath(os.path.join(FILE, '../../utils/pb/order_details'))
    print(f"order_path: {order_path}")
    sys.path.insert(0, order_path)


init_grpc_pathes()


# import pb.order_details.order_details_pb2 as order_details
import pb.services.order_details_pb2 as order_details
import grpc


class BaseServiceWrapper:
    def __init__(self, service_id, n_services):
        self.service_id = service_id
        self.n_services = n_services
        self.vector_clock = [0] * n_services

        self.order_details = dict()

    def InitTransaction(self, request, context):
        self.order_details[request.order_id] = request
        return order_details.StatusMessage(
            success = True,
            order_id = request.order_id
        )

    def ClearTransaction(self, request, context):
        if request.order_id in self.order_details:
            del self.order_details[request.order_id]
        return order_details.StatusMessage(
            success = True,
            order_id = request.order_id
        )

    def _update_vector_clock(self, incoming_vector_clock):
        for i in range(self.n_services):
            self.vector_clock[i] = max(self.vector_clock[i], incoming_vector_clock[i])
        self.vector_clock[self.service_id] += 1

    def _send_request_to_service(self, stub_class, connection_string, method_name, message):
        # message.vector_clock.CopyFrom(self.vector_clock)
        for i in range(self.n_services):
            message.vector_clock[i] = self.vector_clock[i]
        with grpc.insecure_channel(connection_string) as channel:
            stub = stub_class(channel)
            method = getattr(stub, method_name)
            response = method(message)
        return response

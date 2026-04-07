import sys
import os
import threading

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
        self.vector_clocks = dict()
        self.order_details = dict()
        self._main_lock = threading.Lock()

    def InitTransaction(self, request, context):
        with self._main_lock:
            self.order_details[request.order_id] = request
            self.vector_clocks[request.order_id] = [0] * self.n_services
        return order_details.StatusMessage(
            success = True,
            order_id = request.order_id
        )

    def ClearTransaction(self, request, context):
        with self._main_lock:
            if request.order_id in self.order_details:
                del self.order_details[request.order_id]
                del self.vector_clocks[request.order_id]
        return order_details.StatusMessage(
            success = True,
            order_id = request.order_id
        )

    def _update_vector_clock(self, order_id, incoming_vector_clock, increment_self=True):
        with self._main_lock:
            for i in range(self.n_services):
                self.vector_clocks[order_id][i] = max(self.vector_clocks[order_id][i], incoming_vector_clock[i])
            if increment_self:
                self.vector_clocks[order_id][self.service_id] += 1

    def _send_request_to_service(self, stub_class, connection_string, method_name, message):
        for i in range(self.n_services):
            message.vector_clock[i] = self.vector_clocks[message.order_id][i]
        with grpc.insecure_channel(connection_string) as channel:
            stub = stub_class(channel)
            method = getattr(stub, method_name)
            response = method(message)
            print(f"Response from {method_name}: {response}")
            self._update_vector_clock(message.order_id, response.status.vector_clock, increment_self=False)
        return response

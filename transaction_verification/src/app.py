import sys
import os
import json
import logging
logging.basicConfig(level=logging.INFO)

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
transaction_verification_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/transaction_verification'))
sys.path.insert(0, transaction_verification_grpc_path)
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
fraud_detection_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/fraud_detection'))
sys.path.insert(0, fraud_detection_grpc_path)
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc

import grpc
from concurrent import futures
from google.protobuf import empty_pb2
import threading

class VectorClockManager:
    def __init__(self, service_index):
        self.service_index = service_index
        self.orders = {} # {order_id: {"clock": [0,0,0], "cond": Condition(), "data": {}}}

    def init_order(self, order_id, data):
        self.orders[order_id] = {
            "clock": [0, 0, 0],
            "cond": threading.Condition(),
            "data": data
        }

    def update_clock(self, order_id, incoming_clock):
        if order_id in self.orders:
            with self.orders[order_id]["cond"]:
                current = self.orders[order_id]["clock"]
                self.orders[order_id]["clock"] = [max(current[i], incoming_clock[i]) for i in range(3)]
                self.orders[order_id]["cond"].notify_all()

    def wait_for_turn(self, order_id, required_index, required_value):
        order = self.orders[order_id]
        with order["cond"]:
            while order["clock"][required_index] < required_value:
                order["cond"].wait()
        return order

vc = VectorClockManager(service_index=1)

class TransactionVerificationService(transaction_verification_grpc.TransactionVerificationServiceServicer):
    def InitOrder(self, request, context):
        order_id = request.order_id
        vc.init_order(order_id, json.loads(request.item_json))
        
        logging.info(f"[{order_id}] Order initialized. Bootstrapping verification...")

        def bootstrap():
            vc.update_clock(order_id, [0, 1, 0])
            self.VerifyTransaction(transaction_verification.VerifyRequest(order_id=order_id), None)

        threading.Thread(target=bootstrap).start()
        return empty_pb2.Empty()

    def UpdateClock(self, request, context):
        vc.update_clock(request.order_id, list(request.clock.values))
        return empty_pb2.Empty()

    def VerifyTransaction(self, request, context):
        order_id = request.order_id
        #logging.info(f"VerifyTransaction called for OrderID: {order_id}")
        logging.info(f"[{order_id}] VerifyTransaction waiting for clock state [0,1,0]...")
        order_state = vc.wait_for_turn(order_id, required_index=1, required_value=1)

        data = order_state["data"]
        user_info = data.get("user", {})
        card_info = data.get("creditCard", {})
        billing = data.get("billingAddress", {})

        logging.info(f"[{order_id}] Processing verification logic...")

        required_fields = [
            user_info.get("name"),
            user_info.get("contact"),
            card_info.get("number"),
            billing.get("street"),
            billing.get("city"),
            data.get("shippingMethod")
        ]
        terms_accepted = data.get("termsAccepted", False)
        

        # Dummy logic: check if all fields have SOMETHING in them
        #TODO: Luhn's algorithm for credit card number
        #TODO: some more interesting checking for fields
        if all(required_fields) and terms_accepted:
            is_valid = True
            logging.info(f"[{order_id}] Verification SUCCESS. Passing to Fraud.")
            with order_state["cond"]:
                current_clock = list(order_state["clock"])
            self.pass_to_fraud(order_id, current_clock, data)

        else:
            is_valid = False
            logging.warning(f"[{order_id}] Verification FAILED. Chain halted.")
        
        logging.info(f"TransactionVerification completed | OrderID: test1 | Is valid?: {is_valid}")
        
        return transaction_verification.VerifyResponse(is_valid=is_valid)
    
    def pass_to_fraud(self, order_id, clock, data):
        try:
            # Connect to Fraud Service (Port 50051)
            with grpc.insecure_channel('fraud_detection:50051') as channel:
                # You must have fraud_detection_pb2_grpc imported
                import fraud_detection_pb2 as fraud
                import fraud_detection_pb2_grpc as fraud_grpc
                
                stub = fraud_grpc.FraudDetectionServiceStub(channel)
                
                # First, update their clock so their 'wait_for_turn' triggers
                stub.UpdateClock(fraud.ClockUpdateRequest(
                    order_id=order_id,
                    clock=fraud.VectorClock(values=clock)
                ))
                
                # Then call their business function
                stub.CheckFraud(fraud.FraudRequest(
                    order_id=order_id,
                    credit_card=data['creditCard']['number'],
                    order_amount=float(data['creditCard'].get('order_amount', 0))
                ))
        except Exception as e:
            logging.error(f"[{order_id}] Failed to trigger Fraud service: {e}")



def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    transaction_verification_grpc.add_TransactionVerificationServiceServicer_to_server(TransactionVerificationService(), server)
    # Listen on port 50052
    port = "50052"
    server.add_insecure_port("[::]:" + port)
    # Start the server
    server.start()
    logging.info(f"TransactionVerification started. Listening on port {port}.")
    # Keep thread alive
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
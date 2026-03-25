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

    def wait_for_turn(self, order_id, target_vector):
            order = self.orders[order_id]
            with order["cond"]:
                # Loop until every index in the current clock is >= the target
                while not all(order["clock"][i] >= target_vector[i] for i in range(len(target_vector))):
                    order["cond"].wait()
            return order

my_index = 0
vc = VectorClockManager(service_index=my_index)

class TransactionVerificationService(transaction_verification_grpc.TransactionVerificationServiceServicer):
    def InitOrder(self, request, context):
        order_id = request.order_id
        vc.init_order(order_id, json.loads(request.item_json))
        
        logging.info(f"[{order_id}] Order initialized.")

        '''
        def bootstrap():
            vc.update_clock(order_id, [1, 0, 0])
            self.VerifyTransaction(transaction_verification.VerifyRequest(order_id=order_id), None)
        
        threading.Thread(target=bootstrap).start()
        '''
        return empty_pb2.Empty()

    def UpdateClock(self, request, context):
        vc.update_clock(request.order_id, list(request.clock.values))
        return empty_pb2.Empty()

    def LuhnAlgorithm(self, request, context):
        order_id = request.order_id
        event_name = "LuhnAlgorithm"
        required_vc = [2,0,0]

        logging.info(f"[{order_id}] {event_name} waiting for vector clock {required_vc}")
        order_state = vc.wait_for_turn(order_id, required_vc)

        logging.info(f"[{order_id}] {event_name} START")

        data = order_state["data"]
        card_info = data.get("creditCard", "")
        digits = [int(d) for d in str(card_info)]

        check_digit = digits[-1]
        payload = digits[:-1]
        reversed_payload = payload[::-1]

        total_sum = 0
        
        for i, digit in enumerate(reversed_payload):
            if (i % 2) == 0:
                doubled_digit = digit * 2
                if doubled_digit > 9:
                    doubled_digit -= 9
                total_sum += doubled_digit
            else:
                total_sum += digit

        check_digit_calculated = (10 - (total_sum % 10)) % 10
        if check_digit == check_digit_calculated:
            logging.info(f"[{order_id}] {event_name} SUCCESS")
            with order_state["cond"]:
                order_state["clock"][my_index] += 1
                order_state["cond"].notify_all()

                

            self.pass_to_fraud(order_id, current_clock, data)
        else:
            logging.warning(f"[{order_id}] {event_name} FAIL")
            current_clock = list(order_state["clock"])
            self.pass_to_orchestrator(order_id, current_clock, data)

        return empty_pb2.Empty() # return ACK
            


    def VerifyTransaction(self, request, context):
        order_id = request.order_id
        #logging.info(f"VerifyTransaction called for OrderID: {order_id}")
        event_name = "VerifyTransaction"
        required_vc = [1,0,0]
        logging.info(f"[{order_id}] {event_name} waiting for vector clock {required_vc}")

        order_state = vc.wait_for_turn(order_id, required_vc)
        logging.info(f"[{order_id}] {event_name} START")

        data = order_state["data"]
        user_info = data.get("user", {})
        card_info = data.get("creditCard", {})
        billing = data.get("billingAddress", {})


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
        #TODO: some more interesting checking for fields
        if all(required_fields) and terms_accepted:
            is_valid = True
            logging.info(f"[{order_id}] VerifyTransaction SUCCESS")
            
            with order_state["cond"]:
                order_state["clock"][my_index] += 1
                order_state["cond"].notify_all()
            # thread here so we can return the ACK immediately, without waiting for the next event to finish
            # I am guessing this is due to the fact this is happening within the same microservice
            threading.Thread(target=self.LuhnAlgorithm, args=(request, context)).start()
            #return self.LuhnAlgorithm(request, context)

        else:
            is_valid = False
            logging.warning(f"[{order_id}] VerifyTransaction FAIL")
            current_clock = list(order_state["clock"])
            self.pass_to_orchestrator(order_id, current_clock, data)
            
            #TODO: this needs to be refactored into just by default fail, but gives the reason

        return empty_pb2.Empty() # return ACK
    
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
    
    def pass_to_orchestrator(self, order_id, clock, data):
        try:
            # Connect to Fraud Service (Port 50051)
            with grpc.insecure_channel('orchestrator:50050') as channel:
                import orchestrator_pb2 as fraud
                import orchestrator_pb2_grpc as fraud_grpc
                
                stub = fraud_grpc.OrchestratorServiceStub(channel)
                
                # First, update their clock so their 'wait_for_turn' triggers
                #stub.UpdateClock(fraud.ClockUpdateRequest(
                    #order_id=order_id,
                    #clock=fraud.VectorClock(values=clock)
               #))
                
                # Then call their business function
                #stub.CheckFraud(fraud.FraudRequest(
                    #order_id=order_id,
                    #credit_card=data['creditCard']['number'],
                    #order_amount=float(data['creditCard'].get('order_amount', 0))
                #))
        except Exception as e:
            logging.error(f"[{order_id}] Failed to send to Orchestrator service: {e}")



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
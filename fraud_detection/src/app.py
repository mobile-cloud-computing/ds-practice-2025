import sys
import os
import json
import logging
logging.basicConfig(level=logging.INFO)

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
fraud_detection_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/fraud_detection'))
sys.path.insert(0, fraud_detection_grpc_path)
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
orchestrator_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/orchestrator'))
sys.path.insert(0, orchestrator_grpc_path)
import orchestrator_pb2 as pb2
import orchestrator_pb2_grpc as pb2_grpc

import grpc
from google.protobuf import empty_pb2
from concurrent import futures
import threading

'''
class HelloService(fraud_detection_grpc.HelloServiceServicer):
    # Create an RPC function to say hello
    def SayHello(self, request, context):
        # Create a HelloResponse object
        response = fraud_detection.HelloResponse()
        # Set the greeting field of the response object
        response.greeting = "Hello, " + request.name
        # Print the greeting message
        print(response.greeting)
        # Return the response object
        return response
'''

import threading

class VectorClockManager:
    def __init__(self, my_index):
        self.my_index = my_index # 0=Fraud, 1=Verif, 2=Sugg
        self.orders = {} # {id: {"clock": [0,0,0], "data": {}, "cond": Condition()}}

    def init(self, order_id, data):
        self.orders[order_id] = {
            "clock": [0, 0, 0],
            "data": data,
            "cond": threading.Condition()
        }

    def update(self, order_id, new_clock):
        with self.orders[order_id]["cond"]:
            # Merge: Take max of each position
            current = self.orders[order_id]["clock"]
            self.orders[order_id]["clock"] = [max(current[i], new_clock[i]) for i in range(3)]
            self.orders[order_id]["cond"].notify_all()

    def wait_for_dependency(self, order_id, dep_index, dep_value):
        order = self.orders[order_id]
        with order["cond"]:
            while order["clock"][dep_index] < dep_value:
                order["cond"].wait()
        return order

vc = VectorClockManager(my_index=1)

class FraudDetectionService(fraud_detection_grpc.FraudDetectionServiceServicer):
    def InitOrder(self, request, context):
        vc.init(request.order_id, json.loads(request.item_json))
        #threading.Thread(target=self.process_order, args=(request.order_id,)).start()
        return empty_pb2.Empty()

    def UpdateClock(self, request, context):
        # Update the local clock and wake up the waiting thread
        vc.update(request.order_id, list(request.clock.values))
        return empty_pb2.Empty()

    def CheckFraud(self, request, context):
        order_id = request.order_id
        
        # WAIT for Verification (Index 1) to be 1
        logging.info(f"[{order_id}] CheckFraud waiting for Verification...")
        order = vc.wait_for_dependency(order_id, dep_index=1, dep_value=1)

        card_number = request.credit_card
        order_amount = request.order_amount
        
        logging.info(f"Checking fraud for card: {card_number} and amount: {order_amount}")

        # Dummy logic: Flag if amount > 1000 or card starts with 999
        is_fraud = False
        if order_amount > 1000 or card_number.startswith("999"):
            is_fraud = True

        logging.info(f"[{order_id}] FraudDetection completed | Is fraud?: {is_fraud}")

        with order["cond"]:
            order["clock"][0] = 1 
            current_clock = list(order["clock"])
        
        if not is_fraud:
            self.pass_to_next(order_id, current_clock)
        else:
            self.notify_orchestrator_denied(order_id)
            
        return fraud_detection.FraudResponse(is_fraud=is_fraud)

    def pass_to_next(self, order_id, clock):
            try:
                with grpc.insecure_channel('suggestions:50053') as channel:
                    suggestions_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/suggestions'))
                    sys.path.insert(0, suggestions_grpc_path)
                    import suggestions_pb2 as suggestions
                    import suggestions_pb2_grpc as suggestions_grpc
                    stub = suggestions_grpc.SuggestionsServiceStub(channel)
                    
                    vc_proto = suggestions.VectorClock(values=clock)
                    stub.UpdateClock(suggestions.ClockUpdateRequest(
                        order_id=order_id, 
                        clock=vc_proto
                    ))

                    stub.SuggestBooks(suggestions.SuggestRequest(order_id=order_id))
                    logging.info(f"[{order_id}] Baton passed to Suggestions.")

            except Exception as e:
                logging.error(f"[{order_id}] Failed to pass to Suggestions: {e}")

    def notify_orchestrator_denied(self, order_id):
        try:
            with grpc.insecure_channel('orchestrator:50050') as channel:
                # You'll need to import orchestrator stubs here
                stub = orchestrator_pb2_grpc.OrderFinalizerStub(channel)
                stub.ReportResult(orchestrator_pb2.FinalOrderResult(
                    order_id=order_id,
                    status="Order Denied",
                    suggested_books=[]
                ))
        except Exception as e:
            logging.error(f"[{order_id}] Failed to notify orchestrator of denial: {e}")

def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    # Add HelloService
    #fraud_detection_grpc.add_HelloServiceServicer_to_server(HelloService(), server)
    fraud_detection_grpc.add_FraudDetectionServiceServicer_to_server(FraudDetectionService(), server)
    # Listen on port 50051
    port = "50051"
    server.add_insecure_port("[::]:" + port)
    # Start the server
    server.start()
    logging.info (f"FraudDetection started. Listening on port {port}.")
    # Keep thread alive
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
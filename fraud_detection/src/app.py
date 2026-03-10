import sys
import os
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

import grpc
from concurrent import futures
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
class FraudDetectionService(fraud_detection_grpc.FraudDetectionServiceServicer):

    def CheckFraud(self, request, context):
        card_number = request.card_number
        order_amount = request.order_amount
        
        logging.info(f"Checking fraud for card: {card_number} and amount: {order_amount}")

        # Dummy logic: Flag if amount > 1000 or card starts with 999
        is_fraud = False
        if order_amount > 1000 or card_number.startswith("999"):
            is_fraud = True

        logging.info(f"FraudDetection completed | OrderID: test1 | Is fraud?: {is_fraud}")
        
        return fraud_detection.FraudResponse(is_fraud=is_fraud)



def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
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
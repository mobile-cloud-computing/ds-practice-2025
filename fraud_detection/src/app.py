import sys
import os

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
fraud_detection_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/fraud_detection'))
sys.path.insert(0, fraud_detection_grpc_path)
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc

import logging
import grpc
from concurrent import futures

logging.basicConfig(level=logging.INFO)

# Create a class to define the server functions, derived from
# fraud_detection_pb2_grpc.HelloServiceServicer
# class HelloService(fraud_detection_grpc.HelloServiceServicer):
#     # Create an RPC function to say hello
#     def SayHello(self, request, context):
#         # Create a HelloResponse object
#         response = fraud_detection.HelloResponse()
#         # Set the greeting field of the response object
#         response.greeting = "Hello, " + request.name
#         # Print the greeting message
#         print(response.greeting)
#         # Return the response object
#         return response

class FraudDetectionService(fraud_detection_grpc.FraudDetectionServiceServicer):

    def CheckFraud(self, request, context):
        """Check for fraud based on two rules: order amount exceeding 1000 and card number prefix '999'."""
        card_number = request.card_number
        order_amount = request.order_amount

        logging.info(f"Checking fraud for card ending in {card_number[-4:]} with amount {order_amount}")

        is_fraud = False
        if float(order_amount) > 1000 or card_number.startswith("999"):
            is_fraud = True

        logging.info(f"Fraud check result: is_fraud={is_fraud}")
        return fraud_detection.FraudResponse(is_fraud=is_fraud)


def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor())
    # Add HelloService
    fraud_detection_grpc.add_FraudDetectionServiceServicer_to_server(FraudDetectionService(), server)
    # Listen on port 50051
    port = "50051"
    server.add_insecure_port("[::]:" + port)
    # Start the server
    server.start()
    logging.info("Fraud Detection service started on port 50051")
    # Keep thread alive
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
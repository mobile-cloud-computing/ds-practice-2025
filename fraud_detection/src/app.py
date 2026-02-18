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

import grpc
from concurrent import futures
    
class FraudDetectionService(fraud_detection_grpc.FraudDetectionServiceServicer):
    # Create an RPC function to detect fraud
    def DetectFraud(self, request, context):
        card_number = request.card_number
        order_amount = request.order_amount

        # Create a FraudDetectionResponse object
        response = fraud_detection.FraudDetectionResponse()
        # Set the is_fraud field of the response object
        response.is_fraud = order_amount > 1000 or card_number.startswith("999")  # Example logic: flag as fraud if amount > 1000 and card starts with '4'
        # Print the transaction details and the fraud detection result
        print(f"Received transaction: [no id], amount: {order_amount}, is_fraud: {response.is_fraud}")
        # Return the response object
        return response

def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor())
    # Add FraudDetectionService
    fraud_detection_grpc.add_FraudDetectionServiceServicer_to_server(FraudDetectionService(), server)
    # Listen on port 50051
    port = "50051"
    server.add_insecure_port("[::]:" + port)
    # Start the server
    server.start()
    print("Server started. Listening on port 50051.")
    # Keep thread alive
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
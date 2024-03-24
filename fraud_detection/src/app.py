import sys
import os
from datetime import datetime

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
utils_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/fraud_detection'))
sys.path.insert(0, utils_path)
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc

import grpc
from concurrent import futures

# Get the server index for the vector clock.
SERVER_INDEX = int(os.getenv("SERVER_INDEX_FOR_VECTOR_CLOCK"))

# Create a class to define the server functions, derived from
# fraud_detection_pb2_grpc.HelloServiceServicer
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
    
class UserdataFraudDetectionService(fraud_detection_grpc.UserdataFraudDetectionServiceServicer):
    # Increment the value in the server index.
    # If the index isn't in the vc_array, append 0 until the index.
    def increment_vector_clock(self, vc_array):
        if SERVER_INDEX <= len(vc_array) - 1:
            vc_array[SERVER_INDEX] += 1
        else:
            while len(vc_array) != SERVER_INDEX:
                vc_array.append(0)
            vc_array.append(1)

    def DetectUserdataFraud(self, request, context):
        print("Fraud dectection request received")
        print(f"[Fraud detection] Server index: {SERVER_INDEX}")

        vector_clock = request.vectorClock
        vc_array = vector_clock.vcArray
        timestamp = vector_clock.timestamp

        print(f"[Fraud detection] VCArray from orchestrator: {vc_array}")
        print(f"[Fraud detection] Timestamp from orchestrator: {timestamp}")

        self.increment_vector_clock(vc_array)
        print(f"[Fraud detection] VCArray in Fraud detection: {vc_array}")
        print(f"[Fraud detection] Timestamp in Fraud detection: {datetime.now().timestamp()}")
        
        # a simple dummy check of is user name and contact exist
        user_name = request.user.name
        contact_number = request.user.contact

        user_data_filled = bool(user_name and contact_number)
        # a simple dummy check if contact is between 7 and 15 inclusive, and if they are all digits
        contact_is_number = (len(contact_number) >= 7 and len(contact_number) <= 15 )and contact_number.isdigit()
         
        is_fraudulent = not user_data_filled or not contact_is_number

        print(f"Fraud check response: {'Fraudulent' if is_fraudulent else 'Not Fraudulent'}")
        return fraud_detection.UserdataFraudDetectionResponse(is_fraudulent=is_fraudulent)
    

class CardinfoFraudDetectionService(fraud_detection_grpc.CardinfoFraudDetectionServiceServicer):
    # Increment the value in the server index.
    # If the index isn't in the vc_array, append 0 until the index.
    def increment_vector_clock(self, vc_array):
        if SERVER_INDEX <= len(vc_array) - 1:
            vc_array[SERVER_INDEX] += 1
        else:
            while len(vc_array) != SERVER_INDEX:
                vc_array.append(0)
            vc_array.append(1)
    
    def DetectCardinfoFraud(self, request, context):
        print("Fraud dectection request received")
        print(f"[Fraud detection] Server index: {SERVER_INDEX}")

        vector_clock = request.vectorClock
        vc_array = vector_clock.vcArray
        timestamp = vector_clock.timestamp

        print(f"[Fraud detection] VCArray from orchestrator: {vc_array}")
        print(f"[Fraud detection] Timestamp from orchestrator: {timestamp}")

        self.increment_vector_clock(vc_array)
        print(f"[Fraud detection] VCArray in Fraud detection: {vc_array}")
        print(f"[Fraud detection] Timestamp in Fraud detection: {datetime.now().timestamp()}")
        
        card_number = request.creditCard.number

        is_fraudulent = not card_number.isdigit()

        print(f"Fraud check response: {'Fraudulent' if is_fraudulent else 'Not Fraudulent'}")
        return fraud_detection.CardinfoFraudDetectionResponse(is_fraudulent=is_fraudulent)

def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor())
    # Add HelloService
    fraud_detection_grpc.add_HelloServiceServicer_to_server(HelloService(), server)
    fraud_detection_grpc.add_UserdataFraudDetectionServiceServicer_to_server(UserdataFraudDetectionService(), server)
    fraud_detection_grpc.add_CardinfoFraudDetectionServiceServicer_to_server(CardinfoFraudDetectionService(), server)
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
import sys
import os
from datetime import datetime
from google.protobuf.json_format import MessageToDict

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
utils_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb'))
sys.path.insert(0, utils_path)
from fraud_detection import fraud_detection_pb2 as fraud_detection
from fraud_detection import fraud_detection_pb2_grpc as fraud_detection_grpc
from transaction_verification import transaction_verification_pb2 as transaction_verification
from transaction_verification import transaction_verification_pb2_grpc as transaction_verification_grpc
from book_suggestion import book_suggestion_pb2 as book_suggestion
from book_suggestion import book_suggestion_pb2_grpc as book_suggestion_grpc

import grpc
from concurrent import futures

# Set the server index for the vector clock.
# Frontend: 0, Orchestrator: 1, TransactionVerification: 2, FraudDetection: 3, BookSuggestion: 4
SERVER_INDEX = 3
NUM_SERVERS = 5
LOCAL_VC_CORRECT_AFTER_USERDATA_VERIFICATION = [0, 0, 0, 0, 0]
VC_CORRECT_AFTER_USERDATA_VERIFICATION = [0, 1, 2, 0, 0]
LOCAL_VC_CORRECT_AFTER_CREDITCARD_VERIFICATION = [0, 0, 0, 1, 0]
VC_CORRECT_AFTER_CREDITCARD_VERIFICATION = [0, 1, 3, 1, 0]

# Create the global local vector clock.
local_vector_clock = {}

def cardinfo_verification_service(data, vector_clock):
    with grpc.insecure_channel('transaction_verification:50052') as channel:
        stub = transaction_verification_grpc.CardinfoVerificationServiceStub(channel)
        attr = MessageToDict(data)
        attr["vectorClock"] = vector_clock
        response = stub.VerifyCardinfo(transaction_verification.CardinfoVerificationRequest(**attr))
        return response
    
def book_suggestion_service(data, vector_clock):
    with grpc.insecure_channel('book_suggestion:50053') as channel:
        stub = book_suggestion_grpc.BookSuggestionServiceStub(channel)
        attr = MessageToDict(data)
        attr["vectorClock"] = vector_clock
        response = stub.SuggestBook(book_suggestion.BookSuggestionRequest(**attr))
        return response
    
# Increment the value in the server index, and update the timestamp.
# If the index isn't in the vc_array, append 0 until the index.
def increment_vector_clock(vector_clock):
    vc_array = [0 for _ in range(NUM_SERVERS)] if not "vcArray" in vector_clock else vector_clock["vcArray"]
    timestamp = datetime.now().timestamp()

    vc_array[SERVER_INDEX] += 1

    return {"vcArray": vc_array, "timestamp": timestamp}


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

    def __init__(self):
        global local_vector_clock
        local_vector_clock = {"vcArray": [0 for _ in range(NUM_SERVERS)], "timestamp": datetime.now().timestamp()}

    def check_vc_after_userdata_verification(self, vector_clock, local_vector_clock):
        request_vc_check = bool(vector_clock['vcArray'] == VC_CORRECT_AFTER_USERDATA_VERIFICATION)
        local_vc_check = bool(local_vector_clock['vcArray'] == LOCAL_VC_CORRECT_AFTER_USERDATA_VERIFICATION)
        timestamp_check = bool(vector_clock['timestamp'] < datetime.now().timestamp())
        return request_vc_check and local_vc_check and timestamp_check
    
    def is_userdata_fraudulent(self, user_name, contact_number):
        # a simple dummy check if contact is between 7 and 15 inclusive, and if they are all digits
        contact_is_number = (len(contact_number) >= 7 and len(contact_number) <= 15 )and contact_number.isdigit()

        is_fraudulent = not contact_is_number
        return is_fraudulent

    def DetectUserdataFraud(self, request, context):
        global local_vector_clock
        print("Fraud dectection request received")
        print(f"[Fraud detection] Server index: {SERVER_INDEX}")

        is_fraudulent = True

        vector_clock = MessageToDict(request.vectorClock)
        user_name = request.user.name
        contact_number = request.user.contact

        if self.check_vc_after_userdata_verification(vector_clock, local_vector_clock):
            print('[Fraud detection] VC is correct after userdata verification.')

            # d: is userdata flaudulent?
            is_fraudulent = self.is_userdata_fraudulent(user_name, contact_number)
            if not is_fraudulent:
                local_vector_clock = increment_vector_clock(local_vector_clock)
                vector_clock = increment_vector_clock(vector_clock)
                print(f"[Fraud detection] VCArray updated (no fraud in userdata) in Fraud detection: {vector_clock['vcArray']}")
                # print(f"[Fraud detection] Timestamp updated in Fraud detection: {vector_clock['timestamp']}")

        print(f"Fraud check response: {'Fraudulent' if is_fraudulent else 'Not Fraudulent'}")
        if not is_fraudulent:
            with futures.ThreadPoolExecutor() as executor:
                cardinfo_future = executor.submit(cardinfo_verification_service, request, vector_clock)
            message = cardinfo_future.result()
            response = MessageToDict(message)
        else:
            response = {
                "isValid": False,
                "errorMessage": "Order Rejected because fraud was detected. Please provvide a valid user name or contact.",
                "books": None
            }
        return fraud_detection.UserdataFraudDetectionResponse(**response)
    

class CardinfoFraudDetectionService(fraud_detection_grpc.CardinfoFraudDetectionServiceServicer):

    def check_vc_after_creditcard_verification(self, vector_clock, local_vector_clock):
        request_vc_check = bool(vector_clock['vcArray'] == VC_CORRECT_AFTER_CREDITCARD_VERIFICATION)
        local_vc_check = bool(local_vector_clock['vcArray'] == LOCAL_VC_CORRECT_AFTER_CREDITCARD_VERIFICATION)
        timestamp_check = bool(vector_clock['timestamp'] < datetime.now().timestamp())
        return request_vc_check and local_vc_check and timestamp_check
    
    def is_creditcard_fraudulent(self, credit_card):
        is_fraudulent = not credit_card.number.isdigit()

        return is_fraudulent
    
    def DetectCardinfoFraud(self, request, context):
        global local_vector_clock
        print("Fraud dectection request received")
        print(f"[Fraud detection] Server index: {SERVER_INDEX}")

        is_fraudulent = True

        local_vector_clock = globals()['local_vector_clock']
        vector_clock = MessageToDict(request.vectorClock)
        credit_card = request.creditCard

        if self.check_vc_after_creditcard_verification(vector_clock, local_vector_clock):
            
            # e: is creditcard flaudulent?
            is_fraudulent = self.is_creditcard_fraudulent(credit_card)
            if not is_fraudulent:
                local_vector_clock = increment_vector_clock(local_vector_clock)
                vector_clock = increment_vector_clock(vector_clock)
                print(f"[Fraud detection] VCArray updated (no fraud in creditcard) in Fraud detection: {vector_clock['vcArray']}")
                # print(f"[Fraud detection] Timestamp updated (no fraud in creditcard) in Fraud detection: {vector_clock['timestamp']}")

        print(f"Fraud check response: {'Fraudulent' if is_fraudulent else 'Not Fraudulent'}")
        if not is_fraudulent:
            with futures.ThreadPoolExecutor() as executor:
                suggestion_future = executor.submit(book_suggestion_service, request, vector_clock)
            message = suggestion_future.result()
            response = MessageToDict(message)
        else:
            response = {
                "isValid": False,
                "errorMessage": "Order Rejected because fraud was detected. Please provvide a valid payment details..",
                "books": None
            }
        return fraud_detection.CardinfoFraudDetectionResponse(**response)

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
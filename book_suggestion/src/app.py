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
from book_suggestion import book_suggestion_pb2 as book_suggestion
from book_suggestion import book_suggestion_pb2_grpc as book_suggestion_grpc

from concurrent import futures
import grpc
import json
import random

# Set the server index for the vector clock.
# Frontend: 0, Orchestrator: 1, TransactionVerification: 2, FraudDetection: 3, BookSuggestion: 4
SERVER_INDEX = 4
NUM_SERVERS = 5
LOCAL_VC_CORRECT_AFTER_CREDITCARD_FRAUD_DETECTION = [0, 0, 0, 0, 0]
VC_CORRECT_AFTER_CREDITCARD_FRAUD_DETECTION = [0, 1, 3, 2, 0]

# Create the global local vector clock.
local_vector_clock = {}

# Transaction flow check by order id.
order_id_from_orchestrator = ""

with open(os.path.abspath(os.path.join(FILE, '../book_list.json'))) as f:
    book_list_json = json.load(f)
    book_list = [book_list_json[key] for key in book_list_json]

# Increment the value in the server index, and update the timestamp.
# If the index isn't in the vc_array, append 0 until the index.
def increment_vector_clock(vector_clock):
    vc_array = [0 for _ in range(NUM_SERVERS)] if not "vcArray" in vector_clock else vector_clock["vcArray"]
    timestamp = datetime.now().timestamp()

    vc_array[SERVER_INDEX] += 1

    return {"vcArray": vc_array, "timestamp": timestamp}

class OrderIdStorageService(book_suggestion_grpc.OrderIdStorageServiceServicer):
    
    def StorageOrderId(self, request, context):
        global order_id_from_orchestrator
        order_id_from_orchestrator = request.orderId
        return book_suggestion.OrderIdStorageResponse(isValid=True)

class BookSuggestionService(book_suggestion_grpc.BookSuggestionServiceServicer):

    def check_order_id(self, order_id):
        is_valid = (order_id_from_orchestrator == order_id)
        return is_valid

    def check_vc_after_userdata_verification(self, vector_clock, local_vector_clock):
        request_vc_check = bool(vector_clock['vcArray'] == VC_CORRECT_AFTER_CREDITCARD_FRAUD_DETECTION)
        local_vc_check = bool(local_vector_clock['vcArray'] == LOCAL_VC_CORRECT_AFTER_CREDITCARD_FRAUD_DETECTION)
        timestamp_check = bool(vector_clock['timestamp'] < datetime.now().timestamp())
        return request_vc_check and local_vc_check and timestamp_check

    def SuggestBook(self, request, context):
        global local_vector_cloc
        local_vector_clock = {"vcArray": [0 for _ in range(NUM_SERVERS)], "timestamp": datetime.now().timestamp()}
        print("Boook Suggestion request received")
        print(f"[Book suggestion] Server index: {SERVER_INDEX}")

        error_response = lambda error_message: {
            "isValid": False,
            "errorMessage": error_message,
            "books": None
        }

        vector_clock = MessageToDict(request.vectorClock)
        order_id = request.orderId

        ### Order Id Confirm ------------------------------------
        if not self.check_order_id(order_id):
            error_message = "Server Error. Please retry later."
            return book_suggestion.BookSuggestionResponse(**error_response(error_message))
        
        print('[Book suggestion] Order Id is confirmed.')


        ### Vector Clock Confirm ------------------------------------
        if not self.check_vc_after_userdata_verification(vector_clock, local_vector_clock):
            error_message = "Server Error. Please retry later."
            return book_suggestion.BookSuggestionResponse(**error_response(error_message))
        
        print('[Book suggestion] VC is correct after credit card fraud detection.')

        local_vector_clock = increment_vector_clock(local_vector_clock)
        vector_clock = increment_vector_clock(vector_clock)
        print(f"[Book suggestion] VCArray updated (suggest book) in Book suggestion: {vector_clock['vcArray']}")
        # print(f"[Book suggestion] Timestamp updated (suggest book) in Book suggestion: {vector_clock['timestamp']}")

        print(f"Ordered Book: {request.item}")
        suggest_books = random.sample(book_list, 2)
        response = {
            "isValid": True,
            "errorMessage": None,
            "books": suggest_books
        }   
        return book_suggestion.BookSuggestionResponse(**response)

    
def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    book_suggestion_grpc.add_OrderIdStorageServiceServicer_to_server(OrderIdStorageService(), server)
    book_suggestion_grpc.add_BookSuggestionServiceServicer_to_server(BookSuggestionService(), server)
    server.add_insecure_port('[::]:50053')
    server.start()
    print("Book Suggestion Service started on port 50053")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
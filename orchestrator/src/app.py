import sys
import os
import uuid
from datetime import datetime

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
utils_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb'))
# utils_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/transaction_verification'))
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
SERVER_INDEX = 1
NUM_SERVERS = 5

def greet(name='you'):
    # Establish a connection with the fraud-detection gRPC service.
    with grpc.insecure_channel('fraud_detection:50051') as channel:
        # Create a stub object.
        stub = fraud_detection_grpc.HelloServiceStub(channel)
        # Call the service through the stub object.
        response = stub.SayHello(fraud_detection.HelloRequest(name=name))
    return response.greeting

# Import Flask.
# Flask is a web framework for Python.
# It allows you to build a web application quickly.
# For more information, see https://flask.palletsprojects.com/en/latest/
from flask import Flask, request
from flask_cors import CORS

# Create a simple Flask app.
app = Flask(__name__)
# Enable CORS for the app.
CORS(app)

# Define a GET endpoint.
@app.route('/', methods=['GET'])
def index():
    """
    Responds with 'Hello, [name]' when a GET request is made to '/' endpoint.
    """
    # Test the fraud-detection gRPC service.
    response = greet(name='orchestrator')
    # Return the response.
    return response

def orderid_storage_fraud_service(order_id):
    with grpc.insecure_channel('fraud_detection:50051') as channel:
        stub = fraud_detection_grpc.OrderIdStorageServiceStub(channel)
        response = stub.StorageOrderId(fraud_detection.OrderIdStorageRequest(
            orderId=order_id
        ))
        return response.isValid
    
def orderid_storage_transaction_service(order_id):
    with grpc.insecure_channel('transaction_verification:50052') as channel:
        stub = transaction_verification_grpc.OrderIdStorageServiceStub(channel)
        response = stub.StorageOrderId(transaction_verification.OrderIdStorageRequest(
            orderId=order_id
        ))
        return response.isValid
    
def orderid_storage_suggestion_service(order_id):
    with grpc.insecure_channel('book_suggestion:50053') as channel:
        stub = book_suggestion_grpc.OrderIdStorageServiceStub(channel)
        response = stub.StorageOrderId(book_suggestion.OrderIdStorageRequest(
            orderId=order_id
        ))
        return response.isValid

def item_and_userdata_verification_service(data, order_id, vector_clock):
    with grpc.insecure_channel('transaction_verification:50052') as channel:
        stub = transaction_verification_grpc.ItemAndUserdataVerificationServiceStub(channel)
        response = stub.VerifyItemAndUserdata(transaction_verification.ItemAndUserdataVerificationRequest(
            orderId=order_id,
            user=data['user'],
            item=data['items'][0],
            creditCard=data['creditCard'],
            vectorClock=vector_clock
        ))
        return response

def transform_suggested_book_response(suggested_books):
    book_array = []
    for book in suggested_books:
        book_dict = {}
        book_dict["bookId"] = book.id
        book_dict["title"] = book.title
        book_dict["author"] = book.author
        book_array.append(book_dict)

    return book_array # key: [bookId, title, author]

# Increment the value in the server index, and update the timestamp.
# If the index isn't in the vc_array, append 0 until the index.
def increment_vector_clock(vector_clock):
    vc_array = [0 for _ in range(NUM_SERVERS)] if not "vcArray" in vector_clock else vector_clock["vcArray"]
    timestamp = datetime.now().timestamp()

    vc_array[SERVER_INDEX] += 1

    return {"vcArray": vc_array, "timestamp": timestamp}

@app.route('/checkout', methods=['POST'])
def checkout():
    """
    Responds with a JSON object containing the order ID, status, and suggested books.
    """
    print(f"[Orchestrator] Server index: {SERVER_INDEX}")
    # Print request object data
    print("Request Data:", request.json)
    data = request.json

    vector_clock = {}
    vector_clock = increment_vector_clock(vector_clock)
    print(f"[Orchestrator] Vector Clock Array: {vector_clock['vcArray']}")
    print(f"[Orchestrator] Timestamp: {vector_clock['timestamp']}")

    order_id = str(uuid.uuid4())
    print(f'[Orchestrator] Order id: {order_id}')

    # Send the order id before requesting.
    with futures.ThreadPoolExecutor() as executor:
        orderid_storage_fraud_future = executor.submit(orderid_storage_fraud_service, order_id)
        orderid_storage_transaction_future = executor.submit(orderid_storage_transaction_service, order_id)
        orderid_storage_suggestion_future = executor.submit(orderid_storage_suggestion_service, order_id)

        futures.wait([orderid_storage_fraud_future, orderid_storage_transaction_future, orderid_storage_suggestion_future], return_when=futures.ALL_COMPLETED)

    if not (orderid_storage_fraud_future.result() and orderid_storage_transaction_future.result() and orderid_storage_suggestion_future.result()):
        order_status_response = {'orderId': '404', "status": "Server Error. Please try later."}
        return order_status_response


    # Triger the flow of events and recieve the end result.
    with futures.ThreadPoolExecutor() as executor:
        item_and_userdata_future = executor.submit(item_and_userdata_verification_service, data, order_id, vector_clock)
        
    checkout_result = item_and_userdata_future.result()
    
    if checkout_result.isValid:
        suggested_books = checkout_result.books
        order_status_response = {
            'orderId': order_id,
            'status': 'Order Approved',
            'suggestedBooks': transform_suggested_book_response(suggested_books)
        }
        return order_status_response
    else:
        print(checkout_result.errorMessage)
        order_status_response = {'orderId': '404', "status": checkout_result.errorMessage}
        return order_status_response

    


if __name__ == '__main__':
    # Run the app in debug mode to enable hot reloading.
    # This is useful for development.
    # The default port is 5000.
    app.run(host='0.0.0.0')

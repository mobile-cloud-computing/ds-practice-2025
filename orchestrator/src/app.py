import sys
import os

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
fraud_detection_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/fraud_detection'))
transaction_verification_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/transaction_verification'))
suggestions_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/suggestions'))
sys.path.insert(0, fraud_detection_grpc_path)
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc
sys.path.insert(0, transaction_verification_grpc_path)
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc

sys.path.insert(0, suggestions_grpc_path)
import suggestions_pb2 as suggestions
import suggestions_pb2_grpc as suggestions_grpc

import grpc


import logging

logging.basicConfig(
    filename="./orchestrator_logs.txt",
    filemode="a",
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    stream=sys.stdout, # also print to console
)

logger = logging.getLogger(__name__)

def detect_fraud(card_nr, order_ammount):
    # Establish a connection with the fraud-detection gRPC service.
    with grpc.insecure_channel('fraud_detection:50051') as channel:
        # Create a stub object.
        stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
        # Call the service through the stub object.
        response = stub.checkFraud(fraud_detection.FraudRequest(card_nr=card_nr, order_ammount=order_ammount))
        if response.is_fraud:
            logger.warning(f"Fraud detected with context: {request}")
    return response.is_fraud

def verify_transaction(card_nr, order_id, money):
    with grpc.insecure_channel('transaction_verification:50052') as channel:
        # Create a stub object.
        stub = transaction_verification_grpc.transactionServiceStub(channel)
        # Call the service through the stub object.
        if isinstance(order_id, bytes):
            order_id = int.from_bytes(order_id)
        response = stub.verifyTransaction(transaction_verification.PayRequest(card_nr=str(card_nr), order_id=order_id, money=money))
        logger.info(f"Transaction with {card_nr} {order_id} {money} result {response.verified}")
        if response.order_id != order_id: return False
    return response.verified

def get_suggested_books(ordered_books):
    with grpc.insecure_channel("suggestions:50053") as channel:
        stub = suggestions_grpc.SuggestionsServiceStub(channel)

        response = stub.suggest(suggestions.SuggestRequest(ordered_books=ordered_books))
    return response.suggested_books

# Import Flask.
# Flask is a web framework for Python.
# It allows you to build a web application quickly.
# For more information, see https://flask.palletsprojects.com/en/latest/
from flask import Flask, request
from flask_cors import CORS
import json

# Create a simple Flask app.
app = Flask(__name__)
# Enable CORS for the app.
CORS(app, resources={r'/*': {'origins': '*'}})

# Define a GET endpoint.
@app.route('/', methods=['GET'])
def index():
    """
    Responds with 'Hello, [name]' when a GET request is made to '/' endpoint.
    """
    # Return the response.
    return "hello orchestrator"

@app.route('/checkout', methods=['POST'])
def checkout():
    """
    Responds with a JSON object containing the order ID, status, and suggested books.
    """
    # Get request object data to json
    request_data = json.loads(request.data)
    # Print request object data

    quantity = sum([item["quantity"] for item in request_data["items"]])

    is_fraud = detect_fraud(request_data["creditCard"]["number"], quantity)
    suggested_books = get_suggested_books([i["name"] for i in request_data["items"]])
    logger.info(f"Got suggested books.")

    # Convert the gRPC response to a dictionary
    suggested_books_dicts = []
    for book in suggested_books:
        suggested_books_dicts.append({
            'bookId': book.bookId,
            'title': book.title,
            'author': book.author
        })

    if not verify_transaction(request_data["creditCard"]["number"], os.urandom(4), quantity):
        is_fraud = True



    # Dummy response following the provided YAML specification for the bookstore
    order_status_response = {
        'orderId': '12345',
        'status': ('odred declined' if is_fraud else 'Order Approved'),
        'suggestedBooks': suggested_books_dicts,
    }

    return order_status_response


if __name__ == '__main__':
    # Run the app in debug mode to enable hot reloading.
    # This is useful for development.
    # The default port is 5000.
    app.run(host='0.0.0.0')

import sys
import os
import random

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

# Configure logging to file and console
logging.basicConfig(
    filename="/logs/orchestrator_logs.txt",
    filemode="a",
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


fraud_channel = grpc.insecure_channel('fraud_detection:50051')
verification_channel = grpc.insecure_channel('transaction_verification:50052')
suggestion_channel = grpc.insecure_channel("suggestions:50053")

fraud_stub = fraud_detection_grpc.FraudDetectionServiceStub(fraud_channel)
verification_stub = transaction_verification_grpc.transactionServiceStub(verification_channel)
suggestion_stub = suggestions_grpc.SuggestionsServiceStub(suggestion_channel)


def detect_fraud(card_nr, order_ammount):
    # Call the service through the stub object.
    response = fraud_stub.checkFraud(fraud_detection.FraudRequest(card_nr=card_nr, order_ammount=order_ammount))
    if response.is_fraud:
        logger.warning(f"Fraud detected for card {card_nr} with amount {order_ammount}")
    return response.is_fraud

def verify_transaction(card_nr, order_id, money):
    response = verification_stub.verifyTransaction(transaction_verification.PayRequest(card_nr=str(card_nr), order_id=order_id, money=money))
    logger.info(f"Transaction with {card_nr} {order_id} {money} result {response.verified}")
    if response.order_id != order_id: return False
    return response.verified

def get_suggested_books(ordered_books):
    response = suggestion_stub.suggest(suggestions.SuggestRequest(ordered_books=ordered_books))
    return response.suggested_books





def orchestrator_checkout_flow(order_id, order_data):
    fraud_stub.InitOrder(order_id, order_data)

    def fraud_event():
        resp = fraud_stub.IsFraud(order_id)
        if resp["fail"]:
            raise Exception(f"fraud failed with {order_data}")


# Import Flask.
# Flask is a web framework for Python.
# It allows you to build a web application quickly.
# For more information, see https://flask.palletsprojects.com/en/latest/
from flask import Flask, request, jsonify
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
    order_id = int.from_bytes(os.urandom(8)) # equivalent to random.randint(0, 2**63 - 1) a random 64 bit unsigned integer
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

    # Generate order_id

    verified = verify_transaction(request_data["creditCard"]["number"], order_id, quantity)
    if not verified:
        is_fraud = True

    # Dummy response following the provided YAML specification for the bookstore
    order_status_response = {
        'orderId': str(order_id),
        'status': ('Order Rejected' if is_fraud else 'Order Approved'),
        'suggestedBooks': suggested_books_dicts if not is_fraud else [],
    }

    return jsonify(order_status_response)

suggestion_channel.close()
verification_channel.close()
fraud_channel.close()

if __name__ == '__main__':
    # Run the app in debug mode to enable hot reloading.
    # This is useful for development.
    # The default port is 5000.
    app.run(host='0.0.0.0')
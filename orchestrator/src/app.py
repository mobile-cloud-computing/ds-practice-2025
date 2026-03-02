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

suggestions_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/suggestions'))
sys.path.insert(0, suggestions_grpc_path)
import suggestions_pb2 as suggestions
import suggestions_pb2_grpc as suggestions_grpc

transaction_verification_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/transaction_verification'))
sys.path.insert(0, transaction_verification_grpc_path)
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc

from flask import Flask, request
from flask_cors import CORS
import json
import grpc
import logging
logging.basicConfig(level=logging.INFO)

def detect(card_number, order_amount):
    try:
        # Establish a connection with the fraud-detection gRPC service.
        with grpc.insecure_channel('fraud_detection:50051') as channel:
            # Create a stub object.
            stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
            # Call the service through the stub object.
            response = stub.CheckFraud(fraud_detection.FraudRequest(card_number=card_number, order_amount=order_amount))
        return response.is_fraud
    except Exception as e:
        logging.error(f"gRPC Call Failed: {e}")
        return True # default to fraud if error

def get_suggestions(items):
    try:
        with grpc.insecure_channel('suggestions:50053') as channel:
            stub = suggestions_grpc.SuggestionsServiceStub(channel)
            # Build the request from checkout items
            book_items = [suggestions.BookItem(name=item.get('name', ''), quantity=item.get('quantity', 0)) for item in items]
            response = stub.GetSuggestions(suggestions.SuggestionsRequest(items=book_items))
        return [{'bookId': book.bookId, 'title': book.title, 'author': book.author} for book in response.books]
    except Exception as e:
        logging.error(f"gRPC Call Failed: {e}")
        return []

def verify_transaction(payload: dict):
    """
    Call Transaction Verification service.
    Returns (is_valid: bool, message: str)
    Default to invalid if error.
    """
    try:
        logging.info("Starting transaction verification")

        user = payload.get("user", {}) or {}
        name = user.get("name", "")
        email = user.get("contact", "")

        cc = payload.get("creditCard", {}) or {}
        card_number = cc.get("number", "")
        expiration_date = cc.get("expirationDate", "") or cc.get("expiry", "")
        cvv = cc.get("cvv", "")
        billing = payload.get("billingAddress", {}) or {}

        logging.info(
            f"Verification payload extracted: "
            f"name='{name}', email='{email}', "
            f"card_number_ending='{card_number[-4:] if card_number else ''}'"
        )

        with grpc.insecure_channel("transaction_verification:50052") as channel:
            stub = transaction_verification_grpc.TransactionVerificationServiceStub(channel)
            req = transaction_verification.VerificationRequest(
                name=name,
                email=email,
                card_number=card_number,
                expiration_date=expiration_date,
                cvv=cvv,
                billing_address=transaction_verification.BillingAddress(
                    street=billing.get("street", ""),
                    city=billing.get("city", ""),
                    state=billing.get("state", ""),
                    zip=billing.get("zip", ""),
                    country=billing.get("country", ""),
                )
            )

            logging.info("Calling TransactionVerification gRPC service")
            res = stub.VerifyTransaction(req)

        logging.info(
            f"TransactionVerification response: "
            f"is_valid={res.is_valid}, message='{res.message}'"
        )

        return bool(res.is_valid), getattr(res, "message", "")

    except Exception as e:
        logging.error(f"Transaction Verification gRPC Call Failed: {e}")
        return False, "Transaction verification service error"

app = Flask(__name__)
# Enable CORS for the app.
CORS(app, resources={r'/*': {'origins': '*'}})

# Define a GET endpoint.
@app.route('/', methods=['GET'])
def index():
    """
    Responds with 'Hello, [name]' when a GET request is made to '/' endpoint.
    """
    # Test the fraud-detection gRPC service.
    response = 'Hello, orchestrator!'
    # Return the response.
    return response

@app.route('/suggestions', methods=['POST'])
def suggestions_endpoint():
    """
    Tests the suggestions gRPC service by returning suggested books for given items.
    """
    request_data = json.loads(request.data)
    items = request_data.get('items', [])
    suggested_books = get_suggestions(items)
    return {'suggestedBooks': suggested_books}

@app.route('/checkout', methods=['POST'])
def checkout():
    """
    Responds with a JSON object containing the order ID, status, and suggested books.
    """
    # Get request object data to json
    request_data = json.loads(request.data)
    # Print request object data
    print("Request Data:", request_data.get('items'))

    is_valid, message = verify_transaction(request_data)
    if not is_valid:
        return {
            "orderId": "12345",
            "status": "Order Denied",
            "reason":  "Invalid transaction data",
            "suggestedBooks": [
                {"bookId": "123", "title": "The Best Book", "author": "Author 1"},
                {"bookId": "456", "title": "The Second Best Book", "author": "Author 2"},
            ],
        }, 200




    # Extract values needed for fraud check
    card_number = request_data.get('creditCard', {}).get('number', '')
    order_amount = str(sum(item.get('quantity', 0) for item in request_data.get('items', [])))

    # Call fraud detection gRPC service
    is_fraud = detect(card_number=card_number, order_amount=order_amount)

    # Call suggestions gRPC service
    items = request_data.get('items', [])
    suggested_books = get_suggestions(items)

    # Build response following the provided YAML specification for the bookstore
    order_status_response = {
        'orderId': '12345',
        'status': 'Order Denied' if is_fraud else 'Order Approved',
        'suggestedBooks': suggested_books
    }

    return order_status_response


if __name__ == '__main__':
    # Run the app in debug mode to enable hot reloading.
    # This is useful for development.
    # The default port is 5000.
    app.run(host='0.0.0.0')

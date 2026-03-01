import sys
import os
import grpc

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")

fraud_detection_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/fraud_detection'))
sys.path.insert(0, fraud_detection_grpc_path)
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc

transaction_verification_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/transaction_verification'))
sys.path.insert(0, transaction_verification_grpc_path)
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc

suggestions_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/suggestions'))
sys.path.insert(0, suggestions_grpc_path)
import suggestions_pb2 as suggestions
import suggestions_pb2_grpc as suggestions_grpc

def verify_transaction(user, items, card_number, card_expiry, card_cvv, order_amount):
    try:
        with grpc.insecure_channel('transaction_verification:50052') as channel:
            # Create a stub object.
            stub = transaction_verification_grpc.TransactionVerificationServiceStub(channel)
            user_data = transaction_verification.UserData(
                name=user.get('name', ''),
                email=user.get('email', ''),
                address=user.get('address', '')
            )
            # Convert items to protobuf format
            item_msgs = [
                transaction_verification.Item(
                    name=str(item.get('name', '')),
                    quantity=float(item.get('quantity', 0))
                ) for item in items
            ]
            print(f"Verifying transaction for user: {user_data.name}, items: {[item.name for item in item_msgs]}, card_number: {card_number}, order_amount: {order_amount}")
            # Build request
            req = transaction_verification.TransactionVerificationRequest(
                user=user_data,
                items=item_msgs,
                card_number=card_number,
                card_expiry=card_expiry,
                card_cvv=card_cvv,
                order_amount=order_amount
            )
            response = stub.VerifyTransaction(req)
            print(f"Transaction verification response: is_verified={response.is_verified}")
        return response.is_verified
    except Exception as e:
        print(f"Error connecting to transaction verification service: {e}")
        return False

def detect_fraud(card_number, order_amount):
    try:
        # Establish a connection with the fraud-detection gRPC service.
        with grpc.insecure_channel('fraud_detection:50051') as channel:
            # Create a stub object.
            stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
            # Call the service through the stub object.
            response = stub.DetectFraud(fraud_detection.FraudDetectionRequest(card_number=card_number, order_amount=order_amount))
        return response.is_fraud
    except Exception as e:
        print(f"Error connecting to fraud detection service: {e}")
        return False  # Default to not fraud if there's an error

def get_suggestions(user_id):
    # Connect to the suggestions gRPC service and get book suggestions 
    try:
        with grpc.insecure_channel('suggestions:50053') as channel:
            # Create a stub object.
            stub = suggestions_grpc.SuggestionsServiceStub(channel)
            response = stub.GetSuggestions(suggestions.SuggestionsRequest(user_id=str(user_id)))
        return list(response.suggestions)
    except Exception as e:
        print(f"Error connecting to suggestions service: {e}")
        return []

def parse_suggestion(suggestion_line):
    # Parse a suggestion line in the format "Title by Author" and return a dictionary with 'title' and 'author' keys.
    text = (suggestion_line or '').strip()
    if ' by ' in text:
        parts = text.split(' by ', 1)
        return {'title': parts[0].strip(), 'author': parts[1].strip()}
    return {'title': text, 'author': 'Unknown'}


# Import Flask.
# Flask is a web framework for Python.
# It allows you to build a web application quickly.
# For more information, see https://flask.palletsprojects.com/en/latest/
from flask import Flask, request
import logging
from flask_cors import CORS
import json
from concurrent.futures import ThreadPoolExecutor

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
    # Test the fraud-detection gRPC service.
    response = detect_fraud(card_number="9991234567890", order_amount=1500)
    # Return the response.
    return response

@app.route('/checkout', methods=['POST'])
def checkout():
    """
    Responds with a JSON object containing the order ID, status, and suggested books.
    """
    # Get request object data to json
    request_data = json.loads(request.data)
    try:
        print(f"Received checkout request: {request.data}")
        # Extract necessary information from the request data
        card_info = request_data.get('creditCard', {})
        card_number = card_info.get('number', '')
        card_expiry = card_info.get('expirationDate', '')
        card_cvv = card_info.get('cvv', '')
        order_amount = card_info.get('orderAmount', 0)
        user_id = request_data.get('userId', 'anonymous')

        user_info = request_data.get('user', {})
        address = request_data.get('billingAddress', {})
        address_str = ', '.join([str(address.get(k, '')) for k in ['street', 'city', 'state', 'zip', 'country']])
        user_data = {
            'name': user_info.get('name', ''),
            'email': user_info.get('contact', ''),
            'address': address_str
        }
        items = request_data.get('items', [])

        with ThreadPoolExecutor() as executor:
            # THreadPoolExecutor allows us to run multiple tasks concurrently
            logging.info(f"Submitting fraud detection task to executor: card_number={card_number}, order_amount={order_amount}")
            fraud_future = executor.submit(detect_fraud, card_number, order_amount)
            transaction_future = executor.submit(verify_transaction, user_data, items, card_number, card_expiry, card_cvv, order_amount)
            is_verified = transaction_future.result()
            suggestions_future = executor.submit(get_suggestions, user_id)
            is_fraud = fraud_future.result()
            suggested_titles = suggestions_future.result()
        logging.info(f"Fraud detection completed: is_fraud={is_fraud}")
        logging.info(f"Transaction verification completed: is_verified={is_verified}")
        logging.info(f"Suggestions retrieval completed: suggested_titles={suggested_titles}")
        # Prepare the order status based on fraud detection and transaction verification results
        if is_fraud:
            status = 'Order Declined due to suspected fraud'
        elif not is_verified:
            status = 'Order Declined due to invalid transaction'
        else:
            status = 'Order Approved'

        order_status_response = {
            'orderId': '12345',
            'status': status,
            'suggestedBooks': [
                parse_suggestion(title) for title in suggested_titles[:3]
            ]
        }

        return order_status_response
    except Exception as e:
        logging.error(f"Error processing checkout request: {e}")
        return {'error': 'An error occurred while processing the checkout request'}, 500

if __name__ == '__main__':
    # Run the app in debug mode to enable hot reloading.
    # This is useful for development.
    # The default port is 5000.
    app.run(host='0.0.0.0')

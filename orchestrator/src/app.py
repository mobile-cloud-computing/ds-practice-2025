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

import grpc

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
    try:
        with grpc.insecure_channel('suggestions:50053') as channel:
            stub = suggestions_grpc.SuggestionsServiceStub(channel)
            response = stub.GetSuggestions(suggestions.SuggestionsRequest(user_id=str(user_id)))
        return list(response.suggestions)
    except Exception as e:
        print(f"Error connecting to suggestions service: {e}")
        return []

    

# Import Flask.
# Flask is a web framework for Python.
# It allows you to build a web application quickly.
# For more information, see https://flask.palletsprojects.com/en/latest/
from flask import Flask, request
import logging
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
    # Print request object data
    print("Request Data:", request_data.get('items'))

    from concurrent.futures import ThreadPoolExecutor

    try:
        logging.info(f"Received checkout request: {request.data}")

        card_info = request_data.get('creditCard', {})
        card_number = card_info.get('number', '')
        order_amount = card_info.get('orderAmount', 0)
        user_id = request_data.get('userId', 'anonymous')

        with ThreadPoolExecutor() as executor:
            logging.info(f"Submitting fraud detection task to executor: card_number={card_number}, order_amount={order_amount}")
            fraud_future = executor.submit(detect_fraud, card_number, order_amount)
            suggestions_future = executor.submit(get_suggestions, user_id)
            is_fraud = fraud_future.result()
            suggested_titles = suggestions_future.result()
        logging.info(f"Fraud detection completed: is_fraud={is_fraud}")

        # add static examples to suggestions
        if not is_fraud:
            suggested_titles.extend(["Book C", "Book D", "Book E"])

        # Dummy response following the provided YAML specification for the bookstore
        order_status_response = {
            'orderId': '12345',
            'status': 'Order Approved' if not is_fraud else 'Order Declined due to suspected fraud',
            'suggestedBooks': [
                {'bookId': str(i + 1), 'title': title, 'author': 'Unknown'}
                for i, title in enumerate(suggested_titles)
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

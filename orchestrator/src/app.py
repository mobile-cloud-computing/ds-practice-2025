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
    response = greet(name='orchestrator')
    # Return the response.
    return response

@app.route('/checkout', methods=['POST'])
def checkout():
    """
    Responds with a JSON object containing the order ID, status, and suggested books.
    """
    request_data = request.get_json(silent=True)

    if request_data is None:
        return {
            "error": {
                "code": "BAD_REQUEST",
                "message": "Request body must be valid JSON."
            }
        }, 400

    user = request_data.get("user", {})
    items = request_data.get("items", [])
    shipping_method = request_data.get("shippingMethod")
    terms_accepted = request_data.get("termsAndConditionsAccepted", False)

    user_name = user.get("name")
    user_contact = user.get("contact")
    user_comment = user.get("userComment", "")

    credit_card = user.get("creditCard", {})
    card_number = credit_card.get("number")
    expiration_date = credit_card.get("expirationDate")
    cvv = credit_card.get("cvv")

    print("FULL REQUEST DATA:", request_data)
    print("USER NAME:", user_name)
    print("USER CONTACT:", user_contact)
    print("USER COMMENT:", user_comment)
    print("ITEMS:", items)
    print("SHIPPING METHOD:", shipping_method)
    print("TERMS ACCEPTED:", terms_accepted)
    print("CARD NUMBER:", card_number)
    print("EXPIRATION DATE:", expiration_date)
    print("CVV:", cvv)

    # Basic validation
    if not user_name:
        return {
            "error": {
                "code": "BAD_REQUEST",
                "message": "User name is required."
            }
        }, 400

    if not user_contact:
        return {
            "error": {
                "code": "BAD_REQUEST",
                "message": "User contact is required."
            }
        }, 400

    if not items:
        return {
            "orderId": "12345",
            "status": "Order Rejected",
            "suggestedBooks": []
        }, 200

    if not terms_accepted:
        return {
            "orderId": "12345",
            "status": "Order Rejected",
            "suggestedBooks": []
        }, 200

    if not card_number or not expiration_date or not cvv:
        return {
            "orderId": "12345",
            "status": "Order Rejected",
            "suggestedBooks": []
        }, 200

    # Dummy success response for now
    return {
        "orderId": "12345",
        "status": "Order Approved",
        "suggestedBooks": [
            {"bookId": "123", "title": "The Best Book", "author": "Author 1"},
            {"bookId": "456", "title": "The Second Best Book", "author": "Author 2"}
        ]
    }, 200


if __name__ == '__main__':
    # Run the app in debug mode to enable hot reloading.
    # This is useful for development.
    # The default port is 5000.
    app.run(host='0.0.0.0')

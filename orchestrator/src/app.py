import sys
import os

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
transaction_verification_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/transaction_verification'))
sys.path.insert(0, transaction_verification_grpc_path)
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc

fraud_detection_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/fraud_detection'))
sys.path.insert(0, fraud_detection_grpc_path)
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc

import grpc
import uuid

def greet(name='you'):
    # Establish a connection with the fraud-detection gRPC service.
    with grpc.insecure_channel('fraud_detection:50051') as channel:
        # Create a stub object.
        stub = fraud_detection_grpc.HelloServiceStub(channel)
        # Call the service through the stub object.
        response = stub.SayHello(fraud_detection.HelloRequest(name=name))
    return response.greeting


def verify_transaction(checkout_data):
    user = checkout_data.get("user", {})
    credit_card = checkout_data.get("creditCard", {})
    billing_address = checkout_data.get("billingAddress", {})
    items = checkout_data.get("items", [])

    with grpc.insecure_channel('transaction_verification:50052') as channel:
        stub = transaction_verification_grpc.TransactionVerificationServiceStub(channel)
        
        response = stub.VerifyTransaction(
            transaction_verification.TransactionVerificationRequest(
                transaction_id=checkout_data['orderId'],
                purchaser_name=user.get("name", ""),
                purchaser_email=user.get("contact", ""),
                credit_card_number=credit_card.get("number", ""),
                credit_card_expiration=credit_card.get("expirationDate", ""),
                credit_card_cvv=credit_card.get("cvv", ""),
                billing_street=billing_address.get("street", ""),
                billing_city=billing_address.get("city", ""),
                billing_state=billing_address.get("state", ""),
                billing_zip=billing_address.get("zip", ""),
                billing_country=billing_address.get("country", ""),
                items=[
                    transaction_verification.Item(
                        name=item.get("name", ""),
                        quantity=item.get("quantity", 0),
                    )
                    for item in items
                ],
                terms_accepted=checkout_data.get("termsAccepted", False),
            )
        )
    return response


def detect_fraud(checkout_data):
    user = checkout_data.get("user", {})
    credit_card = checkout_data.get("creditCard", {})
    billing_address = checkout_data.get("billingAddress", {})

    with grpc.insecure_channel('fraud_detection:50051') as channel:
        stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
        response = stub.DetectFraud(
            fraud_detection.FraudDetectionRequest(
                transaction_id=checkout_data['orderId'],
                purchaser_name=user.get("name", ""),
                purchaser_email=user.get("contact", ""),
                credit_card_number=credit_card.get("number", ""),
                billing_street=billing_address.get("street", ""),
                billing_city=billing_address.get("city", ""),
                billing_state=billing_address.get("state", ""),
                billing_zip=billing_address.get("zip", ""),
                billing_country=billing_address.get("country", ""),
            )
        )
    return response

# Import Flask.
# Flask is a web framework for Python.
# It allows you to build a web application quickly.
# For more information, see https://flask.palletsprojects.com/en/latest/
from flask import Flask, request
from flask_cors import CORS
import json
import logging


# Create a simple Flask app.
app = Flask(__name__)
# Enable CORS for the app.
CORS(app, resources={r'/*': {'origins': '*'}})

logging.basicConfig(
    level=logging.INFO,
    format="===LOG=== %(levelname)s %(asctime)s %(name)s %(message)s"
)
logger = logging.getLogger("orchestrator")

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
    # Get request object data to json
    request_data = json.loads(request.data)
    request_data['orderId'] = str(uuid.uuid4())
    # Print request object data
    print("Request Data:", request_data.get('items'))

    # FIRST we verify the transaction using the Transaction Verification gRPC service.
    verification = verify_transaction(request_data)
    if not verification.is_valid:
        logger.warning(
            "order=%s rejected_by=transaction_verification reasons=%s",
            request_data['orderId'],
            list(verification.reasons),
        )

        return {
            "status": "Order Rejected",
            "reasons": list(verification.reasons),
            "suggestedBooks": [],
        }

    # SECOND we check for fraud using the Fraud Detection gRPC service.
    fraud_check = detect_fraud(request_data)
    if fraud_check.is_fraud:
        order_status_response = {
            'status': 'Order Rejected',
            'suggestedBooks': []
        }
        print(f"Order rejected due to fraud check: {fraud_check.reason}")
    else:
        # Dummy
        order_status_response = {
            'status': 'Order Approved',
            'suggestedBooks': [
                {'bookId': '123', 'title': 'The Best Book', 'author': 'Author 1'},
                {'bookId': '456', 'title': 'The Second Best Book', 'author': 'Author 2'}
            ]
        }

    logger.info("order=%s approved", request_data['orderId'])
    return order_status_response


if __name__ == '__main__':
    # Run the app in debug mode to enable hot reloading.
    # This is useful for development.
    # The default port is 5000.
    app.run(host='0.0.0.0')

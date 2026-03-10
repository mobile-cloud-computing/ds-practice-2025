import sys
import os

import logging
logging.basicConfig(level=logging.INFO)

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
fraud_detection_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/fraud_detection'))
sys.path.insert(0, fraud_detection_grpc_path)
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
transaction_verification_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/transaction_verification'))
sys.path.insert(0, transaction_verification_grpc_path)
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc

import grpc
'''
def greet(name='you'):
    # Establish a connection with the fraud-detection gRPC service.
    with grpc.insecure_channel('fraud_detection:50051') as channel:
        # Create a stub object.
        stub = fraud_detection_grpc.HelloServiceStub(channel)
        # Call the service through the stub object.
        response = stub.SayHello(fraud_detection.HelloRequest(name=name))
    return response.greeting
'''

def call_fraud_detection(card_number, order_amount):
    try:
        with grpc.insecure_channel('fraud_detection:50051') as channel:
            stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
            request_obj = fraud_detection.FraudRequest(card_number=card_number,order_amount=float(order_amount))
            response = stub.CheckFraud(request_obj)
            return response.is_fraud
    except Exception as e:
        logging.error(f"gRPC Call Failed: {e}")
        return True # Default to fraud if errors


def call_transaction_verification(request_data):
    user_info = request_data.get("user", {})
    card_info = request_data.get("creditCard", {})
    billing_address = request_data.get("billingAddress", {})
    items = request_data.get("items", {})

    try:
        with grpc.insecure_channel('transaction_verification:50052') as channel:
            stub = transaction_verification_grpc.TransactionVerificationServiceStub(channel)
            request_obj = transaction_verification.VerifyRequest(
                user_name=user_info.get("name", ""),
                contact=user_info.get("contact", ""),
                card_number=card_info.get("number", ""),
                
                street=billing_address.get("street", ""),
                city=billing_address.get("city", ""),
                state=billing_address.get("state", ""),
                zip_code=billing_address.get("zip", ""),
                country=billing_address.get("country", ""),
                
                shipping_method=request_data.get("shippingMethod", ""),
                terms_accepted=request_data.get("termsAccepted", False)
            )
            
            response = stub.VerifyTransaction(request_obj)
            return response.is_valid
    except Exception as e:
        logging.error(f"gRPC Call Failed: {e}")
        return False # Default to invalid if errors

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
    # Get request object data to json
    request_data = json.loads(request.data)

    '''
    const data = {
        user: {
            name: formData.get('name'),
            contact: formData.get('contact'),
        },
        creditCard: {
            number: formData.get('creditCard'),
            expirationDate: formData.get('expirationDate'),
            cvv: formData.get('cvv'),
        },
        userComment: formData.get('userComment'),
        items: items,
        billingAddress: {
            street: formData.get('billingStreet'),
            city: formData.get('billingCity'),
            state: formData.get('billingState'),
            zip: formData.get('billingZip'),
            country: formData.get('billingCountry'),
        },
        shippingMethod: formData.get('shippingMethod'),
        giftWrapping: formData.get('giftWrapping') === 'on',
        termsAccepted: formData.get('terms') === 'on',
    };
    '''

    # Log request object data
    logging.info(f"Received request Data: {request_data.get('items')}")

    ##### THREADING #####
    from concurrent.futures import ThreadPoolExecutor

    try:
        logging.info("Orchestrator received order data", extra={"order_data": request_data})
        
        user_info = request_data.get("user", {})
        name = user_info.get("name", "")
        contact = user_info.get("contact", "")

        card_info = request_data.get("creditCard", {})
        card_number = card_info.get("number", "")
        order_amount = card_info.get("order_amount", 0.0)

        user_comment = request_data.get("userComment", "")

        items = request_data.get("items", {})

        billing_address = request_data.get("billingAddress", {})
        street = billing_address.get("street", "")
        city = billing_address.get("city", "")
        state = billing_address.get("state", "")
        zip_code = billing_address.get("zip", "")
        country = billing_address.get("country", "")

        shipping_method = request_data.get("shippingMethod", "") #Standard, Express, Next-day

        gift_wrapping = request_data.get("giftWrapping", False)

        terms_accepted = request_data.get("termsAccepted", False)




        with ThreadPoolExecutor(max_workers=3) as executor:
            logging.info("Starting thread for FraudDetection")
            future_fraud = executor.submit(call_fraud_detection, card_number, order_amount)

            logging.info("Starting thread for TransactionVerification")
            future_verification = executor.submit(call_transaction_verification, request_data)

            is_fraud = future_fraud.result()
            logging.info(f"Thread returned fraud status: {is_fraud}")

        order_status_response = {
            'orderId': '12345',
            'status': 'Order Denied' if is_fraud else 'Order Approved',
            'suggestedBooks': [
                {'bookId': '123', 'title': 'The Best Book', 'author': 'Author 1'},
                {'bookId': '456', 'title': 'The Second Best Book', 'author': 'Author 2'}
            ]
        }

        logging.info("Checkout completed", extra={"order_status_response": order_status_response})
        return order_status_response

    except Exception as e:
        logging.exception("Checkout endpoint failed")
        return {"error": str(e)}

if __name__ == '__main__':
    # Run the app in debug mode to enable hot reloading.
    # This is useful for development.
    # The default port is 5000.
    app.run(host='0.0.0.0')

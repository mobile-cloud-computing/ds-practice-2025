import sys
import os
import logging
logging.basicConfig(level=logging.INFO)

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
fraud_detection_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/fraud_detection'))
sys.path.insert(0, fraud_detection_grpc_path)
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc

import grpc

def greet(name='you'):
    with grpc.insecure_channel('fraud_detection:50051') as channel:
        stub = fraud_detection_grpc.HelloServiceStub(channel)
        response = stub.SayHello(fraud_detection.HelloRequest(name=name))
    return response.greeting

def call_fraud_detection(card_number, order_amount):
    try:
        with grpc.insecure_channel('fraud_detection:50051') as channel:
            stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
            request_obj = fraud_detection.FraudRequest(card_number=card_number, order_amount=order_amount)
            response = stub.CheckFraud(request_obj)
        return response.is_fraud
    except Exception as e:
        logging.error(f"gRPC call failed: {e}")
        return True

from flask import Flask, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r'/*': {'origins': '*'}})

@app.route('/', methods=['GET'])
def index():
    response = greet(name='orchestrator')
    return response

@app.route('/checkout', methods=['POST'])
def checkout():
    from concurrent.futures import ThreadPoolExecutor
    try:
        # force=True parses JSON regardless of Content-Type header
        # silent=True returns None instead of error if parsing fails
        request_data = request.get_json(force=True, silent=True) or {}
        logging.info(f"Checkout request received: {request_data}")

        card_info = request_data.get("creditCard", {})
        card_number = card_info.get("number", "")
        order_amount = request_data.get("totalAmount", 0.0)

        with ThreadPoolExecutor(max_workers=3) as executor:
            fraud_future = executor.submit(call_fraud_detection, card_number, order_amount)
            is_fraud = fraud_future.result()
            logging.info(f"Fraud detection result: {is_fraud}")

        if is_fraud:
            order_status_response = {
                "orderId": "1234567890",
                "status": "Order Rejected",
                "suggestedBooks": []
            }
        else:
            order_status_response = {
                "orderId": "1234567890",
                "status": "Order Approved",
                "suggestedBooks": [
                    {'bookId': '123', 'title': 'Book 1', 'author': 'Author 1'},
                    {'bookId': '456', 'title': 'Book 2', 'author': 'Author 2'},
                    {'bookId': '789', 'title': 'Book 3', 'author': 'Author 3'}
                ]
            }

        logging.info(f"Checkout completed: {order_status_response}")
        return order_status_response

    except Exception as e:
        logging.error(f"Checkout failed: {e}")
        return {"error": {"message": str(e)}}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0')
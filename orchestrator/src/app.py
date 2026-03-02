import sys
import os

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")

# Import fraud detection stubs
fraud_detection_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/fraud_detection'))
sys.path.insert(0, fraud_detection_grpc_path)
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc

# Import transaction verification stubs
transaction_verification_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/transaction_verification'))
sys.path.insert(0, transaction_verification_grpc_path)
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc

import grpc
from flask import Flask, request
from flask_cors import CORS

def greet(name='you'):
    with grpc.insecure_channel('fraud_detection:50051') as channel:
        stub = fraud_detection_grpc.HelloServiceStub(channel)
        response = stub.SayHello(fraud_detection.HelloRequest(name=name))
    return response.greeting

def call_fraud_detection(card_number, order_amount):
    try:
        with grpc.insecure_channel('fraud_detection:50051') as channel:
            stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
            request_obj = fraud_detection.FraudRequest(
                card_number=card_number,
                order_amount=order_amount
            )
            response = stub.CheckFraud(request_obj)
        return response.is_fraud
    except Exception as e:
        print(f"Fraud detection gRPC call failed: {e}")
        return True

def call_transaction_verification(request_data):
    try:
        with grpc.insecure_channel('transaction_verification:50052') as channel:
            stub = transaction_verification_grpc.TransactionVerificationServiceStub(channel)

            card_info = request_data.get("creditCard", {})
            user_info = request_data.get("user", {})
            items = request_data.get("items", [])

            grpc_items = [
                transaction_verification.Item(
                    name=item.get("name", ""),
                    quantity=item.get("quantity", 0)
                ) for item in items
            ]

            request_obj = transaction_verification.TransactionRequest(
                card_number=card_info.get("number", ""),
                card_expiration=card_info.get("expirationDate", ""),
                card_cvv=card_info.get("cvv", ""),
                items=grpc_items,
                user_name=user_info.get("name", ""),
                user_contact=user_info.get("contact", "")
            )
            response = stub.VerifyTransaction(request_obj)
        return response.is_valid
    except Exception as e:
        print(f"Transaction verification gRPC call failed: {e}")
        return False

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
        request_data = request.get_json(force=True, silent=True) or {}
        print("Request Data:", request_data.get('items'))

        card_info = request_data.get("creditCard", {})
        card_number = card_info.get("number", "")
        order_amount = request_data.get("totalAmount", 0.0)

        # Run fraud detection and transaction verification in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            fraud_future = executor.submit(call_fraud_detection, card_number, order_amount)
            verify_future = executor.submit(call_transaction_verification, request_data)

            is_fraud = fraud_future.result()
            is_valid = verify_future.result()

        print(f"Fraud: {is_fraud}, Valid: {is_valid}")

        # Consolidate results
        if is_fraud or not is_valid:
            order_status_response = {
                'orderId': '12345',
                'status': 'Order Rejected',
                'suggestedBooks': []
            }
        else:
            order_status_response = {
                'orderId': '12345',
                'status': 'Order Approved',
                'suggestedBooks': [
                    {'bookId': '123', 'title': 'The Best Book', 'author': 'Author 1'},
                    {'bookId': '456', 'title': 'The Second Best Book', 'author': 'Author 2'}
                ]
            }

        return order_status_response

    except Exception as e:
        print(f"Checkout failed: {e}")
        return {"error": {"message": str(e)}}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0')
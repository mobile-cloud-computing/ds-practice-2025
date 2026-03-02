import sys
import os
import threading

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")

fraud_detection_grpc_path = os.path.abspath(
    os.path.join(FILE, '../../../utils/pb/fraud_detection')
)
sys.path.insert(0, fraud_detection_grpc_path)
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc

transaction_verification_grpc_path = os.path.abspath(
    os.path.join(FILE, '../../../utils/pb/transaction_verification')
)
sys.path.insert(0, transaction_verification_grpc_path)
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc

suggestions_grpc_path = os.path.abspath(
    os.path.join(FILE, '../../../utils/pb/suggestions')
)
sys.path.insert(0, suggestions_grpc_path)
import suggestions_pb2 as suggestions
import suggestions_pb2_grpc as suggestions_grpc

import grpc

from flask import Flask, request
from flask_cors import CORS


def greet(name='you'):
    with grpc.insecure_channel('fraud_detection:50051') as channel:
        stub = fraud_detection_grpc.HelloServiceStub(channel)
        response = stub.SayHello(fraud_detection.HelloRequest(name=name))
    return response.greeting


def detect_fraud(user_name, card_number, item_count):
    with grpc.insecure_channel('fraud_detection:50051') as channel:
        stub = fraud_detection_grpc.HelloServiceStub(channel)
        response = stub.CheckFraud(
            fraud_detection.FraudCheckRequest(
                user_name=user_name or "",
                card_number=card_number or "",
                item_count=item_count
            )
        )
    return response


def verify_transaction(user_name, user_contact, card_number, expiration_date, cvv, item_count, terms_accepted):
    with grpc.insecure_channel('transaction_verification:50052') as channel:
        stub = transaction_verification_grpc.TransactionVerificationServiceStub(channel)
        response = stub.VerifyTransaction(
            transaction_verification.TransactionVerificationRequest(
                user_name=user_name or "",
                user_contact=user_contact or "",
                card_number=card_number or "",
                expiration_date=expiration_date or "",
                cvv=cvv or "",
                item_count=item_count,
                terms_accepted=terms_accepted
            )
        )
    return response


def get_suggestions(user_name, item_count):
    with grpc.insecure_channel('suggestions:50053') as channel:
        stub = suggestions_grpc.SuggestionsServiceStub(channel)
        response = stub.GetSuggestions(
            suggestions.SuggestionsRequest(
                user_name=user_name or "",
                item_count=item_count
            )
        )
    return response


app = Flask(__name__)
CORS(app, resources={r'/*': {'origins': '*'}})


@app.route('/', methods=['GET'])
def index():
    response = greet(name='orchestrator')
    return response


@app.route('/checkout', methods=['POST'])
def checkout():
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
    masked_card_number = mask_fixed(card_number)
    expiration_date = credit_card.get("expirationDate")
    cvv = credit_card.get("cvv")
    print(
        "Received a request for checkout of user : {} for card number : {}".format(
            user_name, masked_card_number
        )
    )


    # Keep these simple bad-request checks locally
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

    item_count = len(items)

    results = {
        "fraud": None,
        "verification": None,
        "suggestions": None,
        "errors": []
    }

    def fraud_worker():
        try:
            print("Calling fraud_detection service...")
            results["fraud"] = detect_fraud(
                user_name=user_name,
                card_number=card_number,
                item_count=item_count
            )
            print(
                "fraud_detection result:",
                results["fraud"].is_fraud,
                results["fraud"].message
            )
        except Exception as e:
            error_msg = f"fraud_detection failed: {e}"
            print(error_msg)
            results["errors"].append(error_msg)

    def verification_worker():
        try:
            print("Calling transaction_verification service...")
            results["verification"] = verify_transaction(
                user_name=user_name,
                user_contact=user_contact,
                card_number=card_number,
                expiration_date=expiration_date,
                cvv=cvv,
                item_count=item_count,
                terms_accepted=terms_accepted
            )
            print(
                "transaction_verification result:",
                results["verification"].is_valid,
                results["verification"].message
            )
        except Exception as e:
            error_msg = f"transaction_verification failed: {e}"
            print(error_msg)
            results["errors"].append(error_msg)

    def suggestions_worker():
        try:
            print("Calling suggestions service...")
            results["suggestions"] = get_suggestions(
                user_name=user_name,
                item_count=item_count
            )
            print(
                "suggestions returned:",
                len(results["suggestions"].books),
                "books"
            )
        except Exception as e:
            error_msg = f"suggestions failed: {e}"
            print(error_msg)
            results["errors"].append(error_msg)

    fraud_thread = threading.Thread(target=fraud_worker)
    verification_thread = threading.Thread(target=verification_worker)
    suggestions_thread = threading.Thread(target=suggestions_worker)

    print("Starting worker threads...")
    fraud_thread.start()
    verification_thread.start()
    suggestions_thread.start()

    fraud_thread.join()
    verification_thread.join()
    suggestions_thread.join()
    print("All worker threads finished.")

    if results["errors"]:
        return {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "; ".join(results["errors"])
            }
        }, 500

    if results["fraud"] and results["fraud"].is_fraud:
        return {
            "orderId": "12345",
            "status": "Order Rejected",
            "suggestedBooks": []
        }, 200

    if results["verification"] and not results["verification"].is_valid:
        return {
            "orderId": "12345",
            "status": "Order Rejected",
            "suggestedBooks": []
        }, 200

    suggested_books = []
    if results["suggestions"]:
        for book in results["suggestions"].books:
            suggested_books.append({
                "bookId": book.bookId,
                "title": book.title,
                "author": book.author
            })

    return {
        "orderId": "12345",
        "status": "Order Approved",
        "suggestedBooks": suggested_books
    }, 200

def mask_fixed(card: str) -> str:
    digits = ''.join(c for c in str(card) if c.isdigit())
    masked = '*' * 12 + digits[-4:].rjust(4, '*')
    return ' '.join(masked[i:i+4] for i in range(0, 16, 4))

if __name__ == '__main__':
    app.run(host='0.0.0.0')
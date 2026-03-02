import sys
import os

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")

fd_grpc_path = os.path.abspath(os.path.join(FILE, "../../../utils/pb/fraud_detection"))
sys.path.insert(0, fd_grpc_path)
import fraud_detection_pb2 as fd_pb2
import fraud_detection_pb2_grpc as fd_grpc

sg_grpc_path = os.path.abspath(os.path.join(FILE, "../../../utils/pb/suggestions"))
sys.path.insert(0, sg_grpc_path)
import suggestions_pb2 as sg_pb2
import suggestions_pb2_grpc as sg_grpc

tv_grpc_path = os.path.abspath(
    os.path.join(FILE, "../../../utils/pb/transaction_verification")
)
sys.path.insert(0, tv_grpc_path)
import transaction_verification_pb2 as tv_pb2
import transaction_verification_pb2_grpc as tv_grpc

from flask import Flask, request
from flask_cors import CORS
import json
import grpc
import logging

logging.basicConfig(level=logging.INFO)


def detect_fraud(card_number, order_amount):
    try:
        # Establish a connection with the fraud-detection gRPC service.
        with grpc.insecure_channel("fraud_detection:50051") as channel:
            # Create a stub object.
            stub = fd_grpc.FraudDetectionServiceStub(channel)
            # Call the service through the stub object.
            response = stub.CheckFraud(
                fd_pb2.FraudRequest(card_number=card_number, order_amount=order_amount)
            )
        return response.is_fraud
    except Exception as e:
        logging.error(f"gRPC Call Failed: {e}")
        return True  # default to fraud if error


def get_suggestions(items):
    try:
        with grpc.insecure_channel("suggestions:50053") as channel:
            stub = sg_grpc.SuggestionsServiceStub(channel)
            # Build the request from checkout items
            book_items = [
                sg_pb2.BookItem(
                    name=item.get("name", ""), quantity=item.get("quantity", 0)
                )
                for item in items
            ]
            response = stub.GetSuggestions(sg_pb2.SuggestionsRequest(items=book_items))
        return [
            {"bookId": book.bookId, "title": book.title, "author": book.author}
            for book in response.books
        ]
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
            stub = tv_grpc.TransactionVerificationServiceStub(channel)
            req = tv_pb2.VerificationRequest(
                name=name,
                email=email,
                card_number=card_number,
                expiration_date=expiration_date,
                cvv=cvv,
                billing_address=tv_pb2.BillingAddress(
                    street=billing.get("street", ""),
                    city=billing.get("city", ""),
                    state=billing.get("state", ""),
                    zip=billing.get("zip", ""),
                    country=billing.get("country", ""),
                ),
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
CORS(app, resources={r"/*": {"origins": "*"}})


# Define a GET endpoint.
@app.route("/", methods=["GET"])
def index():
    """
    Responds with 'Hello, [name]' when a GET request is made to '/' endpoint.
    """
    # Test the fraud-detection gRPC service.
    response = "Hello, orchestrator!"
    # Return the response.
    return response


# @app.route("/suggestions", methods=["POST"])
# def suggestions_endpoint():
#     """
#     Tests the suggestions gRPC service by returning suggested books for given items.
#     """
#     request_data = json.loads(request.data)
#     items = request_data.get("items", [])
#     suggested_books = get_suggestions(items)
#     return {"suggestedBooks": suggested_books}


@app.route("/checkout", methods=["POST"])
def checkout():
    """Process a checkout request through the sequential pipeline: transaction verification → fraud detection → suggestions."""
    # Get request object data to json
    request_data = json.loads(request.data)
    logging.info(
        f"Checkout request received with {len(request_data.get('items', []))} items"
    )

    items = request_data.get("items", [])
    card_number = request_data.get("creditCard", {}).get("number", "")
    order_amount = str(sum(item.get("quantity", 0) for item in items))

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=1) as executor:
        future_fraud = executor.submit(detect_fraud, card_number, order_amount)
        future_verification = executor.submit(verify_transaction, request_data)
        future_suggestions = executor.submit(get_suggestions, items)

        is_fraud = future_fraud.result()
        is_valid, message = future_verification.result()
        suggested_books = future_suggestions.result()

    if not is_valid:
        return {
            "orderId": "12345",
            "status": "Order Denied",
            "reason": message or "Invalid transaction data",
            "suggestedBooks": [],
        }, 200

    order_status_response = {
        "orderId": "12345",
        "status": "Order Denied" if is_fraud else "Order Approved",
        "reason": "Fraud detected" if is_fraud else "",
        "suggestedBooks": suggested_books,
    }

    return order_status_response


if __name__ == "__main__":
    # Run the app in debug mode to enable hot reloading.
    # This is useful for development.
    # The default port is 5000.
    app.run(host="0.0.0.0")

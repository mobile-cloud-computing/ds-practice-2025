import sys
import os

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

# Import Flask.
from flask import Flask, request
from flask_cors import CORS


def greet(name='you'):
    # Establish a connection with the fraud-detection gRPC service.
    with grpc.insecure_channel('fraud_detection:50051') as channel:
        # Create a stub object.
        stub = fraud_detection_grpc.HelloServiceStub(channel)
        # Call the service through the stub object.
        response = stub.SayHello(fraud_detection.HelloRequest(name=name))
    return response.greeting


def verify_transaction(user_name, user_contact, card_number, expiration_date, cvv, item_count, terms_accepted):
    # Establish a connection with the transaction_verification gRPC service.
    with grpc.insecure_channel('transaction_verification:50052') as channel:
        # Create a stub object.
        stub = transaction_verification_grpc.TransactionVerificationServiceStub(channel)
        # Call the service through the stub object.
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
    # Establish a connection with the suggestions gRPC service.
    with grpc.insecure_channel('suggestions:50053') as channel:
        # Create a stub object.
        stub = suggestions_grpc.SuggestionsServiceStub(channel)
        # Call the service through the stub object.
        response = stub.GetSuggestions(
            suggestions.SuggestionsRequest(
                user_name=user_name or "",
                item_count=item_count
            )
        )
    return response


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

    print("Calling transaction_verification service...")
    verification_response = verify_transaction(
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
        verification_response.is_valid,
        verification_response.message
    )

    if not verification_response.is_valid:
        return {
            "orderId": "12345",
            "status": "Order Rejected",
            "suggestedBooks": []
        }, 200

    print("Calling suggestions service...")
    suggestions_response = get_suggestions(
        user_name=user_name,
        item_count=item_count
    )
    print("suggestions returned:", len(suggestions_response.books), "books")

    suggested_books = []
    for book in suggestions_response.books:
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


if __name__ == '__main__':
    # Run the app in debug mode to enable hot reloading.
    # This is useful for development.
    # The default port is 5000.
    app.run(host='0.0.0.0')
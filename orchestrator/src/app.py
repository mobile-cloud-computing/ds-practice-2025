import queue
import sys
import os
import threading

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")

fraud_detection_grpc_path = os.path.abspath(
    os.path.join(FILE, "../../../utils/pb/fraud_detection")
)
transaction_verification_grpc_path = os.path.abspath(
    os.path.join(FILE, "../../../utils/pb/transaction_verification")
)
suggestions_grpc_path = os.path.abspath(
    os.path.join(FILE, "../../../utils/pb/suggestions")
)

sys.path.insert(0, fraud_detection_grpc_path)
sys.path.insert(1, transaction_verification_grpc_path)
sys.path.insert(2, suggestions_grpc_path)

import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc
import suggestions_pb2 as suggestions
import suggestions_pb2_grpc as suggestions_grpc

import grpc
from google.protobuf.json_format import MessageToDict

# Import Flask.
# Flask is a web framework for Python.
# It allows you to build a web application quickly.
# For more information, see https://flask.palletsprojects.com/en/latest/
from flask import Flask, request, jsonify
from flask_cors import CORS
import json

# Create a simple Flask app.
app = Flask(__name__)
# Enable CORS for the app.
CORS(app, resources={r"/*": {"origins": "*"}})


def call_fraud_detection(number, result):
    with grpc.insecure_channel("fraud_detection:50051") as channel:
        # Create a stub object.
        stub = fraud_detection_grpc.FraudServiceStub(channel)
        # Call the service through the stub object.
        response = stub.CheckFraud(fraud_detection.FraudRequest(number=number))
        result.put(("is_fraud", response.is_fraud))


def call_transaction_verification(cvv, result):
    with grpc.insecure_channel("transaction_verification:50052") as channel:
        # Create a stub object.
        stub = transaction_verification_grpc.TransactionVerificationServiceStub(channel)
        # Call the service through the stub object.
        response = stub.VerifyTransaction(
            transaction_verification.TransactionRequest(id="123", cvv=int(cvv))
        )
        result.put(("is_verified", response.is_verified))


def call_suggestions(comment, result):
    with grpc.insecure_channel("suggestions:50053") as channel:
        # Create a stub object.
        stub = suggestions_grpc.SuggestionServiceStub(channel)
        # Call the service through the stub object.
        response = stub.GetSuggestions(suggestions.SuggestionRequest(comment=comment))

        # Convert gRPC response to dictionary
        response_dict = MessageToDict(response)
        suggestions_list = response_dict.get("suggestions", [])

        # Put suggestions directly into the result
        result.put(("suggestions", suggestions_list))


@app.route("/checkout", methods=["POST"])
def checkout():
    """
    Responds with a JSON object containing the order ID, status, and suggested books.
    """
    # Get request object data to json
    request_data = json.loads(request.data)
    result_queue = queue.Queue()

    threads = [
        threading.Thread(
            target=call_fraud_detection,
            args=(request_data["creditCard"]["number"], result_queue),
        ),
        threading.Thread(
            target=call_transaction_verification,
            args=(request_data["creditCard"]["cvv"], result_queue),
        ),
        threading.Thread(
            target=call_suggestions, args=(request_data["userComment"], result_queue)
        ),
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    results = {}
    while not result_queue.empty():
        key, value = result_queue.get()
        results[key] = value

    order_status_response = {
        "orderId": "12345",
        "status": (
            "Order Rejected"
            if results.get("is_fraud", False) or not results.get("is_verified", False)
            else "Order Approved"
        ),
        "suggestedBooks": [
            {"bookId": str(i + 1), "title": title, "author": "Unknown"}
            for i, title in enumerate(results.get("suggestions", []))
        ],
    }

    return order_status_response


if __name__ == "__main__":
    # Run the app in debug mode to enable hot reloading.
    # This is useful for development.
    # The default port is 5000.
    app.run(host="0.0.0.0")

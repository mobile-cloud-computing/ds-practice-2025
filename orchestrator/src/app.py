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
    try:
        print(f"Starting fraud check request")
        with grpc.insecure_channel("fraud_detection:50051") as channel:
            stub = fraud_detection_grpc.FraudServiceStub(channel)
            response = stub.CheckFraud(fraud_detection.FraudRequest(number=number))
            print(f"Fraud check result recieved")
            result.put(("is_fraud", response.is_fraud))
    except Exception as e:
        print(f"ERROR in fraud detection: {str(e)}")
        result.put(("is_fraud", True))


def call_transaction_verification(cvv, result):
    try:
        print(f"Starting transaction verification request")
        with grpc.insecure_channel("transaction_verification:50052") as channel:
            stub = transaction_verification_grpc.TransactionVerificationServiceStub(
                channel
            )
            response = stub.VerifyTransaction(
                transaction_verification.TransactionRequest(id="123", cvv=int(cvv))
            )
            print(f"transaction verification result recieved")
            result.put(("is_verified", response.is_verified))

    except Exception as e:
        print(f"ERROR in transaction verification: {str(e)}")
        result.put(("is_verified", False))


def call_suggestions(comment, result):
    try:
        print(f"Starting book suggestions request")
        with grpc.insecure_channel("suggestions:50053") as channel:
            stub = suggestions_grpc.SuggestionServiceStub(channel)
            response = stub.GetSuggestions(
                suggestions.SuggestionRequest(comment=comment)
            )
            print(f"Book suggestions recieved")
            response_dict = MessageToDict(response)
            suggestions_list = response_dict.get("suggestions", [])
            result.put(("suggestions", suggestions_list))

    except Exception as e:
        print(f"ERROR in suggestions service: {str(e)}")
        result.put(("suggestions", []))


@app.route("/checkout", methods=["POST"])
def checkout():
    try:
        print(f"Received new checkout request")

        request_data = json.loads(request.data)
        result_queue = queue.Queue()

        print(f"Processing order for user: {request_data.get('userId', 'unknown')}")
        print(f"Creating worker threads")
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
                target=call_suggestions,
                args=(request_data["userComment"], result_queue),
            ),
        ]

        print(f"Starting worker threads")
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()
        print(f"Threads processing completed")

        results = {}
        while not result_queue.empty():
            key, value = result_queue.get()
            results[key] = value
        print(f"Final results: {results}")

        status = "Order Approved"
        if results.get("is_fraud", False):
            status = "Order Rejected (Fraud detected)"
        elif not results.get("is_verified", False):
            status = "Order Rejected (Transaction verification failed)"

        print(f"Sending checkout response to user")

        return {
            "orderId": "12345",
            "status": status,
            "suggestedBooks": [
                {"bookId": str(i + 1), "title": title, "author": "Unknown"}
                for i, title in enumerate(results.get("suggestions", []))
            ],
        }

    except json.JSONDecodeError:
        print(f"ERROR: Invalid JSON received")
        return jsonify({"error": "Invalid JSON"}), 400
    except KeyError as e:
        print(f"ERROR: Missing field {str(e)}")
        return jsonify({"error": f"Missing required field: {str(e)}"}), 400
    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    # Run the app in debug mode to enable hot reloading.
    # This is useful for development.
    # The default port is 5000.
    app.run(host="0.0.0.0")

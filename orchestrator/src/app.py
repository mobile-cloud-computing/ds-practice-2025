import os
import sys
import json
import grpc

from flask import Flask, request, jsonify
from flask_cors import CORS

# Import gRPC generated stubs 
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
pb_root = os.path.abspath(os.path.join(FILE, "../../../utils/pb"))
sys.path.insert(0, pb_root)

from fraud_detection import fraud_detection_pb2 as fd_pb2
from fraud_detection import fraud_detection_pb2_grpc as fd_grpc
from transaction_verification import transaction_verification_pb2 as tv_pb2
from transaction_verification import transaction_verification_pb2_grpc as tv_grpc

# Flask app setup 
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


def call_fraud_detection(order_dict):
    """
    Calls fraud_detection gRPC service and returns (fraud_detected: bool, reason: str)
    """
    with grpc.insecure_channel("fraud_detection:50051") as channel:
        stub = fd_grpc.FraudDetectionServiceStub(channel)
        req = fd_pb2.OrderRequest(order_json=json.dumps(order_dict))
        resp = stub.CheckFraud(req, timeout=3)
        return resp.fraud_detected, resp.reason


def call_transaction_verification(order_dict):
    """
    Calls transaction_verification gRPC service and returns (is_valid: bool, reason: str)
    """
    with grpc.insecure_channel("transaction_verification:50052") as channel:
        stub = tv_grpc.TransactionVerificationServiceStub(channel)
        req = tv_pb2.TransactionRequest(order_json=json.dumps(order_dict))
        resp = stub.VerifyTransaction(req, timeout=3)
        return resp.is_valid, resp.reason


@app.route("/", methods=["GET"])
def index():
    # simple health check endpoint
    return "Orchestrator is running", 200


@app.route("/checkout", methods=["POST"])
def checkout():
    print("CONTENT-TYPE:", request.content_type)
    print("RAW DATA:", request.data[:500])
    # Parse JSON safely
    request_data = request.get_json(silent=True)
    if request_data is None and request.data:
        try:
            request_data = json.loads(request.data.decode("utf-8"))
        except Exception:
            request_data = None

    print("FULL REQUEST:", request_data)
    if request_data is None:
        return jsonify({"error": {"message": "Invalid or missing JSON body"}}), 400

    items = request_data.get("items")
    if not isinstance(items, list) or len(items) == 0:
        return jsonify({"error": {"message": "items must be a non-empty list"}}), 400

    print("Request items:", items)

    # Call fraud detection
    fraud_detected, fraud_reason = call_fraud_detection(request_data)
    print("Fraud result:", fraud_detected, fraud_reason)

    # Call transaction verification
    transaction_valid, transaction_reason = call_transaction_verification(request_data)
    print("Transaction result:", transaction_valid, transaction_reason)

    # Consolidate results: reject if fraud detected OR transaction invalid
    approved = (not fraud_detected) and transaction_valid

    order_status_response = {
        "orderId": "12345",
        "status": "Order Approved" if approved else "Order Rejected",
        "suggestedBooks": [] if not approved else [
            {"bookId": "123", "title": "The Best Book", "author": "Author 1"},
            {"bookId": "456", "title": "The Second Best Book", "author": "Author 2"}
        ]
    }

    return jsonify(order_status_response), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0")

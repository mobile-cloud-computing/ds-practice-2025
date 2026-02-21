import os
import sys
import json
import grpc
import logging
import threading

from flask import Flask, request, jsonify
from flask_cors import CORS

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("orchestrator")

# Import gRPC generated stubs 
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
pb_root = os.path.abspath(os.path.join(FILE, "../../../utils/pb"))
sys.path.insert(0, pb_root)

from fraud_detection import fraud_detection_pb2 as fd_pb2
from fraud_detection import fraud_detection_pb2_grpc as fd_grpc
from transaction_verification import transaction_verification_pb2 as tv_pb2
from transaction_verification import transaction_verification_pb2_grpc as tv_grpc
from suggestions import suggestions_pb2 as sg_pb2
from suggestions import suggestions_pb2_grpc as sg_grpc

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


def call_suggestions(order_dict):
    """
    Calls suggestions gRPC service and returns list of book suggestions
    """
    with grpc.insecure_channel("suggestions:50053") as channel:
        stub = sg_grpc.SuggestionsServiceStub(channel)
        req = sg_pb2.SuggestionsRequest(order_json=json.dumps(order_dict))
        resp = stub.GetSuggestions(req, timeout=3)
        return [
            {"bookId": book.book_id, "title": book.title, "author": book.author}
            for book in resp.books
        ]


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

    # Prepare shared storage for thread results
    results = {}
    
    # Define worker functions that store results in the shared dict
    def worker_fraud_detection():
        log.info("Thread: Starting fraud detection")
        try:
            fraud_detected, fraud_reason = call_fraud_detection(request_data)
            results['fraud'] = {'detected': fraud_detected, 'reason': fraud_reason}
            log.info(f"Thread: Fraud detection completed - detected={fraud_detected}")
        except Exception as e:
            log.error(f"Thread: Fraud detection failed - {e}")
            results['fraud'] = {'detected': True, 'reason': 'Service error'}
    
    def worker_transaction_verification():
        log.info("Thread: Starting transaction verification")
        try:
            is_valid, reason = call_transaction_verification(request_data)
            results['transaction'] = {'valid': is_valid, 'reason': reason}
            log.info(f"Thread: Transaction verification completed - valid={is_valid}")
        except Exception as e:
            log.error(f"Thread: Transaction verification failed - {e}")
            results['transaction'] = {'valid': False, 'reason': 'Service error'}
    
    def worker_suggestions():
        log.info("Thread: Starting suggestions")
        try:
            books = call_suggestions(request_data)
            results['suggestions'] = {'books': books}
            log.info(f"Thread: Suggestions completed - {len(books)} books")
        except Exception as e:
            log.error(f"Thread: Suggestions failed - {e}")
            results['suggestions'] = {'books': []}
    
    # Create worker threads
    thread_fraud = threading.Thread(target=worker_fraud_detection, name="FraudThread")
    thread_transaction = threading.Thread(target=worker_transaction_verification, name="TransactionThread")
    thread_suggestions = threading.Thread(target=worker_suggestions, name="SuggestionsThread")
    
    log.info("Starting all worker threads")
    thread_fraud.start()
    thread_transaction.start()
    thread_suggestions.start()
    
    thread_fraud.join()
    thread_transaction.join()
    thread_suggestions.join()
    log.info("All threads completed")
    
    # Extract results from shared dict
    fraud_detected = results.get('fraud', {}).get('detected', True)
    fraud_reason = results.get('fraud', {}).get('reason', 'Unknown')
    transaction_valid = results.get('transaction', {}).get('valid', False)
    transaction_reason = results.get('transaction', {}).get('reason', 'Unknown')
    suggested_books = results.get('suggestions', {}).get('books', [])
    
    print("Fraud result:", fraud_detected, fraud_reason)
    print("Transaction result:", transaction_valid, transaction_reason)
    print("Suggestions result:", len(suggested_books), "books")

    # Consolidate results: reject if fraud detected OR transaction invalid
    approved = (not fraud_detected) and transaction_valid
    if not approved:
        suggested_books = []

    order_status_response = {
        "orderId": "12345",
        "status": "Order Approved" if approved else "Order Rejected",
        "suggestedBooks": suggested_books
    }

    return jsonify(order_status_response), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0")

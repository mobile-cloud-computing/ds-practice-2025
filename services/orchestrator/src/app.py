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
pb_root = os.path.abspath(os.path.join(FILE, "../../../../utils/pb"))
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


def mask_sensitive_data(data):
    """
    Mask sensitive data
    """
    if not isinstance(data, dict):
        return data
    
    masked = data.copy()

    if 'creditCard' in masked and isinstance(masked['creditCard'], dict):
        cc = masked['creditCard'].copy()
        if 'number' in cc and cc['number']:
            cc['number'] = '****' + str(cc['number'])[-4:] if len(str(cc['number'])) >= 4 else '****'
        if 'cvv' in cc:
            cc['cvv'] = '***'
        masked['creditCard'] = cc
    
    return masked


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
    log.info(f"Received checkout request - Content-Type: {request.content_type}")
    
    # Parse JSON safely
    request_data = request.get_json(silent=True)
    if request_data is None and request.data:
        try:
            request_data = json.loads(request.data.decode("utf-8"))
        except Exception as e:
            log.error(f"Failed to parse JSON: {e}")
            request_data = None

    log.info(f"Parsed request (masked): {mask_sensitive_data(request_data)}")
    
    if request_data is None:
        return jsonify({"error": {"code": "INVALID_JSON", "message": "Invalid or missing JSON body"}}), 400

    # Validate required fields according to API contract
    items = request_data.get("items")
    if not isinstance(items, list) or len(items) == 0:
        return jsonify({"error": {"code": "INVALID_ITEMS", "message": "items must be a non-empty list"}}), 400
    
    # Validate user information
    user = request_data.get("user")
    if not user or not isinstance(user, dict):
        return jsonify({"error": {"code": "MISSING_USER", "message": "user information is required"}}), 400
    
    # Validate credit card information
    credit_card = request_data.get("creditCard")
    if not credit_card or not isinstance(credit_card, dict):
        return jsonify({"error": {"code": "MISSING_CREDIT_CARD", "message": "creditCard information is required"}}), 400

    log.info(f"Request validation passed - {len(items)} items")

    # Prepare shared storage for thread results
    results = {}
    
    # Define worker functions that store results in the shared dict
    def worker_fraud_detection():
        log.info("Thread: Starting fraud detection")
        try:
            fraud_detected, fraud_reason = call_fraud_detection(request_data)
            results['fraud'] = {'detected': fraud_detected, 'reason': fraud_reason, 'error': None}
            log.info(f"Thread: Fraud detection completed - detected={fraud_detected}")
        except grpc.RpcError as e:
            log.error(f"Thread: Fraud detection gRPC error - {e.code()}: {e.details()}")
            results['fraud'] = {'detected': True, 'reason': 'Fraud detection service unavailable', 'error': 'SERVICE_UNAVAILABLE'}
        except Exception as e:
            log.error(f"Thread: Fraud detection unexpected error - {e}")
            results['fraud'] = {'detected': True, 'reason': 'Fraud detection service error', 'error': 'SERVICE_ERROR'}
    
    def worker_transaction_verification():
        log.info("Thread: Starting transaction verification")
        try:
            is_valid, reason = call_transaction_verification(request_data)
            results['transaction'] = {'valid': is_valid, 'reason': reason, 'error': None}
            log.info(f"Thread: Transaction verification completed - valid={is_valid}")
        except grpc.RpcError as e:
            log.error(f"Thread: Transaction verification gRPC error - {e.code()}: {e.details()}")
            results['transaction'] = {'valid': False, 'reason': 'Transaction verification service unavailable', 'error': 'SERVICE_UNAVAILABLE'}
        except Exception as e:
            log.error(f"Thread: Transaction verification unexpected error - {e}")
            results['transaction'] = {'valid': False, 'reason': 'Transaction verification service error', 'error': 'SERVICE_ERROR'}
    
    def worker_suggestions():
        log.info("Thread: Starting suggestions")
        try:
            books = call_suggestions(request_data)
            results['suggestions'] = {'books': books, 'error': None}
            log.info(f"Thread: Suggestions completed - {len(books)} books")
        except grpc.RpcError as e:
            log.error(f"Thread: Suggestions gRPC error - {e.code()}: {e.details()}")
            results['suggestions'] = {'books': [], 'error': 'SERVICE_UNAVAILABLE'}
        except Exception as e:
            log.error(f"Thread: Suggestions unexpected error - {e}")
            results['suggestions'] = {'books': [], 'error': 'SERVICE_ERROR'}
    
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
    fraud_data = results.get('fraud', {})
    fraud_detected = fraud_data.get('detected', True)
    fraud_reason = fraud_data.get('reason', 'Unknown')
    fraud_error = fraud_data.get('error')
    
    transaction_data = results.get('transaction', {})
    transaction_valid = transaction_data.get('valid', False)
    transaction_reason = transaction_data.get('reason', 'Unknown')
    transaction_error = transaction_data.get('error')
    
    suggestions_data = results.get('suggestions', {})
    suggested_books = suggestions_data.get('books', [])
    suggestions_error = suggestions_data.get('error')
    
    log.info(f"Results - Fraud: {fraud_detected} ({fraud_reason}), Transaction: {transaction_valid} ({transaction_reason}), Suggestions: {len(suggested_books)} books")

    # Check if any critical service failed
    if fraud_error or transaction_error:
        error_details = []
        if fraud_error:
            error_details.append("fraud_detection")
        if transaction_error:
            error_details.append("transaction_verification")
        
        log.error(f"Critical services unavailable: {', '.join(error_details)}")
        return jsonify({
            "error": {
                "code": "SERVICE_UNAVAILABLE",
                "message": f"One or more backend services are unavailable: {', '.join(error_details)}"
            }
        }), 503

    # Consolidate results: reject if fraud detected OR transaction invalid
    approved = (not fraud_detected) and transaction_valid
    if not approved:
        suggested_books = []
        log.info(f"Order rejected - Fraud: {fraud_detected}, Valid: {transaction_valid}")
    else:
        log.info("Order approved")

    order_status_response = {
        "orderId": "12345",
        "status": "Order Approved" if approved else "Order Rejected",
        "suggestedBooks": suggested_books
    }

    return jsonify(order_status_response), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0")

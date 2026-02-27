import sys
import os

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
transaction_verification_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/transaction_verification'))
sys.path.insert(0, transaction_verification_grpc_path)
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc

fraud_detection_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/fraud_detection'))
sys.path.insert(0, fraud_detection_grpc_path)
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc

import grpc
import uuid
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import Flask.
# Flask is a web framework for Python.
# It allows you to build a web application quickly.
# For more information, see https://flask.palletsprojects.com/en/latest/
from flask import Flask, request
from flask_cors import CORS
import logging


# Create a simple Flask app.
app = Flask(__name__)
# Enable CORS for the app.
CORS(app, resources={r'/*': {'origins': '*'}})

logging.basicConfig(
    level=logging.INFO,
    format="===LOG=== %(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("orchestrator")


# Create reusable gRPC channels/stubs once for concurrent request handling.
RPC_TIMEOUT_SECONDS = float(os.getenv("GRPC_TIMEOUT_SECONDS", "3.0"))
TRANSACTION_VERIFICATION_ADDR = os.getenv("TRANSACTION_VERIFICATION_ADDR", "transaction_verification:50052")
FRAUD_DETECTION_ADDR = os.getenv("FRAUD_DETECTION_ADDR", "fraud_detection:50051")

transaction_verification_channel = grpc.insecure_channel(TRANSACTION_VERIFICATION_ADDR)
transaction_verification_stub = transaction_verification_grpc.TransactionVerificationServiceStub(
    transaction_verification_channel
)

fraud_detection_channel = grpc.insecure_channel(FRAUD_DETECTION_ADDR)
fraud_detection_stub = fraud_detection_grpc.FraudDetectionServiceStub(fraud_detection_channel)

fraud_hello_stub = fraud_detection_grpc.HelloServiceStub(fraud_detection_channel)


def greet(name="you"):
    # Reuse the existing fraud_detection_channel via a module-level stub.
    response = fraud_hello_stub.SayHello(
        fraud_detection.HelloRequest(name=name),
        timeout=RPC_TIMEOUT_SECONDS,
    )
    return response.greeting

def _mask_card(card_number):
    digits = "".join(ch for ch in str(card_number or "") if ch.isdigit())
    if len(digits) < 4:
        return "****"
    return f"****{digits[-4:]}"


def _email_domain(email):
    email = str(email or "").strip()
    if "@" not in email:
        return "unknown"
    return email.split("@", 1)[1]


def _validate_items_payload(items):
    if not isinstance(items, list):
        return False, "items must be a list"
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            return False, f"items[{index}] must be an object"
    return True, None


def verify_transaction(checkout_data, correlation_id):
    user = checkout_data.get("user", {})
    credit_card = checkout_data.get("creditCard", {})
    billing_address = checkout_data.get("billingAddress", {})
    items = checkout_data.get("items", [])

    request_message = transaction_verification.TransactionVerificationRequest(
        transaction_id=checkout_data.get("orderId", ""),
        purchaser_name=user.get("name", ""),
        purchaser_email=user.get("contact", ""),
        credit_card_number=credit_card.get("number", ""),
        credit_card_expiration=credit_card.get("expirationDate", ""),
        credit_card_cvv=credit_card.get("cvv", ""),
        billing_street=billing_address.get("street", ""),
        billing_city=billing_address.get("city", ""),
        billing_state=billing_address.get("state", ""),
        billing_zip=billing_address.get("zip", ""),
        billing_country=billing_address.get("country", ""),
        items=[
            transaction_verification.Item(
                name=item.get("name", ""),
                quantity=item.get("quantity", 0),
            )
            for item in items
        ],
        terms_accepted=checkout_data.get("termsAccepted", False),
    )

    rpc_start = time.perf_counter()
    try:
        response = transaction_verification_stub.VerifyTransaction(
            request_message,
            timeout=RPC_TIMEOUT_SECONDS,
        )
        latency_ms = (time.perf_counter() - rpc_start) * 1000
        logger.info(
            "cid=%s event=rpc_completed service=transaction_verification rpc=VerifyTransaction ok=true latency_ms=%.2f is_valid=%s reason_count=%s",
            correlation_id,
            latency_ms,
            response.is_valid,
            len(response.reasons),
        )
        return True, response, None, latency_ms
    except grpc.RpcError as error:
        latency_ms = (time.perf_counter() - rpc_start) * 1000
        logger.error(
            "cid=%s service=transaction_verification rpc=VerifyTransaction ok=false latency_ms=%.2f code=%s details=%s",
            correlation_id,
            latency_ms,
            error.code(),
            error.details(),
        )
        return False, None, "Transaction verification service unavailable", latency_ms


def detect_fraud(checkout_data, correlation_id):
    user = checkout_data.get("user", {})
    credit_card = checkout_data.get("creditCard", {})
    billing_address = checkout_data.get("billingAddress", {})

    request_message = fraud_detection.FraudDetectionRequest(
        transaction_id=checkout_data.get("orderId", ""),
        purchaser_name=user.get("name", ""),
        purchaser_email=user.get("contact", ""),
        credit_card_number=credit_card.get("number", ""),
        billing_street=billing_address.get("street", ""),
        billing_city=billing_address.get("city", ""),
        billing_state=billing_address.get("state", ""),
        billing_zip=billing_address.get("zip", ""),
        billing_country=billing_address.get("country", ""),
    )

    rpc_start = time.perf_counter()
    try:
        response = fraud_detection_stub.DetectFraud(
            request_message,
            timeout=RPC_TIMEOUT_SECONDS,
        )
        latency_ms = (time.perf_counter() - rpc_start) * 1000
        logger.info(
            "cid=%s event=rpc_completed service=fraud_detection rpc=DetectFraud ok=true latency_ms=%.2f is_fraud=%s",
            correlation_id,
            latency_ms,
            response.is_fraud,
        )
        return True, response, None, latency_ms
    except grpc.RpcError as error:
        latency_ms = (time.perf_counter() - rpc_start) * 1000
        logger.error(
            "cid=%s service=fraud_detection rpc=DetectFraud ok=false latency_ms=%.2f code=%s details=%s",
            correlation_id,
            latency_ms,
            error.code(),
            error.details(),
        )
        return False, None, "Fraud detection service unavailable", latency_ms
    

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
    total_start = time.perf_counter()

    request_data = request.get_json(silent=True)
    if not isinstance(request_data, dict):
        logger.warning("cid=none event=checkout_invalid_json")
        return {"error": {"message": "Invalid JSON payload"}}, 400

    items = request_data.get("items", [])
    items_ok, items_error = _validate_items_payload(items)
    if not items_ok:
        logger.warning("cid=none event=checkout_invalid_items reason=%s", items_error)
        return {"error": {"message": items_error}}, 400

    correlation_id = str(request_data.get("orderId") or uuid.uuid4())
    request_data["orderId"] = correlation_id

    user = request_data.get("user", {})
    credit_card = request_data.get("creditCard", {})
    billing_address = request_data.get("billingAddress", {})

    logger.info(
        "cid=%s event=checkout_received item_count=%s email_domain=%s card=%s billing_country=%s",
        correlation_id,
        len(items),
        _email_domain(user.get("contact", "")),
        _mask_card(credit_card.get("number", "")),
        billing_address.get("country", ""),
    )

    logger.info(
        "cid=%s event=dispatch_parallel_rpcs services=transaction_verification,fraud_detection",
        correlation_id,
    )

    results = {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_to_service = {
            executor.submit(verify_transaction, request_data, correlation_id): "transaction_verification",
            executor.submit(detect_fraud, request_data, correlation_id): "fraud_detection",
        }

        for future in as_completed(future_to_service):
            service_name = future_to_service[future]
            try:
                results[service_name] = future.result()
            except Exception:
                logger.exception("cid=%s service=%s unexpected_error=true", correlation_id, service_name)
                if service_name == "transaction_verification":
                    results[service_name] = (False, None, "Transaction verification service unavailable", None)
                else:
                    results[service_name] = (False, None, "Fraud detection service unavailable", None)

    verification_ok, verification_response, verification_error, _ = results.get(
        "transaction_verification",
        (False, None, "Transaction verification service unavailable", None),
    )
    fraud_ok, fraud_response, fraud_error, _ = results.get(
        "fraud_detection",
        (False, None, "Fraud detection service unavailable", None),
    )

    reject_reasons = []

    if not verification_ok:
        reject_reasons.append(verification_error)
    elif not verification_response.is_valid:
        reject_reasons.extend(list(verification_response.reasons))

    if not fraud_ok:
        reject_reasons.append(fraud_error)
    elif fraud_response.is_fraud:
        if getattr(fraud_response, "reasons", None) and len(fraud_response.reasons) > 0:
            reject_reasons.extend(list(fraud_response.reasons))
        else:
            reject_reasons.append("Fraud indicators detected")

    if reject_reasons:
        total_latency_ms = (time.perf_counter() - total_start) * 1000
        logger.warning(
            "cid=%s event=checkout_completed decision=rejected reason_count=%s total_latency_ms=%.2f reasons=%s",
            correlation_id,
            len(reject_reasons),
            total_latency_ms,
            reject_reasons,
        )
        return {
            "status": "Order Rejected",
            "reasons": reject_reasons,
            "suggestedBooks": [],
        }

    # Dummy
    order_status_response = {
        "status": "Order Approved",
        "suggestedBooks": [
            {"bookId": "123", "title": "The Best Book", "author": "Author 1"},
            {"bookId": "456", "title": "The Second Best Book", "author": "Author 2"}
        ]
    }

    total_latency_ms = (time.perf_counter() - total_start) * 1000
    logger.info(
        "cid=%s event=checkout_completed decision=approved total_latency_ms=%.2f",
        correlation_id,
        total_latency_ms,
    )
    return order_status_response


if __name__ == '__main__':
    # Run the app in debug mode to enable hot reloading.
    # This is useful for development.
    # The default port is 5000.
    app.run(host='0.0.0.0')



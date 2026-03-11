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
from concurrent.futures import ThreadPoolExecutor, as_completed
from uuid import uuid4

project_root = os.path.abspath(os.path.join(FILE, "../../.."))
sys.path.insert(0, project_root)
from utils.vector_clock import (
    EVENT_TRACE_METADATA_KEY,
    ORDER_ID_METADATA_KEY,
    SUGGESTED_BOOKS_METADATA_KEY,
    VECTOR_CLOCK_METADATA_KEY,
    deserialize_clock,
    deserialize_trace,
    merge_clocks,
    metadata_to_dict,
    new_clock,
    record_event,
    serialize_clock,
    tick,
)

logging.basicConfig(level=logging.INFO)


def _metadata(order_id, clock):
    return (
        (ORDER_ID_METADATA_KEY, order_id),
        (VECTOR_CLOCK_METADATA_KEY, serialize_clock(clock)),
    )


def _merge_service_result(event_trace, vector_clock, service_clock, service_trace):
    event_trace.extend(service_trace)
    return merge_clocks(vector_clock, service_clock)


def _deny_response(order_id, reason, vector_clock, event_trace):
    return {
        "orderId": order_id,
        "status": "Order Denied",
        "reason": reason,
        "suggestedBooks": [],
        "vectorClock": vector_clock,
        "eventTrace": event_trace,
    }


def initialize_fraud_detection(card_number, order_amount, order_id, clock):
    try:
        with grpc.insecure_channel("fraud_detection:50051") as channel:
            stub = fd_grpc.FraudDetectionServiceStub(channel)
            response, call = stub.InitializeFraudOrder.with_call(
                fd_pb2.FraudRequest(card_number=card_number, order_amount=order_amount),
                metadata=_metadata(order_id, clock),
            )
        metadata = metadata_to_dict(call.trailing_metadata())
        return (
            response.is_fraud,
            "Fraud order cached",
            deserialize_clock(metadata.get(VECTOR_CLOCK_METADATA_KEY)),
            deserialize_trace(metadata.get(EVENT_TRACE_METADATA_KEY)),
        )
    except grpc.RpcError:
        raise
    except Exception as e:
        logging.error(f"gRPC Call Failed: {e}")
        return True, "Fraud detection service error", clock, []


def initialize_suggestions(items, order_id, clock):
    try:
        with grpc.insecure_channel("suggestions:50053") as channel:
            stub = sg_grpc.SuggestionsServiceStub(channel)
            book_items = [
                sg_pb2.BookItem(
                    name=item.get("name", ""), quantity=item.get("quantity", 0)
                )
                for item in items
            ]
            response, call = stub.InitializeSuggestionsOrder.with_call(
                sg_pb2.SuggestionsRequest(items=book_items),
                metadata=_metadata(order_id, clock),
            )
        metadata = metadata_to_dict(call.trailing_metadata())
        return (
            [
                {"bookId": book.bookId, "title": book.title, "author": book.author}
                for book in response.books
            ],
            "Suggestions order cached",
            deserialize_clock(metadata.get(VECTOR_CLOCK_METADATA_KEY)),
            deserialize_trace(metadata.get(EVENT_TRACE_METADATA_KEY)),
        )
    except grpc.RpcError:
        raise
    except Exception as e:
        logging.error(f"gRPC Call Failed: {e}")
        return [], "Suggestions service error", clock, []


def _verification_request(payload):
    user = payload.get("user", {}) or {}
    cc = payload.get("creditCard", {}) or {}
    billing = payload.get("billingAddress", {}) or {}

    return tv_pb2.VerificationRequest(
        name=user.get("name", ""),
        email=user.get("contact", ""),
        card_number=cc.get("number", ""),
        expiration_date=cc.get("expirationDate", "") or cc.get("expiry", ""),
        cvv=cc.get("cvv", ""),
        billing_address=tv_pb2.BillingAddress(
            street=billing.get("street", ""),
            city=billing.get("city", ""),
            state=billing.get("state", ""),
            zip=billing.get("zip", ""),
            country=billing.get("country", ""),
        ),
    )


def initialize_transaction_verification(payload: dict, order_id, clock):
    try:
        logging.info("Initializing transaction verification")
        req = _verification_request(payload)
        with grpc.insecure_channel("transaction_verification:50052") as channel:
            stub = tv_grpc.TransactionVerificationServiceStub(channel)
            res, call = stub.InitializeVerificationOrder.with_call(
                req, metadata=_metadata(order_id, clock)
            )
        metadata = metadata_to_dict(call.trailing_metadata())
        return (
            bool(res.is_valid),
            getattr(res, "message", ""),
            json.loads(metadata.get(SUGGESTED_BOOKS_METADATA_KEY, "[]")),
            deserialize_clock(metadata.get(VECTOR_CLOCK_METADATA_KEY)),
            deserialize_trace(metadata.get(EVENT_TRACE_METADATA_KEY)),
        )
    except grpc.RpcError:
        raise
    except Exception as e:
        logging.error(f"Transaction Verification gRPC Call Failed: {e}")
        return False, "Transaction verification service error", clock, []


def run_order_execution_flow(
    order_id,
    init_futures,
    initial_clock,
    initial_trace,
):
    vector_clock = initial_clock
    event_trace = list(initial_trace)
    future_to_service = {future: name for name, future in init_futures.items()}
    final_result = None

    for future in as_completed(future_to_service):
        service_name = future_to_service[future]
        try:
            result = future.result()
        except grpc.RpcError as exc:
            for pending in future_to_service:
                if pending is not future:
                    pending.cancel()
            vector_clock = tick(vector_clock, "orchestrator")
            record_event(
                event_trace,
                vector_clock,
                "orchestrator",
                f"{service_name}_initialization_failed",
            )
            return _deny_response(
                order_id,
                exc.details() or f"{service_name} initialization failed",
                vector_clock,
                event_trace,
            )

        if service_name == "transaction_verification":
            is_valid, message, suggested_books, service_clock, service_trace = result
            final_result = (is_valid, message, suggested_books)
        else:
            _, _, service_clock, service_trace = result

        vector_clock = _merge_service_result(
            event_trace, vector_clock, service_clock, service_trace
        )
        vector_clock = tick(vector_clock, "orchestrator")
        record_event(
            event_trace,
            vector_clock,
            "orchestrator",
            (
                "transaction_verification_result_received"
                if service_name == "transaction_verification"
                else f"{service_name}_initialized"
            ),
        )

    if final_result is None:
        vector_clock = tick(vector_clock, "orchestrator")
        record_event(
            event_trace,
            vector_clock,
            "orchestrator",
            "transaction_verification_result_missing",
        )
        return _deny_response(
            order_id,
            "Transaction verification result missing",
            vector_clock,
            event_trace,
        )

    is_valid, message, suggested_books = final_result

    if not is_valid:
        vector_clock = tick(vector_clock, "orchestrator")
        record_event(
            event_trace, vector_clock, "orchestrator", "checkout_denied_invalid"
        )
        return _deny_response(
            order_id, message or "Invalid transaction data", vector_clock, event_trace
        )

    response = {
        "orderId": order_id,
        "status": "Order Approved",
        "reason": "",
        "suggestedBooks": suggested_books,
    }
    vector_clock = tick(vector_clock, "orchestrator")
    record_event(event_trace, vector_clock, "orchestrator", "checkout_response_ready")
    response["vectorClock"] = vector_clock
    response["eventTrace"] = event_trace
    return response


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
    """Process a checkout request through a partially ordered pipeline with vector clocks."""
    # Get request object data to json
    request_data = json.loads(request.data)
    logging.info(
        f"Checkout request received with {len(request_data.get('items', []))} items"
    )

    order_id = str(uuid4())
    vector_clock = new_clock()
    event_trace = []

    vector_clock = tick(vector_clock, "orchestrator")
    record_event(event_trace, vector_clock, "orchestrator", "checkout_request_received")
    vector_clock = tick(vector_clock, "orchestrator")
    record_event(event_trace, vector_clock, "orchestrator", "order_id_created")

    items = request_data.get("items", [])
    card_number = request_data.get("creditCard", {}).get("number", "")
    order_amount = str(sum(item.get("quantity", 0) for item in items))

    executor = ThreadPoolExecutor(max_workers=4)
    try:
        suggestions_init_clock = tick(vector_clock, "orchestrator")
        record_event(
            event_trace,
            suggestions_init_clock,
            "orchestrator",
            "dispatch_suggestions_init",
        )
        future_suggestions_init = executor.submit(
            initialize_suggestions, items, order_id, suggestions_init_clock
        )

        fraud_init_clock = tick(suggestions_init_clock, "orchestrator")
        record_event(
            event_trace,
            fraud_init_clock,
            "orchestrator",
            "dispatch_fraud_detection_init",
        )
        future_fraud_init = executor.submit(
            initialize_fraud_detection,
            card_number,
            order_amount,
            order_id,
            fraud_init_clock,
        )
        verification_init_clock = tick(fraud_init_clock, "orchestrator")
        record_event(
            event_trace,
            verification_init_clock,
            "orchestrator",
            "dispatch_transaction_verification_init",
        )
        future_verification_init = executor.submit(
            initialize_transaction_verification,
            request_data,
            order_id,
            verification_init_clock,
        )
        future_pipeline = executor.submit(
            run_order_execution_flow,
            order_id,
            {
                "suggestions": future_suggestions_init,
                "fraud_detection": future_fraud_init,
                "transaction_verification": future_verification_init,
            },
            verification_init_clock,
            event_trace,
        )

        return future_pipeline.result()
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


if __name__ == "__main__":
    # Run the app in debug mode to enable hot reloading.
    # This is useful for development.
    # The default port is 5000.
    app.run(host="0.0.0.0")

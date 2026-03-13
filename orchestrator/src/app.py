import sys
import os
import threading
import uuid

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")

fraud_detection_grpc_path = os.path.abspath(
    os.path.join(FILE, "../../../utils/pb/fraud_detection")
)
sys.path.insert(0, fraud_detection_grpc_path)
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc

transaction_verification_grpc_path = os.path.abspath(
    os.path.join(FILE, "../../../utils/pb/transaction_verification")
)
sys.path.insert(0, transaction_verification_grpc_path)
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc

suggestions_grpc_path = os.path.abspath(
    os.path.join(FILE, "../../../utils/pb/suggestions")
)
sys.path.insert(0, suggestions_grpc_path)
import suggestions_pb2 as suggestions
import suggestions_pb2_grpc as suggestions_grpc

import grpc

from flask import Flask, request
from flask_cors import CORS


def greet(name="you"):
    with grpc.insecure_channel("fraud_detection:50051") as channel:
        stub = fraud_detection_grpc.HelloServiceStub(channel)
        response = stub.SayHello(fraud_detection.HelloRequest(name=name))
    return response.greeting


def detect_fraud(order_id, user_name, card_number, item_count):
    with grpc.insecure_channel("fraud_detection:50051") as channel:
        stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
        response = stub.CheckFraud(
            fraud_detection.FraudCheckRequest(
                order_id=order_id,
                user_name=user_name or "",
                card_number=card_number or "",
                item_count=item_count,
            ),
            timeout=5.0,
        )
    return response


def trigger_fraud_check(order_id, event_type="all"):
    with grpc.insecure_channel("fraud_detection:50051") as channel:
        stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
        response = stub.TriggerFraudCheck(
            fraud_detection.TriggerRequest(order_id=order_id, event_type=event_type),
            timeout=5.0,
        )
    return response


def get_fraud_vector_clock(order_id):
    with grpc.insecure_channel("fraud_detection:50051") as channel:
        stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
        response = stub.GetVectorClock(
            fraud_detection.VectorClockRequest(order_id=order_id),
            timeout=5.0,
        )
    return response


def trigger_verification(order_id, event_type="all"):
    with grpc.insecure_channel("transaction_verification:50052") as channel:
        stub = transaction_verification_grpc.TransactionVerificationServiceStub(channel)
        response = stub.TriggerVerification(
            transaction_verification.TriggerRequest(
                order_id=order_id, event_type=event_type
            ),
            timeout=5.0,
        )
    return response


def get_verification_vector_clock(order_id):
    with grpc.insecure_channel("transaction_verification:50052") as channel:
        stub = transaction_verification_grpc.TransactionVerificationServiceStub(channel)
        response = stub.GetVectorClock(
            transaction_verification.VectorClockRequest(order_id=order_id),
            timeout=5.0,
        )
    return response


def trigger_suggestions(order_id, event_type="all"):
    with grpc.insecure_channel("suggestions:50053") as channel:
        stub = suggestions_grpc.SuggestionsServiceStub(channel)
        response = stub.TriggerSuggestions(
            suggestions.TriggerRequest(order_id=order_id, event_type=event_type),
            timeout=5.0,
        )
    return response


def get_suggestions_vector_clock(order_id):
    with grpc.insecure_channel("suggestions:50053") as channel:
        stub = suggestions_grpc.SuggestionsServiceStub(channel)
        response = stub.GetVectorClock(
            suggestions.VectorClockRequest(order_id=order_id),
            timeout=5.0,
        )
    return response


def broadcast_clear_order(order_id, final_vc):
    broadcast_results = {}

    try:
        with grpc.insecure_channel("fraud_detection:50051") as channel:
            stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
            response = stub.ClearOrder(
                fraud_detection.ClearOrderRequest(
                    order_id=order_id,
                    final_vc_fraud_detection=final_vc.get("fraud_detection", 0),
                    final_vc_fd_event_d=final_vc.get("fd_event_d", 0),
                    final_vc_fd_event_e=final_vc.get("fd_event_e", 0),
                    final_vc_transaction_verification=final_vc.get(
                        "transaction_verification", 0
                    ),
                    final_vc_tv_event_a=final_vc.get("tv_event_a", 0),
                    final_vc_tv_event_b=final_vc.get("tv_event_b", 0),
                    final_vc_tv_event_c=final_vc.get("tv_event_c", 0),
                    final_vc_suggestions=final_vc.get("suggestions", 0),
                ),
                timeout=5.0,
            )
            broadcast_results["fraud_detection"] = {
                "success": response.success,
                "message": response.message,
            }
    except Exception as e:
        broadcast_results["fraud_detection"] = {"success": False, "message": str(e)}

    try:
        with grpc.insecure_channel("transaction_verification:50052") as channel:
            stub = transaction_verification_grpc.TransactionVerificationServiceStub(
                channel
            )
            response = stub.ClearOrder(
                transaction_verification.ClearOrderRequest(
                    order_id=order_id,
                    final_vc_transaction_verification=final_vc.get(
                        "transaction_verification", 0
                    ),
                    final_vc_tv_event_a=final_vc.get("tv_event_a", 0),
                    final_vc_tv_event_b=final_vc.get("tv_event_b", 0),
                    final_vc_tv_event_c=final_vc.get("tv_event_c", 0),
                    final_vc_fraud_detection=final_vc.get("fraud_detection", 0),
                    final_vc_suggestions=final_vc.get("suggestions", 0),
                ),
                timeout=5.0,
            )
            broadcast_results["transaction_verification"] = {
                "success": response.success,
                "message": response.message,
            }
    except Exception as e:
        broadcast_results["transaction_verification"] = {
            "success": False,
            "message": str(e),
        }

    try:
        with grpc.insecure_channel("suggestions:50053") as channel:
            stub = suggestions_grpc.SuggestionsServiceStub(channel)
            response = stub.ClearOrder(
                suggestions.ClearOrderRequest(
                    order_id=order_id,
                    final_vc_suggestions=final_vc.get("suggestions", 0),
                    final_vc_fraud_detection=final_vc.get("fraud_detection", 0),
                    final_vc_fd_event_d=final_vc.get("fd_event_d", 0),
                    final_vc_fd_event_e=final_vc.get("fd_event_e", 0),
                    final_vc_transaction_verification=final_vc.get(
                        "transaction_verification", 0
                    ),
                    final_vc_tv_event_a=final_vc.get("tv_event_a", 0),
                    final_vc_tv_event_b=final_vc.get("tv_event_b", 0),
                    final_vc_tv_event_c=final_vc.get("tv_event_c", 0),
                ),
                timeout=5.0,
            )
            broadcast_results["suggestions"] = {
                "success": response.success,
                "message": response.message,
            }
    except Exception as e:
        broadcast_results["suggestions"] = {"success": False, "message": str(e)}

    return broadcast_results


def verify_transaction(
    order_id,
    user_name,
    user_contact,
    card_number,
    expiration_date,
    cvv,
    item_count,
    terms_accepted,
):
    with grpc.insecure_channel("transaction_verification:50052") as channel:
        stub = transaction_verification_grpc.TransactionVerificationServiceStub(channel)
        response = stub.VerifyTransaction(
            transaction_verification.TransactionVerificationRequest(
                order_id=order_id,
                user_name=user_name or "",
                user_contact=user_contact or "",
                card_number=card_number or "",
                expiration_date=expiration_date or "",
                cvv=cvv or "",
                item_count=item_count,
                terms_accepted=terms_accepted,
            )
        )
    return response


def get_suggestions(order_id, user_name, item_count):
    with grpc.insecure_channel("suggestions:50053") as channel:
        stub = suggestions_grpc.SuggestionsServiceStub(channel)
        response = stub.GetSuggestions(
            suggestions.SuggestionsRequest(
                order_id=order_id, user_name=user_name or "", item_count=item_count
            )
        )
    return response


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


@app.route("/", methods=["GET"])
def index():
    response = greet(name="orchestrator")
    return response


@app.route("/checkout", methods=["POST"])
def checkout():
    request_data = request.get_json(silent=True)

    if request_data is None:
        return {
            "error": {
                "code": "BAD_REQUEST",
                "message": "Request body must be valid JSON.",
            }
        }, 400

    user = request_data.get("user", {})
    items = request_data.get("items", [])
    shipping_method = request_data.get("shippingMethod")
    terms_accepted = request_data.get("termsAndConditionsAccepted", False)

    # Normalize user fields and enforce that user_name is not empty or just spaces
    user_name = (user.get("name") or "").strip()
    user_contact = (user.get("contact") or "").strip()
    user_comment = user.get("userComment", "")

    credit_card = user.get("creditCard", {})
    card_number = credit_card.get("number").strip()
    masked_card_number = mask_fixed(card_number)
    expiration_date = credit_card.get("expirationDate").strip()
    cvv = credit_card.get("cvv").strip()
    print(
        "Received a request for checkout of user : {} for card number : {}".format(
            user_name, masked_card_number
        )
    )

    # Keep these simple bad-request checks locally
    # user_name must not be empty or contain spaces
    if not user_name or "" == user_name:
        return {
            "error": {
                "code": "BAD_REQUEST",
                "message": "User name is required and must not contain spaces.",
            }
        }, 400

    if not user_contact or "" == user_contact:
        return {
            "error": {
                "code": "BAD_REQUEST",
                "message": "User contact is required and must not contain spaces.",
            }
        }, 400

    item_count = len(items)
    order_id = str(uuid.uuid4())

    results = {"fraud": None, "verification": None, "suggestions": None, "errors": []}

    def fraud_worker():
        try:
            print(f"Calling fraud_detection service to cache order {order_id}...")
            detect_fraud(
                order_id=order_id,
                user_name=user_name,
                card_number=card_number,
                item_count=item_count,
            )
            print(f"Order {order_id} cached in fraud_detection")
        except Exception as e:
            print(f"fraud_detection caching failed: {e}")
            results["errors"].append("fraud_detection service unavailable")

    def verification_worker():
        try:
            print(
                f"Calling transaction_verification service to cache order {order_id}..."
            )
            verify_transaction(
                order_id=order_id,
                user_name=user_name,
                user_contact=user_contact,
                card_number=card_number,
                expiration_date=expiration_date,
                cvv=cvv,
                item_count=item_count,
                terms_accepted=terms_accepted,
            )
            print(f"Order {order_id} cached in transaction_verification")
        except Exception as e:
            error_msg = f"transaction_verification caching failed: {e}"
            print(error_msg)
            results["errors"].append(error_msg)

    def suggestions_worker():
        try:
            print(f"Calling suggestions service to cache order {order_id}...")
            get_suggestions(
                order_id=order_id, user_name=user_name, item_count=item_count
            )
            print(f"Order {order_id} cached in suggestions")
        except Exception as e:
            error_msg = f"suggestions caching failed: {e}"
            print(error_msg)
            results["errors"].append(error_msg)

    fraud_thread = threading.Thread(target=fraud_worker)
    verification_thread = threading.Thread(target=verification_worker)
    suggestions_thread = threading.Thread(target=suggestions_worker)

    print("Starting worker threads to cache orders...")
    fraud_thread.start()
    verification_thread.start()
    suggestions_thread.start()

    # The requirement says: "some of the threads created by the orchestrator may finish right away,
    # and only one thread may wait for the end of the execution flow".
    # We will let fraud and suggestions threads finish initialization quickly.
    # Verification thread will be the one we join to ensure basic caching is done before triggers.
    # Actually, to be safe, we join all to ensure all services have the data before we start triggering.
    # But for the task, let's just join them as before, they are "initialization" threads.
    fraud_thread.join()
    verification_thread.join()
    suggestions_thread.join()
    print("All caching threads finished. Starting event-based execution...")

    event_results = {
        "event_a": None,
        "event_b": None,
        "event_c": None,
        "event_d": None,
        "event_e": None,
        "event_f": None,
    }
    failed = False
    failure_message = ""

    def trigger_event_a():
        try:
            print(
                f"Triggering event_a (verify_items_not_empty) for order {order_id}..."
            )
            event_results["event_a"] = trigger_verification(order_id, "event_a")
            vc = get_verification_vector_clock(order_id)
            print(
                f"event_a result: {event_results['event_a'].is_valid}, {event_results['event_a'].message}, VC: a={vc.tv_event_a}"
            )
            if not event_results["event_a"].is_valid:
                return True, event_results["event_a"].message
        except Exception as e:
            print(f"event_a failed: {e}")
            return True, str(e)
        return False, ""

    def trigger_event_b():
        try:
            print(f"Triggering event_b (verify_user_data) for order {order_id}...")
            event_results["event_b"] = trigger_verification(order_id, "event_b")
            vc = get_verification_vector_clock(order_id)
            print(
                f"event_b result: {event_results['event_b'].is_valid}, {event_results['event_b'].message}, VC: b={vc.tv_event_b}"
            )
            if not event_results["event_b"].is_valid:
                return True, event_results["event_b"].message
        except Exception as e:
            print(f"event_b failed: {e}")
            return True, str(e)
        return False, ""

    thread_a = threading.Thread(target=lambda: None)
    thread_b = threading.Thread(target=lambda: None)

    def run_a():
        nonlocal failed, failure_message
        f, m = trigger_event_a()
        if f:
            failed = True
            failure_message = m

    def run_b():
        nonlocal failed, failure_message
        f, m = trigger_event_b()
        if f:
            failed = True
            failure_message = m

    thread_a = threading.Thread(target=run_a)
    thread_b = threading.Thread(target=run_b)

    thread_a.start()
    thread_b.start()
    thread_a.join()
    thread_b.join()

    if failed:
        print(f"Early failure detected in events a/b: {failure_message}")
        vc_fraud = get_fraud_vector_clock(order_id)
        vc_verif = get_verification_vector_clock(order_id)
        final_vc = {
            "fraud_detection": vc_fraud.fraud_detection,
            "fd_event_d": vc_fraud.fd_event_d,
            "fd_event_e": vc_fraud.fd_event_e,
            "transaction_verification": vc_verif.transaction_verification,
            "tv_event_a": vc_verif.tv_event_a,
            "tv_event_b": vc_verif.tv_event_b,
            "tv_event_c": vc_verif.tv_event_c,
            "suggestions": 0,
        }
        print(f"Broadcasting clear order with final VC: {final_vc}")
        broadcast_results = broadcast_clear_order(order_id, final_vc)
        print(f"Broadcast results: {broadcast_results}")
        return {
            "orderId": order_id,
            "status": "Order Rejected",
            "suggestedBooks": [],
            "failure": failure_message,
        }, 200

    print("Events a and b completed. Vector clocks updated.")

    def trigger_event_c():
        try:
            print(f"Triggering event_c (verify_card_format) for order {order_id}...")
            event_results["event_c"] = trigger_verification(order_id, "event_c")
            vc = get_verification_vector_clock(order_id)
            print(
                f"event_c result: {event_results['event_c'].is_valid}, {event_results['event_c'].message}, VC: c={vc.tv_event_c}"
            )
            if not event_results["event_c"].is_valid:
                return True, event_results["event_c"].message
        except Exception as e:
            print(f"event_c failed: {e}")
            return True, str(e)
        return False, ""

    def trigger_event_d():
        try:
            print(f"Triggering event_d (check_user_fraud) for order {order_id}...")
            event_results["event_d"] = trigger_fraud_check(order_id, "event_d")
            vc = get_fraud_vector_clock(order_id)
            print(
                f"event_d result: {event_results['event_d'].is_fraud}, {event_results['event_d'].message}, VC: d={vc.fd_event_d}"
            )
            if event_results["event_d"].is_fraud:
                return True, event_results["event_d"].message
        except Exception as e:
            print(f"event_d failed: {e}")
            return True, str(e)
        return False, ""

    thread_c = threading.Thread(target=lambda: None)
    thread_d = threading.Thread(target=lambda: None)

    def run_c():
        nonlocal failed, failure_message
        f, m = trigger_event_c()
        if f:
            failed = True
            failure_message = m

    def run_d():
        nonlocal failed, failure_message
        f, m = trigger_event_d()
        if f:
            failed = True
            failure_message = m

    thread_c = threading.Thread(target=run_c)
    thread_d = threading.Thread(target=run_d)

    thread_c.start()
    thread_d.start()
    thread_c.join()
    thread_d.join()

    if failed:
        print(f"Early failure detected in events c/d: {failure_message}")
        vc_fraud = get_fraud_vector_clock(order_id)
        vc_verif = get_verification_vector_clock(order_id)
        final_vc = {
            "fraud_detection": vc_fraud.fraud_detection,
            "fd_event_d": vc_fraud.fd_event_d,
            "fd_event_e": vc_fraud.fd_event_e,
            "transaction_verification": vc_verif.transaction_verification,
            "tv_event_a": vc_verif.tv_event_a,
            "tv_event_b": vc_verif.tv_event_b,
            "tv_event_c": vc_verif.tv_event_c,
            "suggestions": 0,
        }
        print(f"Broadcasting clear order with final VC: {final_vc}")
        broadcast_results = broadcast_clear_order(order_id, final_vc)
        print(f"Broadcast results: {broadcast_results}")
        return {
            "orderId": order_id,
            "status": "Order Rejected",
            "suggestedBooks": [],
            "failure": failure_message,
        }, 200

    print("Events c and d completed.")

    def trigger_event_e():
        try:
            print(f"Triggering event_e (check_card_fraud) for order {order_id}...")
            event_results["event_e"] = trigger_fraud_check(order_id, "event_e")
            vc = get_fraud_vector_clock(order_id)
            print(
                f"event_e result: {event_results['event_e'].is_fraud}, {event_results['event_e'].message}, VC: e={vc.fd_event_e}"
            )
            if event_results["event_e"].is_fraud:
                return True, event_results["event_e"].message
        except Exception as e:
            print(f"event_e failed: {e}")
            return True, str(e)
        return False, ""

    thread_e = threading.Thread(target=lambda: None)

    def run_e():
        nonlocal failed, failure_message
        f, m = trigger_event_e()
        if f:
            failed = True
            failure_message = m

    thread_e = threading.Thread(target=run_e)
    thread_e.start()
    thread_e.join()

    if failed:
        print(f"Early failure detected in event e: {failure_message}")
        vc_fraud = get_fraud_vector_clock(order_id)
        vc_verif = get_verification_vector_clock(order_id)
        final_vc = {
            "fraud_detection": vc_fraud.fraud_detection,
            "fd_event_d": vc_fraud.fd_event_d,
            "fd_event_e": vc_fraud.fd_event_e,
            "transaction_verification": vc_verif.transaction_verification,
            "tv_event_a": vc_verif.tv_event_a,
            "tv_event_b": vc_verif.tv_event_b,
            "tv_event_c": vc_verif.tv_event_c,
            "suggestions": 0,
        }
        print(f"Broadcasting clear order with final VC: {final_vc}")
        broadcast_results = broadcast_clear_order(order_id, final_vc)
        print(f"Broadcast results: {broadcast_results}")
        return {
            "orderId": order_id,
            "status": "Order Rejected",
            "suggestedBooks": [],
            "failure": failure_message,
        }, 200

    print("Event e completed.")

    def trigger_event_f():
        try:
            print(f"Triggering event_f (generate_suggestions) for order {order_id}...")
            event_results["event_f"] = trigger_suggestions(order_id, "event_f")
            print(f"event_f returned {len(event_results['event_f'].books)} books")
        except Exception as e:
            print(f"event_f failed: {e}")

    thread_f = threading.Thread(target=trigger_event_f)
    thread_f.start()
    thread_f.join()
    print("Event f completed. All events finished.")

    results["fraud"] = event_results["event_e"]
    results["verification"] = event_results["event_c"]
    results["suggestions"] = event_results["event_f"]

    vc_fraud = get_fraud_vector_clock(order_id)
    vc_verif = get_verification_vector_clock(order_id)
    vc_suggestions = get_suggestions_vector_clock(order_id)

    final_vc = {
        "fraud_detection": vc_fraud.fraud_detection,
        "fd_event_d": vc_fraud.fd_event_d,
        "fd_event_e": vc_fraud.fd_event_e,
        "transaction_verification": vc_verif.transaction_verification,
        "tv_event_a": vc_verif.tv_event_a,
        "tv_event_b": vc_verif.tv_event_b,
        "tv_event_c": vc_verif.tv_event_c,
        "suggestions": vc_suggestions.suggestions,
    }
    print(f"Final vector clock: {final_vc}")

    print(f"Broadcasting clear order with final VC: {final_vc}")
    broadcast_results = broadcast_clear_order(order_id, final_vc)
    print(f"Broadcast results: {broadcast_results}")

    if results["errors"]:
        return {
            "error": {"code": "INTERNAL_ERROR", "message": "; ".join(results["errors"])}
        }, 500

    if results["fraud"] and results["fraud"].is_fraud:
        return {
            "orderId": order_id,
            "status": "Order Rejected",
            "suggestedBooks": [],
        }, 200

    if results["verification"] and not results["verification"].is_valid:
        return {
            "orderId": order_id,
            "status": "Order Rejected",
            "suggestedBooks": [],
        }, 200

    suggested_books = []
    if results["suggestions"]:
        for book in results["suggestions"].books:
            suggested_books.append(
                {"bookId": book.bookId, "title": book.title, "author": book.author}
            )

    return {
        "orderId": order_id,
        "status": "Order Approved",
        "suggestedBooks": suggested_books,
    }, 200


def mask_fixed(card: str) -> str:
    digits = "".join(c for c in str(card) if c.isdigit())
    masked = "*" * 12 + digits[-4:].rjust(4, "*")
    return " ".join(masked[i : i + 4] for i in range(0, 16, 4))


if __name__ == "__main__":
    app.run(host="0.0.0.0")

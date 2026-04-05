import os
import sys
import threading
import uuid

import grpc
from flask import Flask, request
from flask_cors import CORS

# Import gRPC stubs
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

order_queue_grpc_path = os.path.abspath(
    os.path.join(FILE, "../../../utils/pb/order_queue")
)
sys.path.insert(0, order_queue_grpc_path)
import order_queue_pb2 as order_queue
import order_queue_pb2_grpc as order_queue_grpc


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


def mask_fixed(card: str) -> str:
    digits = "".join(c for c in str(card) if c.isdigit())
    masked = "*" * 12 + digits[-4:].rjust(4, "*")
    return " ".join(masked[i:i + 4] for i in range(0, 16, 4))


def merge_vcs(*vectors):
    result = [0, 0, 0]
    for vc in vectors:
        for i in range(3):
            result[i] = max(result[i], vc[i])
    return result


def build_order_kwargs(
    user_name, user_contact, card_number, expiration_date, cvv, item_count, terms_accepted
):
    return {
        "user_name": user_name,
        "user_contact": user_contact,
        "card_number": card_number,
        "expiration_date": expiration_date,
        "cvv": cvv,
        "item_count": item_count,
        "terms_accepted": terms_accepted,
    }


def init_fraud_service(order_id, order_kwargs):
    with grpc.insecure_channel("fraud_detection:50051") as channel:
        stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
        request = fraud_detection.InitOrderRequest(
            order=fraud_detection.OrderData(order_id=order_id, **order_kwargs)
        )
        return stub.InitOrder(request, timeout=5.0)


def init_transaction_service(order_id, order_kwargs):
    with grpc.insecure_channel("transaction_verification:50052") as channel:
        stub = transaction_verification_grpc.TransactionVerificationServiceStub(channel)
        request = transaction_verification.InitOrderRequest(
            order=transaction_verification.OrderData(order_id=order_id, **order_kwargs)
        )
        return stub.InitOrder(request, timeout=5.0)


def init_suggestions_service(order_id, order_kwargs):
    with grpc.insecure_channel("suggestions:50053") as channel:
        stub = suggestions_grpc.SuggestionsServiceStub(channel)
        request = suggestions.InitOrderRequest(
            order=suggestions.OrderData(order_id=order_id, **order_kwargs)
        )
        return stub.InitOrder(request, timeout=5.0)


def enqueue_order(order_id, order_kwargs):
    with grpc.insecure_channel("order_queue:50054") as channel:
        stub = order_queue_grpc.OrderQueueServiceStub(channel)
        request = order_queue.EnqueueRequest(
            order=order_queue.OrderData(
                order_id=order_id,
                user_name=order_kwargs["user_name"],
                user_contact=order_kwargs["user_contact"],
                card_number=order_kwargs["card_number"],
                expiration_date=order_kwargs["expiration_date"],
                cvv=order_kwargs["cvv"],
                item_count=order_kwargs["item_count"],
                terms_accepted=order_kwargs["terms_accepted"],
            )
        )
        return stub.Enqueue(request, timeout=5.0)


def tv_validate_items(order_id, vc):
    with grpc.insecure_channel("transaction_verification:50052") as channel:
        stub = transaction_verification_grpc.TransactionVerificationServiceStub(channel)
        request = transaction_verification.EventRequest(
            order_id=order_id,
            vc=transaction_verification.VectorClock(values=vc),
        )
        return stub.ValidateItems(request, timeout=5.0)


def tv_validate_user_data(order_id, vc):
    with grpc.insecure_channel("transaction_verification:50052") as channel:
        stub = transaction_verification_grpc.TransactionVerificationServiceStub(channel)
        request = transaction_verification.EventRequest(
            order_id=order_id,
            vc=transaction_verification.VectorClock(values=vc),
        )
        return stub.ValidateUserData(request, timeout=5.0)


def tv_validate_card_format(order_id, vc):
    with grpc.insecure_channel("transaction_verification:50052") as channel:
        stub = transaction_verification_grpc.TransactionVerificationServiceStub(channel)
        request = transaction_verification.EventRequest(
            order_id=order_id,
            vc=transaction_verification.VectorClock(values=vc),
        )
        return stub.ValidateCardFormat(request, timeout=5.0)


def fd_check_user_fraud(order_id, vc):
    with grpc.insecure_channel("fraud_detection:50051") as channel:
        stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
        request = fraud_detection.EventRequest(
            order_id=order_id,
            vc=fraud_detection.VectorClock(values=vc),
        )
        return stub.CheckUserFraud(request, timeout=5.0)


def fd_check_card_fraud(order_id, vc):
    with grpc.insecure_channel("fraud_detection:50051") as channel:
        stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
        request = fraud_detection.EventRequest(
            order_id=order_id,
            vc=fraud_detection.VectorClock(values=vc),
        )
        return stub.CheckCardFraud(request, timeout=5.0)


def sug_precompute(order_id, vc):
    with grpc.insecure_channel("suggestions:50053") as channel:
        stub = suggestions_grpc.SuggestionsServiceStub(channel)
        request = suggestions.EventRequest(
            order_id=order_id,
            vc=suggestions.VectorClock(values=vc),
        )
        return stub.PrecomputeSuggestions(request, timeout=5.0)


def sug_finalize(order_id, vc):
    with grpc.insecure_channel("suggestions:50053") as channel:
        stub = suggestions_grpc.SuggestionsServiceStub(channel)
        request = suggestions.EventRequest(
            order_id=order_id,
            vc=suggestions.VectorClock(values=vc),
        )
        return stub.FinalizeSuggestions(request, timeout=5.0)


def clear_fraud_service(order_id, final_vc):
    with grpc.insecure_channel("fraud_detection:50051") as channel:
        stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
        request = fraud_detection.ClearOrderRequest(
            order_id=order_id,
            final_vc=fraud_detection.VectorClock(values=final_vc),
        )
        return stub.ClearOrder(request, timeout=5.0)


def clear_transaction_service(order_id, final_vc):
    with grpc.insecure_channel("transaction_verification:50052") as channel:
        stub = transaction_verification_grpc.TransactionVerificationServiceStub(channel)
        request = transaction_verification.ClearOrderRequest(
            order_id=order_id,
            final_vc=transaction_verification.VectorClock(values=final_vc),
        )
        return stub.ClearOrder(request, timeout=5.0)


def clear_suggestions_service(order_id, final_vc):
    with grpc.insecure_channel("suggestions:50053") as channel:
        stub = suggestions_grpc.SuggestionsServiceStub(channel)
        request = suggestions.ClearOrderRequest(
            order_id=order_id,
            final_vc=suggestions.VectorClock(values=final_vc),
        )
        return stub.ClearOrder(request, timeout=5.0)


def broadcast_clear(order_id, final_vc):
    try:
        clear_results = [
            ("transaction_verification", clear_transaction_service(order_id, final_vc)),
            ("fraud_detection", clear_fraud_service(order_id, final_vc)),
            ("suggestions", clear_suggestions_service(order_id, final_vc)),
        ]
        failed_services = [
            f"{service}: {response.message}"
            for service, response in clear_results
            if not response.success
        ]

        if failed_services:
            print(
                f"[ORCH] order={order_id} clear_broadcast_warning="
                f"{'; '.join(failed_services)} final_vc={final_vc}"
            )
            return False

        print(f"[ORCH] order={order_id} clear_broadcast_sent final_vc={final_vc}")
        return True
    except Exception as e:
        print(f"[ORCH] order={order_id} clear_broadcast_warning={e}")
        return False


@app.route("/", methods=["GET"])
def index():
    return {"message": "Orchestrator is running."}, 200


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

    user = request_data.get("user", {}) or {}
    items = request_data.get("items", []) or []
    terms_accepted = bool(request_data.get("termsAndConditionsAccepted", False))

    user_name = (user.get("name") or "").strip()
    user_contact = (user.get("contact") or "").strip()

    credit_card = (user.get("creditCard") or {})
    card_number = (credit_card.get("number") or "").strip()
    expiration_date = (credit_card.get("expirationDate") or "").strip()
    cvv = (credit_card.get("cvv") or "").strip()

    if not user_name:
        return {
            "error": {
                "code": "BAD_REQUEST",
                "message": "User name is required.",
            }
        }, 400

    if not user_contact:
        return {
            "error": {
                "code": "BAD_REQUEST",
                "message": "User contact is required.",
            }
        }, 400

    item_count = len(items)
    order_id = str(uuid.uuid4())

    print(
        f"[ORCH] order={order_id} received_checkout "
        f"user={user_name} card={mask_fixed(card_number)} item_count={item_count}"
    )

    order_kwargs = build_order_kwargs(
        user_name=user_name,
        user_contact=user_contact,
        card_number=card_number,
        expiration_date=expiration_date,
        cvv=cvv,
        item_count=item_count,
        terms_accepted=terms_accepted,
    )

    # Initialization phase
    try:
        init_tv = init_transaction_service(order_id, order_kwargs)
        init_fd = init_fraud_service(order_id, order_kwargs)
        init_sug = init_suggestions_service(order_id, order_kwargs)
    except Exception as e:
        print(f"[ORCH] order={order_id} initialization_error={e}")
        return {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to initialize backend services.",
            }
        }, 500

    for name, response in [
        ("InitTransactionVerification", init_tv),
        ("InitFraudDetection", init_fd),
        ("InitSuggestions", init_sug),
    ]:
        if not response.success:
            print(
                f"[ORCH] order={order_id} step={name} success=False message={response.message}"
            )
            return {
                "orderId": order_id,
                "status": "Order Rejected",
                "suggestedBooks": [],
                "reason": response.message,
            }, 200

    print(f"[ORCH] order={order_id} initialization_complete")

    # Event-flow state
    cancelled = threading.Event()

    done = {
        "a": threading.Event(),  # ValidateItems
        "b": threading.Event(),  # ValidateUserData
        "c": threading.Event(),  # ValidateCardFormat
        "d": threading.Event(),  # CheckUserFraud
        "e": threading.Event(),  # CheckCardFraud
        "f": threading.Event(),  # PrecomputeSuggestions
        "g": threading.Event(),  # FinalizeSuggestions
    }

    state = {
        "event_vcs": {},
        "final_vc": [0, 0, 0],
        "books": [],
        "failure_kind": None,  # "event_failure" or "internal_error"
        "failed_step": None,
        "failure_message": None,
    }
    lock = threading.Lock()

    def store_event_result(step, response):
        vc = list(response.vc.values)
        with lock:
            state["event_vcs"][step] = vc
            state["final_vc"] = merge_vcs(state["final_vc"], vc)

    def merged_from(*steps):
        with lock:
            vcs = [state["event_vcs"][step] for step in steps if step in state["event_vcs"]]
        if not vcs:
            return [0, 0, 0]
        return merge_vcs(*vcs)

    def record_event_failure(step, response):
        with lock:
            if state["failure_kind"] is None:
                state["failure_kind"] = "event_failure"
                state["failed_step"] = step
                state["failure_message"] = response.message
                state["final_vc"] = merge_vcs(
                    state["final_vc"], list(response.vc.values)
                )
        cancelled.set()
        print(f"[ORCH] order={order_id} step={step} success=False message={response.message}")

    def record_internal_failure(step, message, fallback_vc):
        with lock:
            if state["failure_kind"] is None:
                state["failure_kind"] = "internal_error"
                state["failed_step"] = step
                state["failure_message"] = message
                state["final_vc"] = merge_vcs(state["final_vc"], fallback_vc)
        cancelled.set()
        print(f"[ORCH] order={order_id} step={step} internal_error={message}")

    def run_event(step, prereqs, input_steps, rpc_func):
        for prereq in prereqs:
            done[prereq].wait()

        if cancelled.is_set():
            done[step].set()
            return

        request_vc = merged_from(*input_steps)

        try:
            response = rpc_func(order_id, request_vc)
            store_event_result(step, response)

            if not response.success:
                record_event_failure(step, response)
        except Exception as e:
            record_internal_failure(step, str(e), request_vc)
        finally:
            done[step].set()

    def run_finalize():
        for prereq in ["e", "f"]:
            done[prereq].wait()

        if cancelled.is_set():
            done["g"].set()
            return

        request_vc = merged_from("e", "f")

        try:
            response = sug_finalize(order_id, request_vc)
            store_event_result("g", response)

            if response.success:
                books = []
                for book in response.books:
                    books.append(
                        {
                            "bookId": book.bookId,
                            "title": book.title,
                            "author": book.author,
                        }
                    )
                with lock:
                    state["books"] = books
            else:
                record_event_failure("g", response)
        except Exception as e:
            record_internal_failure("g", str(e), request_vc)
        finally:
            done["g"].set()

    # Example partial order:
    # a || b
    # c after a
    # d after b
    # e after c and d
    # f after a
    # g after e and f
    workers = [
        threading.Thread(target=run_event, args=("a", [], [], tv_validate_items)),
        threading.Thread(target=run_event, args=("b", [], [], tv_validate_user_data)),
        threading.Thread(target=run_event, args=("c", ["a"], ["a"], tv_validate_card_format)),
        threading.Thread(target=run_event, args=("d", ["b"], ["b"], fd_check_user_fraud)),
        threading.Thread(target=run_event, args=("e", ["c", "d"], ["c", "d"], fd_check_card_fraud)),
        threading.Thread(target=run_event, args=("f", ["a"], ["a"], sug_precompute)),
        threading.Thread(target=run_finalize),
    ]

    print(f"[ORCH] order={order_id} starting_event_flow")
    for worker in workers:
        worker.start()

    for worker in workers:
        worker.join()

    print(f"[ORCH] order={order_id} all_worker_threads_finished")

    with lock:
        final_vc = merge_vcs(state["final_vc"], *state["event_vcs"].values())
        state["final_vc"] = final_vc

    if state["failure_kind"] == "internal_error":
        broadcast_clear(order_id, final_vc)
        return {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": state["failure_message"],
            }
        }, 500

    if state["failure_kind"] == "event_failure":
        broadcast_clear(order_id, final_vc)
        return {
            "error": {
                "code": "ORDER_REJECTED",
                "message": state["failure_message"],
            }
        }, 400

    try:
        enqueue_response = enqueue_order(order_id, order_kwargs)
    except Exception as e:
        print(f"[ORCH] order={order_id} enqueue_error={e}")
        return {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Order was approved but could not be queued.",
            }
        }, 500

    if not enqueue_response.success:
        print(f"[ORCH] order={order_id} enqueue_failed message={enqueue_response.message}")
        return {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": enqueue_response.message,
            }
        }, 500

    print(f"[ORCH] order={order_id} enqueue_success")
    broadcast_clear(order_id, final_vc)
    print(f"[ORCH] order={order_id} final_status=APPROVED final_vc={final_vc}")

    return {
        "orderId": order_id,
        "status": "Order Approved",
        "suggestedBooks": state["books"],
    }, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0")

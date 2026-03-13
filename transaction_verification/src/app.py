import sys
import os
import threading
import time
from concurrent import futures

FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
transaction_verification_grpc_path = os.path.abspath(
    os.path.join(FILE, "../../../utils/pb/transaction_verification")
)
sys.path.insert(0, transaction_verification_grpc_path)

import grpc
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc

order_cache = {}
vector_clocks = {}
cache_lock = threading.Lock()

EVENTS = {
    "a": "verify_items_not_empty",
    "b": "verify_user_data",
    "c": "verify_card_format",
}


def initialize_vector_clock(order_id):
    return {
        "fraud_detection": 0,
        "transaction_verification": 0,
        "suggestions": 0,
        "tv_event_a": 0,
        "tv_event_b": 0,
        "tv_event_c": 0,
    }


def check_event_dependencies(vc, required_events):
    for event in required_events:
        if vc.get(event, 0) == 0:
            return False, f"Required event {event} not completed"
    return True, "OK"


def execute_event_a(order_id):
    order_data = order_cache.get(order_id)
    if not order_data:
        return None

    with cache_lock:
        vector_clocks[order_id]["tv_event_a"] += 1

    item_count = order_data["item_count"]
    is_valid = item_count > 0
    message = "Items verified: not empty" if is_valid else "No items in order."

    print(f"Event a (verify_items_not_empty) for order {order_id}: {is_valid}")
    return {"is_valid": is_valid, "message": message}


def execute_event_b(order_id):
    order_data = order_cache.get(order_id)
    if not order_data:
        return None

    with cache_lock:
        vector_clocks[order_id]["tv_event_b"] += 1

    user_name = order_data.get("user_name", "")
    user_contact = order_data.get("user_contact", "")
    is_valid = bool(user_name and user_contact)
    message = "User data verified" if is_valid else "Missing user name or contact."

    print(f"Event b (verify_user_data) for order {order_id}: {is_valid}")
    return {"is_valid": is_valid, "message": message}


def execute_event_c(order_id):
    order_data = order_cache.get(order_id)
    if not order_data:
        return None

    with cache_lock:
        vector_clocks[order_id]["tv_event_c"] += 1

    card_number = order_data.get("card_number", "")
    expiration_date = order_data.get("expiration_date", "")
    cvv = order_data.get("cvv", "")
    card_digits = extract_card_digits(card_number)

    has_card = bool(card_number and expiration_date and cvv)
    correct_format = len(card_digits) == 16
    is_valid = has_card and correct_format

    if not has_card:
        message = "Missing credit card information."
    elif not correct_format:
        message = "Invalid card number format."
    else:
        message = "Credit card format verified."

    print(f"Event c (verify_card_format) for order {order_id}: {is_valid}")
    return {"is_valid": is_valid, "message": message}


def process_order_sequential(order_id):
    order_data = order_cache.get(order_id)
    if not order_data:
        return None

    with cache_lock:
        vector_clocks[order_id]["transaction_verification"] += 1

    card_digits = extract_card_digits(order_data["card_number"])
    is_valid = True
    message = "Transaction is valid."

    if not order_data["user_name"]:
        is_valid = False
        message = "Missing user name."
    elif not order_data["user_contact"]:
        is_valid = False
        message = "Missing user contact."
    elif order_data["item_count"] <= 0:
        is_valid = False
        message = "No items in order."
    elif not order_data["terms_accepted"]:
        is_valid = False
        message = "Terms and conditions not accepted."
    elif (
        not order_data["card_number"]
        or not order_data["expiration_date"]
        or not order_data["cvv"]
    ):
        is_valid = False
        message = "Missing credit card information."
    elif len(card_digits) != 16:
        is_valid = False
        message = "Invalid card number."

    result = {
        "is_valid": is_valid,
        "message": message,
        "vector_clock": vector_clocks[order_id].copy(),
    }

    print(
        f"Transaction verification processed for order {order_id}: {is_valid}, {message}"
    )
    return result


class TransactionVerificationService(
    transaction_verification_grpc.TransactionVerificationServiceServicer
):
    def VerifyTransaction(self, request, context):
        order_id = request.order_id if hasattr(request, "order_id") else ""
        print(f"Received transaction verification request for order: {order_id}")

        with cache_lock:
            order_cache[order_id] = {
                "user_name": request.user_name,
                "user_contact": request.user_contact,
                "card_number": request.card_number,
                "expiration_date": request.expiration_date,
                "cvv": request.cvv,
                "item_count": request.item_count,
                "terms_accepted": request.terms_accepted,
            }
            if order_id not in vector_clocks:
                vector_clocks[order_id] = initialize_vector_clock(order_id)
            vector_clocks[order_id]["transaction_verification"] = 0

        print(
            f"Order {order_id} cached in transaction_verification. Vector clock: {vector_clocks.get(order_id)}"
        )

        response = transaction_verification.TransactionVerificationResponse()
        response.is_valid = True
        response.message = "Order cached. Waiting for execution trigger."

        return response

    def TriggerVerification(self, request, context):
        order_id = request.order_id
        event_type = request.event_type if hasattr(request, "event_type") else "all"
        print(
            f"Triggering transaction verification for order {order_id}, event: {event_type}"
        )

        with cache_lock:
            if order_id not in vector_clocks:
                vector_clocks[order_id] = initialize_vector_clock(order_id)
            vc = vector_clocks.get(order_id, {})

        results = {}

        if event_type == "all":
            result = process_order_sequential(order_id)
            if result:
                with cache_lock:
                    if order_id in order_cache:
                        del order_cache[order_id]
                response = transaction_verification.TransactionVerificationResponse()
                response.is_valid = result["is_valid"]
                response.message = result["message"]
                response.failed = not result["is_valid"]
                print(
                    f"[VC] Transaction verification for order {order_id}: VC={vector_clocks.get(order_id, {})}"
                )
                return response
        elif event_type == "event_a":
            result = execute_event_a(order_id)
            if result:
                response = transaction_verification.TransactionVerificationResponse()
                response.is_valid = result["is_valid"]
                response.message = result["message"]
                response.failed = not result["is_valid"]
                print(
                    f"[VC] Event a for order {order_id}: VC tv_event_a={vector_clocks.get(order_id, {}).get('tv_event_a', 0)}"
                )
                return response
        elif event_type == "event_b":
            # Event B (verify_user_data) can proceed without dependencies usually
            result = execute_event_b(order_id)
            if result:
                response = transaction_verification.TransactionVerificationResponse()
                response.is_valid = result["is_valid"]
                response.message = result["message"]
                response.failed = not result["is_valid"]
                print(
                    f"[VC] Event b for order {order_id}: VC tv_event_b={vector_clocks.get(order_id, {}).get('tv_event_b', 0)}"
                )
                return response
        elif event_type == "event_c":
            # Event C (verify_credit_card) depends on Event A (verify_items_not_empty)
            can_proceed, msg = check_event_dependencies(vc, ["tv_event_a"])
            if not can_proceed:
                response = transaction_verification.TransactionVerificationResponse()
                response.is_valid = False
                response.message = f"Cannot execute event_c: {msg}"
                response.failed = True
                return response
            result = execute_event_c(order_id)
            if result:
                response = transaction_verification.TransactionVerificationResponse()
                response.is_valid = result["is_valid"]
                response.message = result["message"]
                response.failed = not result["is_valid"]
                print(
                    f"[VC] Event c for order {order_id}: VC tv_event_c={vector_clocks.get(order_id, {}).get('tv_event_c', 0)}"
                )
                return response

        response = transaction_verification.TransactionVerificationResponse()
        response.is_valid = False
        response.message = "Order not found in cache or invalid event type."
        return response

    def GetVectorClock(self, request, context):
        order_id = request.order_id
        with cache_lock:
            vc = vector_clocks.get(order_id, {})

        response = transaction_verification.VectorClockResponse()
        response.transaction_verification = vc.get("transaction_verification", 0)
        response.tv_event_a = vc.get("tv_event_a", 0)
        response.tv_event_b = vc.get("tv_event_b", 0)
        response.tv_event_c = vc.get("tv_event_c", 0)
        response.fraud_detection = vc.get("fraud_detection", 0)
        response.suggestions = vc.get("suggestions", 0)
        return response

    def ClearOrder(self, request, context):
        order_id = request.order_id
        print(f"Received ClearOrder request for order: {order_id}")

        with cache_lock:
            vc = vector_clocks.get(order_id, {})

            local_vc_tv = vc.get("transaction_verification", 0)
            local_vc_a = vc.get("tv_event_a", 0)
            local_vc_b = vc.get("tv_event_b", 0)
            local_vc_c = vc.get("tv_event_c", 0)

            expected_vc_tv = request.final_vc_transaction_verification
            expected_vc_a = request.final_vc_tv_event_a
            expected_vc_b = request.final_vc_tv_event_b
            expected_vc_c = request.final_vc_tv_event_c

            if (
                local_vc_tv <= expected_vc_tv
                and local_vc_a <= expected_vc_a
                and local_vc_b <= expected_vc_b
                and local_vc_c <= expected_vc_c
            ):
                if order_id in order_cache:
                    del order_cache[order_id]
                if order_id in vector_clocks:
                    del vector_clocks[order_id]
                print(
                    f"Order {order_id} cleared successfully in transaction_verification"
                )
                response = transaction_verification.ClearOrderResponse()
                response.success = True
                response.message = "Order cleared successfully"
                return response
            else:
                print(f"Vector clock mismatch for order {order_id}. Local VC: {vc}")
                response = transaction_verification.ClearOrderResponse()
                response.success = False
                response.message = f"Vector clock mismatch. Local: tv={local_vc_tv}, a={local_vc_a}, b={local_vc_b}, c={local_vc_c}. Expected: tv={expected_vc_tv}, a={expected_vc_a}, b={expected_vc_b}, c={expected_vc_c}"
                return response


def extract_card_digits(card: str) -> str:
    """
    Return only the digit characters from the given card number.
    """
    return "".join(c for c in str(card) if c.isdigit())


def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    transaction_verification_grpc.add_TransactionVerificationServiceServicer_to_server(
        TransactionVerificationService(), server
    )

    port = "50052"
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Transaction verification server started. Listening on port 50052.")
    server.wait_for_termination()


def mask_fixed(card: str) -> str:
    digits = "".join(c for c in str(card) if c.isdigit())
    masked = "*" * 12 + digits[-4:].rjust(4, "*")
    return " ".join(masked[i : i + 4] for i in range(0, 16, 4))


if __name__ == "__main__":
    serve()

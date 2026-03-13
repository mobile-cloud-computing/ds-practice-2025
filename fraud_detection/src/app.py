import sys
import os
import threading
import time
from concurrent import futures

FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
fraud_detection_grpc_path = os.path.abspath(
    os.path.join(FILE, "../../../utils/pb/fraud_detection")
)
sys.path.insert(0, fraud_detection_grpc_path)

import grpc
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc

order_cache = {}
vector_clocks = {}
cache_lock = threading.Lock()


def initialize_vector_clock(order_id):
    return {
        "fraud_detection": 0,
        "transaction_verification": 0,
        "suggestions": 0,
        "tv_event_a": 0,
        "tv_event_b": 0,
        "tv_event_c": 0,
        "fd_event_d": 0,
        "fd_event_e": 0,
    }


def check_event_dependencies(vc, required_events):
    for event in required_events:
        if vc.get(event, 0) == 0:
            return False, f"Required event {event} not completed"
    return True, "OK"


def execute_event_d(order_id):
    order_data = order_cache.get(order_id)
    if not order_data:
        return None

    with cache_lock:
        vector_clocks[order_id]["fd_event_d"] += 1

    user_name = order_data.get("user_name", "")
    is_fraud = "fraud" in user_name.lower()
    message = (
        "User data fraud check passed" if not is_fraud else "Suspicious user name."
    )

    print(f"Event d (check_user_fraud) for order {order_id}: {is_fraud}, {message}")
    return {"is_fraud": is_fraud, "message": message}


def execute_event_e(order_id):
    order_data = order_cache.get(order_id)
    if not order_data:
        return None

    with cache_lock:
        vector_clocks[order_id]["fd_event_e"] += 1

    card_number = order_data.get("card_number", "")
    card_digits = extract_card_digits(card_number)
    item_count = order_data.get("item_count", 0)

    is_fraud = False
    message = "Credit card fraud check passed"

    if item_count > 20:
        is_fraud = True
        message = "Too many items in order."
    elif len(card_digits) != 16:
        is_fraud = True
        message = "Invalid card number."
    elif card_digits.startswith("0000"):
        is_fraud = True
        message = "Suspicious card number pattern."
    elif card_digits.endswith("0000"):
        is_fraud = True
        message = "Suspicious card number pattern."

    print(f"Event e (check_card_fraud) for order {order_id}: {is_fraud}, {message}")
    return {"is_fraud": is_fraud, "message": message}


def process_order(order_id):
    order_data = order_cache.get(order_id)
    if not order_data:
        return None

    with cache_lock:
        vector_clocks[order_id]["fraud_detection"] += 1

    card_digits = extract_card_digits(order_data["card_number"])
    is_fraud = False
    message = "No fraud detected."

    if order_data["item_count"] > 20:
        is_fraud = True
        message = "Too many items in order."
    elif len(card_digits) != 16:
        is_fraud = True
        message = "Invalid card number."
    elif card_digits.startswith("0000"):
        is_fraud = True
        message = "Suspicious card number pattern."
    elif card_digits.endswith("0000"):
        is_fraud = True
        message = "Suspicious card number pattern."
    elif "fraud" in order_data["user_name"].lower():
        is_fraud = True
        message = "Suspicious user name."

    result = {
        "is_fraud": is_fraud,
        "message": message,
        "vector_clock": vector_clocks[order_id].copy(),
    }

    print(f"Fraud detection processed for order {order_id}: {is_fraud}, {message}")
    return result


class FraudDetectionService(fraud_detection_grpc.FraudDetectionServiceServicer):
    def CheckFraud(self, request, context):
        order_id = request.order_id if hasattr(request, "order_id") else ""
        print(f"Received fraud check request for order: {order_id}")

        with cache_lock:
            order_cache[order_id] = {
                "user_name": request.user_name,
                "card_number": request.card_number,
                "item_count": request.item_count,
            }
            if order_id not in vector_clocks:
                vector_clocks[order_id] = initialize_vector_clock(order_id)
            vector_clocks[order_id]["fraud_detection"] = 0

        print(
            f"Order {order_id} cached in fraud_detection. Vector clock: {vector_clocks.get(order_id)}"
        )

        response = fraud_detection.FraudCheckResponse()
        response.is_fraud = False
        response.message = "Order cached. Waiting for execution trigger."

        return response

    def TriggerFraudCheck(self, request, context):
        order_id = request.order_id
        event_type = request.event_type if hasattr(request, "event_type") else "all"
        print(f"Triggering fraud check for order {order_id}, event: {event_type}")

        with cache_lock:
            if order_id not in vector_clocks:
                vector_clocks[order_id] = initialize_vector_clock(order_id)
            vc = vector_clocks.get(order_id, {})

        if event_type == "all":
            result = process_order(order_id)
            if result:
                with cache_lock:
                    if order_id in order_cache:
                        del order_cache[order_id]
                response = fraud_detection.FraudCheckResponse()
                response.is_fraud = result["is_fraud"]
                response.message = result["message"]
                response.failed = result["is_fraud"]
                print(
                    f"[VC] Fraud detection for order {order_id}: VC={vector_clocks.get(order_id, {})}"
                )
                return response
        elif event_type == "event_d":
            # Event D (check_user_fraud) should first be cleared by transaction-verification service (Event B)
            can_proceed, msg = check_event_dependencies(vc, ["tv_event_b"])
            if not can_proceed:
                # Update current VC state from other services to be sure
                # In a real system we would use the passed VC or fetch it.
                # For this task, we assume the orchestrator will only call this after tv_event_b is done.
                # But to be robust, we can return a failure that orchestrator handles.
                response = fraud_detection.FraudCheckResponse()
                response.is_fraud = False
                response.message = f"Cannot execute event_d: {msg}"
                response.failed = True
                return response
            result = execute_event_d(order_id)
            if result:
                response = fraud_detection.FraudCheckResponse()
                response.is_fraud = result["is_fraud"]
                response.message = result["message"]
                response.failed = result["is_fraud"]
                print(
                    f"[VC] Event d for order {order_id}: VC fd_event_d={vector_clocks.get(order_id, {}).get('fd_event_d', 0)}"
                )
                return response
        elif event_type == "event_e":
            # Event E (check_card_fraud) should first be cleared by transaction-verification (Event C) and fraud-detection (Event D)
            can_proceed, msg = check_event_dependencies(
                vc, ["tv_event_c", "fd_event_d"]
            )
            if not can_proceed:
                response = fraud_detection.FraudCheckResponse()
                response.is_fraud = False
                response.message = f"Cannot execute event_e: {msg}"
                response.failed = True
                return response
            result = execute_event_e(order_id)
            if result:
                response = fraud_detection.FraudCheckResponse()
                response.is_fraud = result["is_fraud"]
                response.message = result["message"]
                response.failed = result["is_fraud"]
                print(
                    f"[VC] Event e for order {order_id}: VC fd_event_e={vector_clocks.get(order_id, {}).get('fd_event_e', 0)}"
                )
                return response

        response = fraud_detection.FraudCheckResponse()
        response.is_fraud = True
        response.message = "Order not found in cache or invalid event type."
        response.failed = True
        return response

    def GetVectorClock(self, request, context):
        order_id = request.order_id
        with cache_lock:
            vc = vector_clocks.get(order_id, {})

        response = fraud_detection.VectorClockResponse()
        response.fraud_detection = vc.get("fraud_detection", 0)
        response.fd_event_d = vc.get("fd_event_d", 0)
        response.fd_event_e = vc.get("fd_event_e", 0)
        response.transaction_verification = vc.get("transaction_verification", 0)
        response.tv_event_a = vc.get("tv_event_a", 0)
        response.tv_event_b = vc.get("tv_event_b", 0)
        response.tv_event_c = vc.get("tv_event_c", 0)
        response.suggestions = vc.get("suggestions", 0)
        return response

    def ClearOrder(self, request, context):
        order_id = request.order_id
        print(f"Received ClearOrder request for order: {order_id}")

        with cache_lock:
            vc = vector_clocks.get(order_id, {})

            local_vc_fd = vc.get("fraud_detection", 0)
            local_vc_d = vc.get("fd_event_d", 0)
            local_vc_e = vc.get("fd_event_e", 0)
            local_vc_tv = vc.get("transaction_verification", 0)
            local_vc_tv_a = vc.get("tv_event_a", 0)
            local_vc_tv_b = vc.get("tv_event_b", 0)
            local_vc_tv_c = vc.get("tv_event_c", 0)
            local_vc_suggestions = vc.get("suggestions", 0)

            expected_vc_fd = request.final_vc_fraud_detection
            expected_vc_d = request.final_vc_fd_event_d
            expected_vc_e = request.final_vc_fd_event_e
            expected_vc_tv = request.final_vc_transaction_verification
            expected_vc_tv_a = request.final_vc_tv_event_a
            expected_vc_tv_b = request.final_vc_tv_event_b
            expected_vc_tv_c = request.final_vc_tv_event_c
            expected_vc_suggestions = request.final_vc_suggestions

            if (
                local_vc_fd <= expected_vc_fd
                and local_vc_d <= expected_vc_d
                and local_vc_e <= expected_vc_e
                and local_vc_tv <= expected_vc_tv
                and local_vc_tv_a <= expected_vc_tv_a
                and local_vc_tv_b <= expected_vc_tv_b
                and local_vc_tv_c <= expected_vc_tv_c
                and local_vc_suggestions <= expected_vc_suggestions
            ):
                if order_id in order_cache:
                    del order_cache[order_id]
                if order_id in vector_clocks:
                    del vector_clocks[order_id]
                print(f"Order {order_id} cleared successfully in fraud_detection")
                response = fraud_detection.ClearOrderResponse()
                response.success = True
                response.message = "Order cleared successfully"
                return response
            else:
                print(f"Vector clock mismatch for order {order_id}. Local VC: {vc}")
                response = fraud_detection.ClearOrderResponse()
                response.success = False
                response.message = (
                    f"Vector clock mismatch. Local: fd={local_vc_fd}, d={local_vc_d}, e={local_vc_e}, tv={local_vc_tv}, tv_a={local_vc_tv_a}, tv_b={local_vc_tv_b}, tv_c={local_vc_tv_c}, suggestions={local_vc_suggestions}. "
                    f"Expected: fd={expected_vc_fd}, d={expected_vc_d}, e={expected_vc_e}, tv={expected_vc_tv}, tv_a={expected_vc_tv_a}, tv_b={expected_vc_tv_b}, tv_c={expected_vc_tv_c}, suggestions={expected_vc_suggestions}"
                )
                return response


def extract_card_digits(card: str) -> str:
    """
    Return only the digit characters from the given card number.
    """
    return "".join(c for c in str(card) if c.isdigit())


def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    fraud_detection_grpc.add_FraudDetectionServiceServicer_to_server(
        FraudDetectionService(), server
    )

    port = "50051"
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Fraud detection server started. Listening on port 50051.")
    server.wait_for_termination()


def mask_fixed(card: str) -> str:
    digits = "".join(c for c in str(card) if c.isdigit())
    masked = "*" * 12 + digits[-4:].rjust(4, "*")
    return " ".join(masked[i : i + 4] for i in range(0, 16, 4))


if __name__ == "__main__":
    serve()

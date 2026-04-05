import os
import sys
import threading
from concurrent import futures

FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
fraud_detection_grpc_path = os.path.abspath(
    os.path.join(FILE, "../../../utils/pb/fraud_detection")
)
sys.path.insert(0, fraud_detection_grpc_path)

import grpc
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc


SERVICE_INDEX = 1  # [transaction_verification, fraud_detection, suggestions]

orders = {}
orders_lock = threading.Lock()


def merge_vc(local_vc, incoming_vc):
    return [max(a, b) for a, b in zip(local_vc, incoming_vc)]


def tick(vc, idx):
    vc[idx] += 1
    return vc


def extract_card_digits(card: str) -> str:
    return "".join(c for c in str(card) if c.isdigit())


def get_order_state(order_id: str):
    with orders_lock:
        return orders.get(order_id)


class FraudDetectionService(fraud_detection_grpc.FraudDetectionServiceServicer):
    def InitOrder(self, request, context):
        order = request.order

        with orders_lock:
            orders[order.order_id] = {
                "order": order,
                "vc": [0, 0, 0],
            }

        print(f"[FD] order={order.order_id} event=InitOrder vc={[0, 0, 0]} success=True")

        return fraud_detection.EventResponse(
            success=True,
            message="Fraud service initialized order.",
            vc=fraud_detection.VectorClock(values=[0, 0, 0]),
        )

    def CheckUserFraud(self, request, context):
        state = get_order_state(request.order_id)
        if state is None:
            return fraud_detection.EventResponse(
                success=False,
                message="Order not found in fraud service.",
                vc=fraud_detection.VectorClock(values=[0, 0, 0]),
            )

        incoming_vc = list(request.vc.values)
        local_vc = state["vc"]
        vc = merge_vc(local_vc, incoming_vc)
        vc = tick(vc, SERVICE_INDEX)
        state["vc"] = vc

        user_name = state["order"].user_name
        success = "fraud" not in user_name.lower()
        message = "User fraud check passed." if success else "Suspicious user name."

        print(
            f"[FD] order={request.order_id} event=CheckUserFraud "
            f"vc={vc} success={success}"
        )

        return fraud_detection.EventResponse(
            success=success,
            message=message,
            vc=fraud_detection.VectorClock(values=vc),
        )

    def CheckCardFraud(self, request, context):
        state = get_order_state(request.order_id)
        if state is None:
            return fraud_detection.EventResponse(
                success=False,
                message="Order not found in fraud service.",
                vc=fraud_detection.VectorClock(values=[0, 0, 0]),
            )

        incoming_vc = list(request.vc.values)
        local_vc = state["vc"]
        vc = merge_vc(local_vc, incoming_vc)
        vc = tick(vc, SERVICE_INDEX)
        state["vc"] = vc

        card_digits = extract_card_digits(state["order"].card_number)

        success = True
        message = "Card fraud check passed."

        if len(card_digits) != 16:
            success = False
            message = "Invalid card number."
        elif card_digits.startswith("0000") or card_digits.endswith("0000"):
            success = False
            message = "Suspicious card number pattern."

        print(
            f"[FD] order={request.order_id} event=CheckCardFraud "
            f"vc={vc} success={success}"
        )

        return fraud_detection.EventResponse(
            success=success,
            message=message,
            vc=fraud_detection.VectorClock(values=vc),
        )

    def ClearOrder(self, request, context):
        order_id = request.order_id
        final_vc = list(request.final_vc.values)

        with orders_lock:
            state = orders.get(order_id)

            if state is None:
                return fraud_detection.EventResponse(
                    success=False,
                    message="Order not found in fraud service.",
                    vc=fraud_detection.VectorClock(values=[0, 0, 0]),
                )

            local_vc = state["vc"]
            can_clear = all(a <= b for a, b in zip(local_vc, final_vc))

            if can_clear:
                del orders[order_id]

        success = can_clear
        message = (
            "Order cleared from fraud service."
            if success
            else "Cannot clear order: local VC is ahead of final VC."
        )

        print(
            f"[FD] order={order_id} event=ClearOrder "
            f"local_vc={local_vc} final_vc={final_vc} success={success}"
        )

        return fraud_detection.EventResponse(
            success=success,
            message=message,
            vc=fraud_detection.VectorClock(values=final_vc),
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    fraud_detection_grpc.add_FraudDetectionServiceServicer_to_server(
        FraudDetectionService(), server
    )

    port = "50051"
    server.add_insecure_port("[::]:" + port)
    server.start()
    print(f"Fraud detection server started. Listening on port {port}.")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
import os
import sys
import threading
from concurrent import futures

FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
transaction_verification_grpc_path = os.path.abspath(
    os.path.join(FILE, "../../../utils/pb/transaction_verification")
)
sys.path.insert(0, transaction_verification_grpc_path)

import grpc
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc


SERVICE_INDEX = 0  # [transaction_verification, fraud_detection, suggestions]

orders = {}
orders_lock = threading.Lock()


def merge_vc(local_vc, incoming_vc):
    return [max(a, b) for a, b in zip(local_vc, incoming_vc)]


def tick(vc, idx):
    vc[idx] += 1
    return vc


def extract_card_digits(card: str) -> str:
    return "".join(c for c in str(card) if c.isdigit())


def mask_fixed(card: str) -> str:
    digits = extract_card_digits(card)
    masked = "*" * 12 + digits[-4:].rjust(4, "*")
    return " ".join(masked[i:i + 4] for i in range(0, 16, 4))


def get_order_state(order_id: str):
    with orders_lock:
        return orders.get(order_id)


class TransactionVerificationService(
    transaction_verification_grpc.TransactionVerificationServiceServicer
):
    def InitOrder(self, request, context):
        order = request.order

        with orders_lock:
            orders[order.order_id] = {
                "order": order,
                "vc": [0, 0, 0],
            }

        print(f"[TV] order={order.order_id} event=InitOrder vc={[0, 0, 0]} success=True")

        return transaction_verification.EventResponse(
            success=True,
            message="Transaction verification service initialized order.",
            vc=transaction_verification.VectorClock(values=[0, 0, 0]),
        )

    def ValidateItems(self, request, context):
        state = get_order_state(request.order_id)
        if state is None:
            return transaction_verification.EventResponse(
                success=False,
                message="Order not found in transaction verification service.",
                vc=transaction_verification.VectorClock(values=[0, 0, 0]),
            )

        incoming_vc = list(request.vc.values)
        local_vc = state["vc"]
        vc = merge_vc(local_vc, incoming_vc)
        vc = tick(vc, SERVICE_INDEX)
        state["vc"] = vc

        item_count = state["order"].item_count
        success = item_count > 0
        message = "Items check passed." if success else "No items in order."

        print(
            f"[TV] order={request.order_id} event=ValidateItems "
            f"vc={vc} success={success} item_count={item_count}"
        )

        return transaction_verification.EventResponse(
            success=success,
            message=message,
            vc=transaction_verification.VectorClock(values=vc),
        )

    def ValidateUserData(self, request, context):
        state = get_order_state(request.order_id)
        if state is None:
            return transaction_verification.EventResponse(
                success=False,
                message="Order not found in transaction verification service.",
                vc=transaction_verification.VectorClock(values=[0, 0, 0]),
            )

        incoming_vc = list(request.vc.values)
        local_vc = state["vc"]
        vc = merge_vc(local_vc, incoming_vc)
        vc = tick(vc, SERVICE_INDEX)
        state["vc"] = vc

        order = state["order"]
        success = True
        message = "User data check passed."

        if not order.user_name:
            success = False
            message = "Missing user name."
        elif not order.user_contact:
            success = False
            message = "Missing user contact."
        elif not order.terms_accepted:
            success = False
            message = "Terms and conditions not accepted."

        print(
            f"[TV] order={request.order_id} event=ValidateUserData "
            f"vc={vc} success={success}"
        )

        return transaction_verification.EventResponse(
            success=success,
            message=message,
            vc=transaction_verification.VectorClock(values=vc),
        )

    def ValidateCardFormat(self, request, context):
        state = get_order_state(request.order_id)
        if state is None:
            return transaction_verification.EventResponse(
                success=False,
                message="Order not found in transaction verification service.",
                vc=transaction_verification.VectorClock(values=[0, 0, 0]),
            )

        incoming_vc = list(request.vc.values)
        local_vc = state["vc"]
        vc = merge_vc(local_vc, incoming_vc)
        vc = tick(vc, SERVICE_INDEX)
        state["vc"] = vc

        order = state["order"]
        card_digits = extract_card_digits(order.card_number)

        success = True
        message = "Card format check passed."

        if not order.card_number or not order.expiration_date or not order.cvv:
            success = False
            message = "Missing credit card information."
        elif len(card_digits) != 16:
            success = False
            message = "Invalid card number."

        print(
            f"[TV] order={request.order_id} event=ValidateCardFormat "
            f"vc={vc} success={success} masked_card={mask_fixed(order.card_number)}"
        )

        return transaction_verification.EventResponse(
            success=success,
            message=message,
            vc=transaction_verification.VectorClock(values=vc),
        )

    def ClearOrder(self, request, context):
        order_id = request.order_id
        final_vc = list(request.final_vc.values)

        with orders_lock:
            state = orders.get(order_id)

            if state is None:
                return transaction_verification.EventResponse(
                    success=False,
                    message="Order not found in transaction verification service.",
                    vc=transaction_verification.VectorClock(values=[0, 0, 0]),
                )

            local_vc = state["vc"]
            can_clear = all(a <= b for a, b in zip(local_vc, final_vc))

            if can_clear:
                del orders[order_id]

        success = can_clear
        message = (
            "Order cleared from transaction verification service."
            if success
            else "Cannot clear order: local VC is ahead of final VC."
        )

        print(
            f"[TV] order={order_id} event=ClearOrder "
            f"local_vc={local_vc} final_vc={final_vc} success={success}"
        )

        return transaction_verification.EventResponse(
            success=success,
            message=message,
            vc=transaction_verification.VectorClock(values=final_vc),
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    transaction_verification_grpc.add_TransactionVerificationServiceServicer_to_server(
        TransactionVerificationService(), server
    )

    port = "50052"
    server.add_insecure_port("[::]:" + port)
    server.start()
    print(f"Transaction verification server started. Listening on port {port}.")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
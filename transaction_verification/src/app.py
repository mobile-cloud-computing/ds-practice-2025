import sys
import os
import json
import threading
import grpc
from concurrent import futures

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")

transaction_verification_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/transaction_verification'))
sys.path.insert(0, transaction_verification_grpc_path)
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc

fraud_detection_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/fraud_detection'))
sys.path.insert(0, fraud_detection_grpc_path)
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc


SERVICE_NAME = "transaction_verification"
MY_IDX = 0
ORDER_CACHE = {}
ORDER_CACHE_LOCK = threading.Lock()
TOTAL_SERVICES = 3


def zero_vc():
    return [0] * TOTAL_SERVICES

def vc_max(a, b):
    return [max(x, y) for x, y in zip(a, b)]

def vc_leq(a, b):
    return all(x <= y for x, y in zip(a, b))

def merge_and_increment(local_vc, incoming_vc, my_idx):
    merged = vc_max(local_vc, incoming_vc)
    merged[my_idx] += 1
    return merged


class OrderState:
    def __init__(self, order_data):
        self.order_data = order_data
        self.local_vc = zero_vc()
        self.event_vc = {}
        self.finished = False
        self.success = False
        self.message = ""
        self.recommendations = []
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)


class TransactionVerificationService(transaction_verification_grpc.TransactionVerificationServiceServicer):
    def InitOrder(self, request, context):
        try:
            order_data = json.loads(request.order_payload_json or "{}")
            print(f"[TV] InitOrder {request.order_id} payload={order_data} vc={request.vector_clock}")
            state = OrderState(order_data)
            state.local_vc = merge_and_increment(zero_vc(), list(request.vector_clock), MY_IDX)

            with ORDER_CACHE_LOCK:
                ORDER_CACHE[request.order_id] = state

            print(f"[TV] InitOrder {request.order_id} vc={state.local_vc}")
            return transaction_verification.InitOrderResponse(acknowledged=True)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return transaction_verification.InitOrderResponse(acknowledged=False)

    def StartCheckoutFlow(self, request, context):
        order_id = request.order_id
        state = ORDER_CACHE[order_id]

        t_a = threading.Thread(target=self._run_event_a, args=(order_id,))
        t_b = threading.Thread(target=self._run_event_b, args=(order_id,))
        t_a.start()
        t_b.start()

        with state.cond:
            state.cond.wait_for(lambda: state.finished)

            return transaction_verification.StartCheckoutFlowResponse(
                success=state.success,
                message=state.message,
                vector_clock=state.local_vc,
                suggestions=[
                    transaction_verification.BookSuggestion(
                        title=item["title"],
                        author=item["author"]
                    )
                    for item in state.recommendations
                ]
            )

    def FinalizeOrder(self, request, context):
        state = ORDER_CACHE[request.order_id]
        with state.cond:
            state.local_vc = merge_and_increment(state.local_vc, list(request.vector_clock), MY_IDX)
            state.finished = True
            state.success = request.success
            state.message = request.message
            state.recommendations = [
                {"title": s.title, "author": s.author}
                for s in request.suggestions
            ]
            print(f"[TV] FinalizeOrder order={request.order_id} success={state.success} vc={state.local_vc}")
            state.cond.notify_all()

        return transaction_verification.Ack(ok=True)

    def _fail(self, order_id, message):
        state = ORDER_CACHE[order_id]
        with state.cond:
            if state.finished:
                return
            state.finished = True
            state.success = False
            state.message = message
            print(f"[TV] FAIL order={order_id} msg={message} vc={state.local_vc}")
            state.cond.notify_all()

    def _run_event_a(self, order_id):
        state = ORDER_CACHE[order_id]

        with state.cond:
            state.local_vc = merge_and_increment(state.local_vc, state.local_vc, MY_IDX)
            items = state.order_data.get("items", [])
            ok = len(items) > 0
            state.event_vc["a"] = list(state.local_vc)
            print(f"[TV] event a vc={state.local_vc}")

        if not ok:
            self._fail(order_id, "Order Declined: no items in order")
            return

        self._run_event_c(order_id, state.event_vc["a"])

    def _run_event_b(self, order_id):
        state = ORDER_CACHE[order_id]

        with state.cond:
            state.local_vc = merge_and_increment(state.local_vc, state.local_vc, MY_IDX)
            user = state.order_data.get("user", {})
            billing = state.order_data.get("billingAddress", {})
            ok = bool(user.get("name")) and bool(user.get("contact")) and bool(billing.get("street"))
            state.event_vc["b"] = list(state.local_vc)
            print(f"[TV] event b vc={state.local_vc}")

        if not ok:
            self._fail(order_id, "Order Declined: mandatory user data missing")
            return
        try:
            with grpc.insecure_channel("fraud_detection:50051") as channel:
                stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
                stub.NotifyBCompleted(
                    fraud_detection.DependencyNotificationRequest(
                        order_id=order_id,
                        event_name="b",
                        vector_clock=state.event_vc["b"]
                    )
                )
        except Exception as e:
            self._fail(order_id, f"Could not notify fraud service after b: {e}")

    def _run_event_c(self, order_id, incoming_vc):
        state = ORDER_CACHE[order_id]

        with state.cond:
            state.local_vc = merge_and_increment(state.local_vc, incoming_vc, MY_IDX)

            card = state.order_data.get("creditCard", {})
            number = str(card.get("number", ""))
            expiry = str(card.get("expirationDate", ""))
            cvv = str(card.get("cvv", ""))

            ok = (
                number.isdigit() and len(number) >= 12 and
                len(expiry) == 5 and expiry[2] == "/" and
                cvv.isdigit() and len(cvv) == 3
            )

            state.event_vc["c"] = list(state.local_vc)
            print(f"[TV] event c vc={state.local_vc}")

        if not ok:
            self._fail(order_id, "Order Declined: invalid credit card format")
            return

        try:
            with grpc.insecure_channel("fraud_detection:50051") as channel:
                stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
                stub.NotifyCCompleted(
                    fraud_detection.DependencyNotificationRequest(
                        order_id=order_id,
                        event_name="c",
                        vector_clock=state.event_vc["c"]
                    )
                )
        except Exception as e:
            self._fail(order_id, f"Could not notify fraud service after c: {e}")


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    transaction_verification_grpc.add_TransactionVerificationServiceServicer_to_server(
        TransactionVerificationService(), server
    )
    server.add_insecure_port("[::]:50052")
    server.start()
    print("Transaction service listening on 50052")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
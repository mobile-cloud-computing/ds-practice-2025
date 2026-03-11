import sys
import os
import json
import threading
import grpc
import joblib
import re
from concurrent import futures

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")

fraud_detection_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/fraud_detection'))
sys.path.insert(0, fraud_detection_grpc_path)
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc

suggestions_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/suggestions'))
sys.path.insert(0, suggestions_grpc_path)
import suggestions_pb2 as suggestions
import suggestions_pb2_grpc as suggestions_grpc

transaction_verification_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/transaction_verification'))
sys.path.insert(0, transaction_verification_grpc_path)
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc


MY_IDX = 1
ORDER_CACHE = {}
ORDER_CACHE_LOCK = threading.Lock()
TOTAL_SERVICES = 3

fraud_ai = joblib.load("./fraud_detection/ai/fraud_model.joblib")


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


def _safe_card_to_int(card_number):
    digits = re.sub(r"\D", "", str(card_number))
    if not digits:
        return 0
    # Keep feature bounded and aligned with training-style numeric signal.
    print(int(digits[-16:]))
    return int(digits[-16:])


class OrderState:
    def __init__(self, order_data):
        self.order_data = order_data
        self.local_vc = zero_vc()
        self.event_vc = {}
        self.d_started = False
        self.e_started = False
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)


class FraudDetectionService(fraud_detection_grpc.FraudDetectionServiceServicer):
    def _get_state_or_abort(self, order_id, context):
        with ORDER_CACHE_LOCK:
            state = ORDER_CACHE.get(order_id)
        if state is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Order {order_id} not initialized")
        return state

    def _remove_order(self, order_id):
        with ORDER_CACHE_LOCK:
            ORDER_CACHE.pop(order_id, None)

    def InitOrder(self, request, context):
        try:
            order_data = json.loads(request.order_payload_json or "{}")
            state = OrderState(order_data)
            state.local_vc = merge_and_increment(zero_vc(), list(request.vector_clock), MY_IDX)

            with ORDER_CACHE_LOCK:
                ORDER_CACHE[request.order_id] = state

            print(f"[FD] InitOrder {request.order_id} vc={state.local_vc}")
            return fraud_detection.InitOrderResponse(acknowledged=True)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return fraud_detection.InitOrderResponse(acknowledged=False)

    def NotifyBCompleted(self, request, context):
        state = self._get_state_or_abort(request.order_id, context)
        if state is None:
            return fraud_detection.Ack(ok=False)
        with state.cond:
            state.local_vc = merge_and_increment(state.local_vc, list(request.vector_clock), MY_IDX)
            state.event_vc["b"] = list(request.vector_clock)
            print(f"[FD] got b vc={request.vector_clock}, local={state.local_vc}")

            if not state.d_started:
                state.d_started = True
                threading.Thread(target=self._run_event_d, args=(request.order_id,)).start()

            state.cond.notify_all()

        return fraud_detection.Ack(ok=True)

    def NotifyCCompleted(self, request, context):
        state = self._get_state_or_abort(request.order_id, context)
        if state is None:
            return fraud_detection.Ack(ok=False)
        with state.cond:
            state.local_vc = merge_and_increment(state.local_vc, list(request.vector_clock), MY_IDX)
            state.event_vc["c"] = list(request.vector_clock)
            print(f"[FD] got c vc={request.vector_clock}, local={state.local_vc}")

            if not state.e_started:
                state.e_started = True
                threading.Thread(target=self._run_event_e, args=(request.order_id,)).start()

            state.cond.notify_all()

        return fraud_detection.Ack(ok=True)

    def _required_for_e(self, state):
        vc_c = state.event_vc.get("c")
        vc_d = state.event_vc.get("d")
        if vc_c is None or vc_d is None:
            return None
        return vc_max(vc_c, vc_d)

    def _run_event_d(self, order_id):
        with ORDER_CACHE_LOCK:
            state = ORDER_CACHE.get(order_id)
        if state is None:
            return

        with state.cond:
            state.cond.wait_for(lambda: "b" in state.event_vc)

            required = state.event_vc["b"]
            state.cond.wait_for(lambda: vc_leq(required, state.local_vc))

            state.local_vc = merge_and_increment(state.local_vc, required, MY_IDX)

            user = state.order_data.get("user", {})
            suspicious = "fraud" in str(user.get("name", "")).lower()

            state.event_vc["d"] = list(state.local_vc)
            print(f"[FD] event d vc={state.local_vc}")
            state.cond.notify_all()

        if suspicious:
            self._send_failure(order_id, "Order Declined: fraud detected in user data")

    def _run_event_e(self, order_id):
        with ORDER_CACHE_LOCK:
            state = ORDER_CACHE.get(order_id)
        if state is None:
            return

        with state.cond:
            state.cond.wait_for(lambda: self._required_for_e(state) is not None)

            required = self._required_for_e(state)

            # This is the important wait:
            state.cond.wait_for(lambda: vc_leq(required, state.local_vc))

            state.local_vc = merge_and_increment(state.local_vc, required, MY_IDX)

            card = state.order_data.get("creditCard", {})
            number = str(card.get("number", ""))
            amount = float(card.get("orderAmount", 0))
            prediction = fraud_ai.predict([[amount, _safe_card_to_int(number)]])[0]
            suspicious = bool(prediction)

            state.event_vc["e"] = list(state.local_vc)
            print(f"[FD] event e vc={state.local_vc}")
            state.cond.notify_all()

        if suspicious:
            self._send_failure(order_id, "Order Declined: card fraud suspected")
            return

        try:
            with grpc.insecure_channel("suggestions:50053") as channel:
                stub = suggestions_grpc.SuggestionsServiceStub(channel)
                stub.NotifyECompleted(
                    suggestions.DependencyNotificationRequest(
                        order_id=order_id,
                        event_name="e",
                        vector_clock=state.event_vc["e"]
                    )
                )
        except Exception as e:
            self._send_failure(order_id, f"Could not notify suggestions after e: {e}")

    def _send_failure(self, order_id, message):
        with ORDER_CACHE_LOCK:
            state = ORDER_CACHE.get(order_id)
        if state is None:
            return
        try:
            with grpc.insecure_channel("transaction_verification:50052") as channel:
                stub = transaction_verification_grpc.TransactionVerificationServiceStub(channel)
                stub.FinalizeOrder(
                    transaction_verification.FinalizeOrderRequest(
                        order_id=order_id,
                        success=False,
                        message=message,
                        vector_clock=state.local_vc,
                        suggestions=[]
                    )
                )
        except Exception as e:
            print(f"[FD] failed to send failure: {e}")
        finally:
            self._remove_order(order_id)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    fraud_detection_grpc.add_FraudDetectionServiceServicer_to_server(
        FraudDetectionService(), server
    )
    server.add_insecure_port("[::]:50051")
    server.start()
    print("Fraud service listening on 50051")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
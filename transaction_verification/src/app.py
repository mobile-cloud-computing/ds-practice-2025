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
FINALIZE_TIMEOUT_SECONDS = 20


# initial vector clock is [0,0,0]
def zero_vc():
    return [0] * TOTAL_SERVICES

# Utility functions for vector clock comparison and merging
def vc_max(a, b):
    return [max(x, y) for x, y in zip(a, b)]

# Returns True if vc_a <= vc_b (i.e. vc_a is causally before or concurrent with vc_b)
def vc_leq(a, b):
    return all(x <= y for x, y in zip(a, b))

# Returns a new vector clock that is the merge of local_vc and incoming_vc, and increments this service's index to reflect the new event
def merge_and_increment(local_vc, incoming_vc, my_idx):
    merged = vc_max(local_vc, incoming_vc)
    merged[my_idx] += 1
    return merged


class OrderState:
    def __init__(self, order_data):
        self.order_data = order_data
        self.local_vc = zero_vc() # vector clock tracking this service's view of the order state
        self.event_vc = {} # vector clocks for completed events, e.g. {"a": [1,0,0], "b": [2,0,0]}
        self.finished = False
        self.success = False
        self.message = ""
        self.recommendations = []
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)


class TransactionVerificationService(transaction_verification_grpc.TransactionVerificationServiceServicer):
    def _get_state_or_abort(self, order_id, context):
        # Helper to get the order state or abort the gRPC call if the order is not found
        with ORDER_CACHE_LOCK:
            state = ORDER_CACHE.get(order_id)
        if state is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Order {order_id} not initialized")
        return state

    def _remove_order(self, order_id):
        with ORDER_CACHE_LOCK:
            ORDER_CACHE.pop(order_id, None)

    # This is the main entry point to initialize the order state in the transaction verification service.
    # It is called by the orchestrator at checkout start, and sets up local state and initial vector clock.
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
            # In case of any error, we return an INTERNAL gRPC error with the exception details.
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return transaction_verification.InitOrderResponse(acknowledged=False)

    # Starts the checkout event flow for the given order.
    # Events a and b are launched in parallel, and this call waits until success/failure is finalized.
    def StartCheckoutFlow(self, request, context):
        order_id = request.order_id
        state = self._get_state_or_abort(order_id, context)
        if state is None:
            return transaction_verification.StartCheckoutFlowResponse(
                success=False,
                message="Order not initialized",
                vector_clock=zero_vc(),
                suggestions=[]
            )

        t_a = threading.Thread(target=self._run_event_a, args=(order_id,))
        t_b = threading.Thread(target=self._run_event_b, args=(order_id,))
        t_a.start()
        t_b.start()

        with state.cond:
            # Wait until some service finalizes the order, or timeout triggers local failure.
            finished = state.cond.wait_for(lambda: state.finished, timeout=FINALIZE_TIMEOUT_SECONDS)

            if not finished:
                state.finished = True
                state.success = False
                state.message = "Order Declined: checkout flow timeout"
                print(f"[TV] TIMEOUT order={order_id} vc={state.local_vc}")

            response = transaction_verification.StartCheckoutFlowResponse(
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
        self._remove_order(order_id)
        return response

    # Receives final success/failure from downstream services and wakes StartCheckoutFlow waiter.
    def FinalizeOrder(self, request, context):
        state = self._get_state_or_abort(request.order_id, context)
        if state is None:
            return transaction_verification.Ack(ok=False)
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

    # Marks the order as failed locally and notifies any waiting thread.
    def _fail(self, order_id, message):
        with ORDER_CACHE_LOCK:
            state = ORDER_CACHE.get(order_id)
        if state is None:
            return
        with state.cond:
            if state.finished:
                return
            state.finished = True
            state.success = False
            state.message = message
            print(f"[TV] FAIL order={order_id} msg={message} vc={state.local_vc}")
            state.cond.notify_all()

    # Event a: validates that the order has at least one item.
    # If successful, triggers event c; otherwise fails immediately.
    def _run_event_a(self, order_id):
        with ORDER_CACHE_LOCK:
            state = ORDER_CACHE.get(order_id)
        if state is None:
            return

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

    # Event b: validates mandatory user and billing fields.
    # On success, notifies fraud detection that b completed.
    def _run_event_b(self, order_id):
        with ORDER_CACHE_LOCK:
            state = ORDER_CACHE.get(order_id)
        if state is None:
            return

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

    # Event c: validates basic card format, depends on event a's vector clock.
    # On success, notifies fraud detection that c completed.
    def _run_event_c(self, order_id, incoming_vc):
        with ORDER_CACHE_LOCK:
            state = ORDER_CACHE.get(order_id)
        if state is None:
            return

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
    # Bootstraps and starts the gRPC server for this service.
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
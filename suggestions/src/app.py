import sys
import os
import json
import threading
import grpc
from concurrent import futures

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")

suggestions_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/suggestions'))
sys.path.insert(0, suggestions_grpc_path)
import suggestions_pb2 as suggestions
import suggestions_pb2_grpc as suggestions_grpc

transaction_verification_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/transaction_verification'))
sys.path.insert(0, transaction_verification_grpc_path)
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc


MY_IDX = 2
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
        self.f_started = False
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)


class SuggestionsService(suggestions_grpc.SuggestionsServiceServicer):
    def InitOrder(self, request, context):
        try:
            order_data = json.loads(request.order_payload_json or "{}")
            state = OrderState(order_data)
            state.local_vc = merge_and_increment(zero_vc(), list(request.vector_clock), MY_IDX)

            with ORDER_CACHE_LOCK:
                ORDER_CACHE[request.order_id] = state

            print(f"[SG] InitOrder {request.order_id} vc={state.local_vc}")
            return suggestions.InitOrderResponse(acknowledged=True)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return suggestions.InitOrderResponse(acknowledged=False)

    def NotifyECompleted(self, request, context):
        state = ORDER_CACHE[request.order_id]
        with state.cond:
            state.local_vc = merge_and_increment(state.local_vc, list(request.vector_clock), MY_IDX)
            state.event_vc["e"] = list(request.vector_clock)
            print(f"[SG] got e vc={request.vector_clock}, local={state.local_vc}")

            if not state.f_started:
                state.f_started = True
                threading.Thread(target=self._run_event_f, args=(request.order_id,)).start()

            state.cond.notify_all()

        return suggestions.Ack(ok=True)

    def _run_event_f(self, order_id):
        state = ORDER_CACHE[order_id]
        #TODO AI siia
        with state.cond:
            state.cond.wait_for(lambda: "e" in state.event_vc)

            required = state.event_vc["e"]
            state.cond.wait_for(lambda: vc_leq(required, state.local_vc))

            state.local_vc = merge_and_increment(state.local_vc, required, MY_IDX)

            recommendations = [
                {"title": "Dune", "author": "Frank Herbert"},
                {"title": "Foundation", "author": "Isaac Asimov"},
                {"title": "1984", "author": "George Orwell"},
            ]

            state.event_vc["f"] = list(state.local_vc)
            print(f"[SG] event f vc={state.local_vc}")

        self._send_success(order_id, recommendations, state.event_vc["f"])

    def _send_success(self, order_id, recommendations, final_vc):
        try:
            with grpc.insecure_channel("transaction_verification:50052") as channel:
                stub = transaction_verification_grpc.TransactionVerificationServiceStub(channel)
                stub.FinalizeOrder(
                    transaction_verification.FinalizeOrderRequest(
                        order_id=order_id,
                        success=True,
                        message="Order Approved",
                        vector_clock=final_vc,
                        suggestions=[
                            transaction_verification.BookSuggestion(
                                title=item["title"],
                                author=item["author"]
                            )
                            for item in recommendations
                        ]
                    )
                )
        except Exception as e:
            print(f"[SG] failed to send success: {e}")


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    suggestions_grpc.add_SuggestionsServiceServicer_to_server(
        SuggestionsService(), server
    )
    server.add_insecure_port("[::]:50053")
    server.start()
    print("Suggestions service listening on 50053")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
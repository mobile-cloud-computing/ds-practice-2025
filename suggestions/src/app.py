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


def _generate_ai_recommendations(order_data):
    try:
        import google.genai as genai

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return None

        user_id = order_data.get("userId", "anonymous")
        selected_books = [str(item.get("name", "")).strip() for item in order_data.get("items", []) if str(item.get("name", "")).strip()]
        if not selected_books:
            selected_books = [
                "Harry Potter and the Philosopher's Stone by J.K. Rowling",
                "The Hobbit by J.R.R. Tolkien",
            ]

        selected_titles = [book.split(" by ", 1)[0].strip().lower() for book in selected_books]
        input_prompt = (
            "You are a bookstore recommendation assistant. "
            f"User id: {user_id}. "
            f"Selected books: {selected_books}. "
            "Suggest exactly 3 additional books related to selected books. "
            "Rules: suggestions must be different from selected books. "
            "Output strictly 3 lines, each line in exact format: Title by Author. "
            "No numbering, no bullets, no extra text."
        )

        client = genai.Client(api_key=api_key)
        response_ai = client.models.generate_content(
            model="gemini-2.5-flash-lite", contents=input_prompt
        )

        parsed = []
        for line in (response_ai.text or "").split("\n"):
            entry = line.strip()
            if not entry:
                continue
            if " by " in entry:
                title, author = entry.split(" by ", 1)
                title = title.strip()
                author = author.strip()
            else:
                title = entry.strip()
                author = "Unknown"

            if not title or title.lower() in selected_titles:
                continue
            candidate = {"title": title, "author": author}
            if candidate not in parsed:
                parsed.append(candidate)
            if len(parsed) >= 3:
                break

        return parsed if parsed else None
    except Exception:
        return None


class OrderState:
    def __init__(self, order_data):
        self.order_data = order_data
        self.local_vc = zero_vc() # vector clock tracking this service's view of the order state
        self.event_vc = {} # vector clocks for completed events, e.g. {"e": [1,3,0], "f": [1,3,1]}
        self.f_started = False
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)


class SuggestionsService(suggestions_grpc.SuggestionsServiceServicer):
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

    # This is the main entry point to initialize the order state in the suggestions service.
    # It is called by the orchestrator at checkout start, and sets up local state and initial vector clock.
    def InitOrder(self, request, context):
        try:
            order_data = json.loads(request.order_payload_json or "{}")
            state = OrderState(order_data)
            state.local_vc = vc_max(zero_vc(), list(request.vector_clock)) # initialize local vc to the merge of the incoming vc and zero, to capture any causally prior events that we should be aware of at initialization

            with ORDER_CACHE_LOCK:
                ORDER_CACHE[request.order_id] = state

            print(f"[SG] InitOrder {request.order_id} vc={state.local_vc}")
            return suggestions.InitOrderResponse(acknowledged=True)
        except Exception as e:
            # In case of any error, we return an INTERNAL gRPC error with the exception details.
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return suggestions.InitOrderResponse(acknowledged=False)

    # notify that e completed, with the vector clock from e. We update our local vector clock, record
    # the event vc for e, and start event f once.
    def NotifyCardFraudCheckCompleted(self, request, context):
        state = self._get_state_or_abort(request.order_id, context)
        if state is None:
            return suggestions.Ack(ok=False)
        with state.cond:
            #state.local_vc = merge_and_increment(state.local_vc, list(request.vector_clock), MY_IDX)
            # only merge
            state.local_vc = vc_max(state.local_vc, list(request.vector_clock))
            state.event_vc["e"] = list(request.vector_clock)
            print(f"[SG] got e vc={request.vector_clock}, local={state.local_vc}")

            if not state.f_started:
                state.f_started = True
                threading.Thread(target=self._generate_book_suggestions, args=(request.order_id,)).start()

            state.cond.notify_all()

        return suggestions.Ack(ok=True)

    # Final cleanup event broadcast by orchestrator.
    # Service only clears cached order state if local_vc <= final_vector_clock.
    def CleanupOrder(self, request, context):
        with ORDER_CACHE_LOCK:
            state = ORDER_CACHE.get(request.order_id)

        if state is None:
            return suggestions.CleanupOrderResponse(
                cleaned=True,
                vc_valid=True,
                message="Order not found (already cleaned or never initialized)",
                local_vector_clock=zero_vc(),
            )

        final_vc = list(request.final_vector_clock)
        with state.cond:
            local_vc = list(state.local_vc)
            is_valid = vc_leq(local_vc, final_vc)

        if is_valid:
            self._remove_order(request.order_id)
            print(f"[SG] CleanupOrder order={request.order_id} local_vc={local_vc} final_vc={final_vc} status=cleaned")
            return suggestions.CleanupOrderResponse(
                cleaned=True,
                vc_valid=True,
                message="Cleanup successful",
                local_vector_clock=local_vc,
            )

        print(f"[SG] CleanupOrder order={request.order_id} local_vc={local_vc} final_vc={final_vc} status=rejected")
        return suggestions.CleanupOrderResponse(
            cleaned=False,
            vc_valid=False,
            message="Cleanup rejected: local vector clock is not <= final vector clock",
            local_vector_clock=local_vc,
        )

    # Event f: depends on e and generates final book recommendations.
    # Once complete, sends FinalizeOrder(success=True) back to transaction verification.
    def _generate_book_suggestions(self, order_id):
        with ORDER_CACHE_LOCK:
            state = ORDER_CACHE.get(order_id)
        if state is None:
            return

        with state.cond:
            state.cond.wait_for(lambda: "e" in state.event_vc)

            required = state.event_vc["e"]
            state.cond.wait_for(lambda: vc_leq(required, state.local_vc))

            state.local_vc = merge_and_increment(state.local_vc, required, MY_IDX)

            recommendations = _generate_ai_recommendations(state.order_data) or [
                {"title": "Dune", "author": "Frank Herbert"},
                {"title": "Foundation", "author": "Isaac Asimov"},
                {"title": "1984", "author": "George Orwell"},
            ]

            state.event_vc["f"] = list(state.local_vc)
            print(f"[SG] event f vc={state.local_vc}")

        self._send_success(order_id, recommendations, state.event_vc["f"])

    # Sends successful completion with recommendations and final vector clock.
    def _send_success(self, order_id, recommendations, final_vc):
        try:
            with grpc.insecure_channel("transaction_verification:50052") as channel:
                stub = transaction_verification_grpc.TransactionVerificationServiceStub(channel)
                # We call FinalizeOrder on the transaction verification service to indicate that the checkout flow has completed successfully, 
                # and we include the final vector clock and book recommendations in this call. This allows the transaction verification service to return the final response to the user with the recommendations included.
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
    # Bootstraps and starts the gRPC server for this service.
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
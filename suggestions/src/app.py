import sys
import os
import threading
from concurrent import futures

FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
suggestions_grpc_path = os.path.abspath(
    os.path.join(FILE, "../../../utils/pb/suggestions")
)
sys.path.insert(0, suggestions_grpc_path)

import grpc
import suggestions_pb2 as suggestions
import suggestions_pb2_grpc as suggestions_grpc

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


static_books = [
    {"bookId": "101", "title": "Distributed Systems Basics", "author": "A. Author"},
    {
        "bookId": "102",
        "title": "Designing Data-Intensive Applications",
        "author": "Martin Kleppmann",
    },
    {"bookId": "103", "title": "Clean Code", "author": "Robert C. Martin"},
    {"bookId": "104", "title": "The Pragmatic Programmer", "author": "Andrew Hunt"},
]


def execute_event_f(order_id):
    order_data = order_cache.get(order_id)
    if not order_data:
        return None

    with cache_lock:
        vector_clocks[order_id]["suggestions"] += 1

    item_count = order_data.get("item_count", 0)
    chosen = static_books[:2] if item_count > 0 else []

    print(f"Event f (generate_suggestions) for order {order_id}: {len(chosen)} books")
    return {"books": chosen}


def process_order(order_id):
    order_data = order_cache.get(order_id)
    if not order_data:
        return None

    with cache_lock:
        vector_clocks[order_id]["suggestions"] += 1

    chosen = static_books[:2] if order_data["item_count"] > 0 else []

    result = {"books": chosen, "vector_clock": vector_clocks[order_id].copy()}

    print(f"Suggestions processed for order {order_id}: {len(chosen)} books")
    return result


class SuggestionsService(suggestions_grpc.SuggestionsServiceServicer):
    def GetSuggestions(self, request, context):
        order_id = request.order_id if hasattr(request, "order_id") else ""
        print(f"Received suggestions request for order: {order_id}")

        with cache_lock:
            order_cache[order_id] = {
                "user_name": request.user_name,
                "item_count": request.item_count,
            }
            if order_id not in vector_clocks:
                vector_clocks[order_id] = initialize_vector_clock(order_id)
            vector_clocks[order_id]["suggestions"] = 0

        print(
            f"Order {order_id} cached in suggestions. Vector clock: {vector_clocks.get(order_id)}"
        )

        response = suggestions.SuggestionsResponse()
        return response

    def TriggerSuggestions(self, request, context):
        order_id = request.order_id
        event_type = request.event_type if hasattr(request, "event_type") else "all"
        print(f"Triggering suggestions for order {order_id}, event: {event_type}")

        with cache_lock:
            if order_id not in vector_clocks:
                vector_clocks[order_id] = initialize_vector_clock(order_id)
            vc = vector_clocks.get(order_id, {})

        if event_type == "all":
            result = process_order(order_id)
            response = suggestions.SuggestionsResponse()
            if result:
                with cache_lock:
                    if order_id in order_cache:
                        del order_cache[order_id]
                for book in result["books"]:
                    b = response.books.add()
                    b.bookId = book["bookId"]
                    b.title = book["title"]
                    b.author = book["author"]
            print(
                f"[VC] Suggestions for order {order_id}: VC={vector_clocks.get(order_id, {})}"
            )
            return response
        elif event_type == "event_f":
            # Event F depends on Event E (check_card_fraud)
            can_proceed, msg = check_event_dependencies(vc, ["fd_event_e"])
            if not can_proceed:
                response = suggestions.SuggestionsResponse()
                response.failed = True
                return response
            result = execute_event_f(order_id)
            response = suggestions.SuggestionsResponse()
            if result:
                with cache_lock:
                    if order_id in order_cache:
                        del order_cache[order_id]
                for book in result["books"]:
                    b = response.books.add()
                    b.bookId = book["bookId"]
                    b.title = book["title"]
                    b.author = book["author"]
            print(
                f"[VC] Event f for order {order_id}: VC suggestions={vector_clocks.get(order_id, {}).get('suggestions', 0)}"
            )
            return response

    def GetVectorClock(self, request, context):
        order_id = request.order_id
        with cache_lock:
            vc = vector_clocks.get(order_id, {})

        response = suggestions.VectorClockResponse()
        response.suggestions = vc.get("suggestions", 0)
        response.fraud_detection = vc.get("fraud_detection", 0)
        response.fd_event_d = vc.get("fd_event_d", 0)
        response.fd_event_e = vc.get("fd_event_e", 0)
        response.transaction_verification = vc.get("transaction_verification", 0)
        response.tv_event_a = vc.get("tv_event_a", 0)
        response.tv_event_b = vc.get("tv_event_b", 0)
        response.tv_event_c = vc.get("tv_event_c", 0)
        return response

    def ClearOrder(self, request, context):
        order_id = request.order_id
        print(f"Received ClearOrder request for order: {order_id}")

        with cache_lock:
            vc = vector_clocks.get(order_id, {})

            local_vc_s = vc.get("suggestions", 0)

            expected_vc_s = request.final_vc_suggestions

            if local_vc_s <= expected_vc_s:
                if order_id in order_cache:
                    del order_cache[order_id]
                if order_id in vector_clocks:
                    del vector_clocks[order_id]
                print(f"Order {order_id} cleared successfully in suggestions")
                response = suggestions.ClearOrderResponse()
                response.success = True
                response.message = "Order cleared successfully"
                return response
            else:
                print(f"Vector clock mismatch for order {order_id}. Local VC: {vc}")
                response = suggestions.ClearOrderResponse()
                response.success = False
                response.message = f"Vector clock mismatch. Local: s={local_vc_s}. Expected: s={expected_vc_s}"
                return response


def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    suggestions_grpc.add_SuggestionsServiceServicer_to_server(
        SuggestionsService(), server
    )

    port = "50053"
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Suggestions server started. Listening on port 50053.")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

import os
import sys
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


SERVICE_INDEX = 2  # [transaction_verification, fraud_detection, suggestions]

orders = {}
orders_lock = threading.Lock()

STATIC_BOOKS = [
    {
        "bookId": "101",
        "title": "Distributed Systems Basics",
        "author": "A. Author",
    },
    {
        "bookId": "102",
        "title": "Designing Data-Intensive Applications",
        "author": "Martin Kleppmann",
    },
    {
        "bookId": "103",
        "title": "Clean Code",
        "author": "Robert C. Martin",
    },
    {
        "bookId": "104",
        "title": "The Pragmatic Programmer",
        "author": "Andrew Hunt",
    },
]


def merge_vc(local_vc, incoming_vc):
    return [max(a, b) for a, b in zip(local_vc, incoming_vc)]


def tick(vc, idx):
    vc[idx] += 1
    return vc


def get_order_state(order_id: str):
    with orders_lock:
        return orders.get(order_id)


class SuggestionsService(suggestions_grpc.SuggestionsServiceServicer):
    def InitOrder(self, request, context):
        order = request.order

        with orders_lock:
            orders[order.order_id] = {
                "order": order,
                "vc": [0, 0, 0],
                "books": [],
            }

        print(f"[SUG] order={order.order_id} event=InitOrder vc={[0, 0, 0]} success=True")

        return suggestions.EventResponse(
            success=True,
            message="Suggestions service initialized order.",
            vc=suggestions.VectorClock(values=[0, 0, 0]),
        )

    def PrecomputeSuggestions(self, request, context):
        state = get_order_state(request.order_id)
        if state is None:
            return suggestions.EventResponse(
                success=False,
                message="Order not found in suggestions service.",
                vc=suggestions.VectorClock(values=[0, 0, 0]),
            )

        incoming_vc = list(request.vc.values)
        local_vc = state["vc"]
        vc = merge_vc(local_vc, incoming_vc)
        vc = tick(vc, SERVICE_INDEX)
        state["vc"] = vc

        item_count = state["order"].item_count

        if item_count > 0:
            state["books"] = STATIC_BOOKS[:2]
            success = True
            message = "Suggestions prepared."
        else:
            state["books"] = []
            success = False
            message = "Cannot prepare suggestions for empty order."

        print(
            f"[SUG] order={request.order_id} event=PrecomputeSuggestions "
            f"vc={vc} success={success} prepared_books={len(state['books'])}"
        )

        return suggestions.EventResponse(
            success=success,
            message=message,
            vc=suggestions.VectorClock(values=vc),
        )

    def FinalizeSuggestions(self, request, context):
        state = get_order_state(request.order_id)
        if state is None:
            return suggestions.SuggestionsEventResponse(
                success=False,
                message="Order not found in suggestions service.",
                vc=suggestions.VectorClock(values=[0, 0, 0]),
                books=[],
            )

        incoming_vc = list(request.vc.values)
        local_vc = state["vc"]
        vc = merge_vc(local_vc, incoming_vc)
        vc = tick(vc, SERVICE_INDEX)
        state["vc"] = vc

        prepared_books = state["books"]
        success = len(prepared_books) > 0
        message = (
            "Suggestions finalized."
            if success
            else "No prepared suggestions available."
        )

        response = suggestions.SuggestionsEventResponse(
            success=success,
            message=message,
            vc=suggestions.VectorClock(values=vc),
        )

        for book in prepared_books:
            b = response.books.add()
            b.bookId = book["bookId"]
            b.title = book["title"]
            b.author = book["author"]

        print(
            f"[SUG] order={request.order_id} event=FinalizeSuggestions "
            f"vc={vc} success={success} returned_books={len(prepared_books)}"
        )

        return response

    def ClearOrder(self, request, context):
        order_id = request.order_id
        final_vc = list(request.final_vc.values)

        with orders_lock:
            state = orders.get(order_id)

            if state is None:
                return suggestions.EventResponse(
                    success=False,
                    message="Order not found in suggestions service.",
                    vc=suggestions.VectorClock(values=[0, 0, 0]),
                )

            local_vc = state["vc"]
            can_clear = all(a <= b for a, b in zip(local_vc, final_vc))

            if can_clear:
                del orders[order_id]

        success = can_clear
        message = (
            "Order cleared from suggestions service."
            if success
            else "Cannot clear order: local VC is ahead of final VC."
        )

        print(
            f"[SUG] order={order_id} event=ClearOrder "
            f"local_vc={local_vc} final_vc={final_vc} success={success}"
        )

        return suggestions.EventResponse(
            success=success,
            message=message,
            vc=suggestions.VectorClock(values=final_vc),
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    suggestions_grpc.add_SuggestionsServiceServicer_to_server(
        SuggestionsService(), server
    )

    port = "50053"
    server.add_insecure_port("[::]:" + port)
    server.start()
    print(f"Suggestions server started. Listening on port {port}.")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
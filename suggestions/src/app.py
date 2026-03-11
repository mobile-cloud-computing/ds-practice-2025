import sys
import os

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
sg_grpc_path = os.path.abspath(os.path.join(FILE, "../../../utils/pb/suggestions"))
sys.path.insert(0, sg_grpc_path)
import suggestions_pb2 as sg_pb2
import suggestions_pb2_grpc as sg_grpc

project_root = os.path.abspath(os.path.join(FILE, "../../.."))
sys.path.insert(0, project_root)
from utils.vector_clock import (
    EVENT_TRACE_METADATA_KEY,
    ORDER_ID_METADATA_KEY,
    VECTOR_CLOCK_METADATA_KEY,
    deserialize_clock,
    merge_clocks,
    metadata_to_dict,
    new_clock,
    record_event,
    serialize_clock,
    serialize_trace,
    tick,
)

import logging
import grpc
from concurrent import futures
from threading import Lock
from google import genai

logging.basicConfig(level=logging.INFO)

# Configure Google AI
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
order_cache = {}
order_cache_lock = Lock()


class SuggestionsService(sg_grpc.SuggestionsServiceServicer):
    @staticmethod
    def _log_clock(order_id, event, clock):
        logging.info(
            "Order %s suggestions %s vector clock %s",
            order_id,
            event,
            serialize_clock(clock),
        )

    def _respond(self, context, trace, clock, suggested_books):
        clock = tick(clock, "suggestions")
        record_event(trace, clock, "suggestions", "get_suggestions_completed")
        self._log_clock(
            metadata_to_dict(context.invocation_metadata()).get(ORDER_ID_METADATA_KEY, ""),
            "respond",
            clock,
        )
        context.set_trailing_metadata(
            (
                (VECTOR_CLOCK_METADATA_KEY, serialize_clock(clock)),
                (EVENT_TRACE_METADATA_KEY, serialize_trace(trace)),
            )
        )
        return sg_pb2.SuggestionsResponse(books=suggested_books)

    def InitializeSuggestionsOrder(self, request, context):
        metadata = metadata_to_dict(context.invocation_metadata())
        order_id = metadata.get(ORDER_ID_METADATA_KEY, "")
        incoming_clock = deserialize_clock(metadata.get(VECTOR_CLOCK_METADATA_KEY))
        with order_cache_lock:
            cached_order = order_cache.get(order_id)

            if not cached_order:
                clock = tick(merge_clocks(new_clock(), incoming_clock), "suggestions")
                self._log_clock(order_id, "initialize", clock)
                trace = []
                record_event(trace, clock, "suggestions", "suggestions_order_cached")
                order_cache[order_id] = {
                    "items": [
                        {"name": item.name, "quantity": item.quantity}
                        for item in request.items
                    ],
                    "clock": clock,
                    "trace": trace,
                }
                logging.info("Cached suggestions order %s", order_id)
                return self._respond(context, trace, clock, [])

        clock = tick(merge_clocks(cached_order["clock"], incoming_clock), "suggestions")
        trace = list(cached_order["trace"])
        self._log_clock(order_id, "execute", clock)

        record_event(trace, clock, "suggestions", "get_suggestions_request_received")

        items = cached_order["items"]
        logging.info(f"Getting suggestions for {len(items)} items")

        items_str = ", ".join([f"{item['name']} (qty: {item['quantity']})" for item in items])

        prompt = f"Based on the user's purchased books: {items_str}, suggest 2 relevant books. For each book, provide title and author. Respond in the format: 1. Title: [title], Author: [author] 2. Title: [title], Author: [author]"
        response = client.models.generate_content(model='gemma-3-27b-it', contents=prompt)
        result = response.text.strip()

        # Parse the response
        suggested_books = []
        lines = result.split('\n')
        for line in lines:
            if line.startswith(('1.', '2.')):
                parts = line.split('Title:')[1].split('Author:')
                if len(parts) == 2:
                    title = parts[0].strip().strip(',')
                    author = parts[1].strip()
                    book_id = str(hash(title + author))[:6]  # Simple ID
                    suggested_books.append(sg_pb2.SuggestedBook(
                        bookId=book_id, title=title, author=author
                    ))

        logging.info(f"Returning {len(suggested_books)} suggestions")
        return self._respond(context, trace, clock, suggested_books)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    sg_grpc.add_SuggestionsServiceServicer_to_server(SuggestionsService(), server)
    port = "50053"
    server.add_insecure_port("[::]:" + port)
    server.start()
    logging.info(f"Suggestions service started on port {port}")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

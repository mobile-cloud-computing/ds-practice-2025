import sys
import os

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
    clock_le,
    deserialize_clock,
    merge_clocks,
    metadata_to_dict,
    new_clock,
    process_event,
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

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
order_cache = {}
order_cache_lock = Lock()

FALLBACK_SUGGESTIONS = [
    sg_pb2.SuggestedBook(bookId="s1", title="Designing Data-Intensive Applications", author="Martin Kleppmann"),
    sg_pb2.SuggestedBook(bookId="s2", title="Understanding Distributed Systems", author="Roberto Vitillo"),
]


def _set_trailing(context, clock, trace):
    context.set_trailing_metadata((
        (VECTOR_CLOCK_METADATA_KEY, serialize_clock(clock)),
        (EVENT_TRACE_METADATA_KEY, serialize_trace(trace)),
    ))


class SuggestionsService(sg_grpc.SuggestionsServiceServicer):

    @staticmethod
    def _log(order_id, event, clock):
        logging.info(
            "[%s] suggestions %s — VC: %s",
            order_id, event, serialize_clock(clock),
        )

    def _get_order(self, order_id, context):
        with order_cache_lock:
            order = order_cache.get(order_id)
        if not order:
            context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                f"Suggestions order {order_id} not initialized",
            )
        return order

    # ── Init (cache only) ──

    def InitializeSuggestionsOrder(self, request, context):
        metadata = metadata_to_dict(context.invocation_metadata())
        order_id = metadata.get(ORDER_ID_METADATA_KEY, "")
        incoming_clock = deserialize_clock(metadata.get(VECTOR_CLOCK_METADATA_KEY))

        clock = tick(merge_clocks(new_clock(), incoming_clock), "suggestions")
        self._log(order_id, "initialize", clock)

        cached = {
            "items": [
                {"name": item.name, "quantity": item.quantity}
                for item in request.items
            ],
            "clock": clock,
            "trace": [],
            "completed_events": set(),
        }
        record_event(cached["trace"], clock, "suggestions", "suggestions_order_cached")

        with order_cache_lock:
            order_cache[order_id] = cached

        logging.info("Cached suggestions order %s", order_id)
        _set_trailing(context, clock, cached["trace"])
        return sg_pb2.SuggestionsResponse(books=[])

    # ── Event f: generate suggestions ──

    def GenerateSuggestions(self, request, context):
        metadata = metadata_to_dict(context.invocation_metadata())
        order_id = metadata.get(ORDER_ID_METADATA_KEY, "")
        incoming_clock = deserialize_clock(metadata.get(VECTOR_CLOCK_METADATA_KEY))
        order = self._get_order(order_id, context)

        clock = process_event(order, "suggestions", "generate_suggestions", incoming_clock)
        self._log(order_id, "generate_suggestions", clock)
        order["completed_events"].add("f")

        items = order["items"]
        logging.info("[%s] Generating suggestions for %d items", order_id, len(items))

        suggested_books = []
        try:
            items_str = ", ".join(
                f"{item['name']} (qty: {item['quantity']})" for item in items
            )
            prompt = (
                f"Based on the user's purchased books: {items_str}, suggest 2 relevant books. "
                "For each book, provide title and author. "
                "Respond in the format: 1. Title: [title], Author: [author] "
                "2. Title: [title], Author: [author]"
            )
            response = client.models.generate_content(
                model="gemma-3-27b-it", contents=prompt
            )
            result = response.text.strip()
            for line in result.split("\n"):
                if line.startswith(("1.", "2.")) and "Title:" in line and "Author:" in line:
                    parts = line.split("Title:")[1].split("Author:")
                    if len(parts) == 2:
                        title = parts[0].strip().strip(",")
                        author = parts[1].strip()
                        book_id = str(hash(title + author))[:6]
                        suggested_books.append(
                            sg_pb2.SuggestedBook(bookId=book_id, title=title, author=author)
                        )
        except Exception as e:
            logging.warning("[%s] GenAI suggestions failed, using fallback: %s", order_id, e)
            suggested_books = list(FALLBACK_SUGGESTIONS)

        if not suggested_books:
            suggested_books = list(FALLBACK_SUGGESTIONS)

        logging.info("[%s] Returning %d suggestions", order_id, len(suggested_books))
        _set_trailing(context, clock, list(order["trace"]))
        return sg_pb2.SuggestionsResponse(books=suggested_books)

    # ── Clear (bonus) ──

    def ClearSuggestionsOrder(self, request, context):
        metadata = metadata_to_dict(context.invocation_metadata())
        order_id = metadata.get(ORDER_ID_METADATA_KEY, "")
        incoming_clock = deserialize_clock(metadata.get(VECTOR_CLOCK_METADATA_KEY))

        with order_cache_lock:
            order = order_cache.get(order_id)
            if not order:
                logging.info("Clear: suggestions order %s already cleared", order_id)
                _set_trailing(context, incoming_clock, [])
                return sg_pb2.SuggestionsResponse(books=[])

            if clock_le(order["clock"], incoming_clock):
                del order_cache[order_id]
                logging.info("[%s] Cleared suggestions order data", order_id)
                _set_trailing(context, incoming_clock, [])
                return sg_pb2.SuggestionsResponse(books=[])
            else:
                logging.error(
                    "[%s] Clear rejected: local VC %s NOT <= final VC %s",
                    order_id, serialize_clock(order["clock"]), serialize_clock(incoming_clock),
                )
                _set_trailing(context, order["clock"], [])
                return sg_pb2.SuggestionsResponse(books=[])


def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    sg_grpc.add_SuggestionsServiceServicer_to_server(SuggestionsService(), server)
    port = "50053"
    server.add_insecure_port("[::]:" + port)
    server.start()
    logging.info("Suggestions service started on port %s", port)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

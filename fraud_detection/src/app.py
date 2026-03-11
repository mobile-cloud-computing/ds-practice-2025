import sys
import os

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
fd_grpc_path = os.path.abspath(os.path.join(FILE, "../../../utils/pb/fraud_detection"))
sys.path.insert(0, fd_grpc_path)
import fraud_detection_pb2 as fd_pb2
import fraud_detection_pb2_grpc as fd_grpc

sg_grpc_path = os.path.abspath(os.path.join(FILE, "../../../utils/pb/suggestions"))
sys.path.insert(0, sg_grpc_path)
import suggestions_pb2 as sg_pb2
import suggestions_pb2_grpc as sg_grpc

project_root = os.path.abspath(os.path.join(FILE, "../../.."))
sys.path.insert(0, project_root)
from utils.vector_clock import (
    EVENT_TRACE_METADATA_KEY,
    ORDER_ID_METADATA_KEY,
    SUGGESTED_BOOKS_METADATA_KEY,
    VECTOR_CLOCK_METADATA_KEY,
    deserialize_clock,
    deserialize_trace,
    merge_clocks,
    metadata_to_dict,
    new_clock,
    record_event,
    serialize_clock,
    serialize_trace,
    tick,
)

import json
import logging
import grpc
from concurrent import futures
from threading import Lock
from google import genai
import time

logging.basicConfig(level=logging.INFO)

# Configure Google AI
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
order_cache = {}
order_cache_lock = Lock()


class FraudDetectionService(fd_grpc.FraudDetectionServiceServicer):
    @staticmethod
    def _log_clock(order_id, event, clock):
        logging.info(
            "Order %s fraud_detection %s vector clock %s",
            order_id,
            event,
            serialize_clock(clock),
        )

    def _respond(self, context, trace, clock, is_fraud, extra_metadata=()):
        clock = tick(clock, "fraud_detection")
        record_event(trace, clock, "fraud_detection", "check_fraud_completed")
        self._log_clock(
            metadata_to_dict(context.invocation_metadata()).get(ORDER_ID_METADATA_KEY, ""),
            "respond",
            clock,
        )
        metadata = [
            (VECTOR_CLOCK_METADATA_KEY, serialize_clock(clock)),
            (EVENT_TRACE_METADATA_KEY, serialize_trace(trace)),
        ]
        metadata.extend(extra_metadata)
        context.set_trailing_metadata(tuple(metadata))
        return fd_pb2.FraudResponse(is_fraud=is_fraud)

    def _execute_suggestions(self, order_id, clock):
        deadline = time.monotonic() + 5
        while True:
            try:
                with grpc.insecure_channel("suggestions:50053") as channel:
                    stub = sg_grpc.SuggestionsServiceStub(channel)
                    response, call = stub.InitializeSuggestionsOrder.with_call(
                        sg_pb2.SuggestionsRequest(items=[]),
                        metadata=(
                            (ORDER_ID_METADATA_KEY, order_id),
                            (VECTOR_CLOCK_METADATA_KEY, serialize_clock(clock)),
                        ),
                    )
                metadata = metadata_to_dict(call.trailing_metadata())
                books = [
                    {"bookId": book.bookId, "title": book.title, "author": book.author}
                    for book in response.books
                ]
                return (
                    books,
                    deserialize_clock(metadata.get(VECTOR_CLOCK_METADATA_KEY)),
                    deserialize_trace(metadata.get(EVENT_TRACE_METADATA_KEY)),
                )
            except grpc.RpcError as exc:
                if (
                    exc.code() == grpc.StatusCode.FAILED_PRECONDITION
                    and time.monotonic() < deadline
                ):
                    time.sleep(0.05)
                    continue
                raise

    def InitializeFraudOrder(self, request, context):
        metadata = metadata_to_dict(context.invocation_metadata())
        order_id = metadata.get(ORDER_ID_METADATA_KEY, "")
        incoming_clock = deserialize_clock(metadata.get(VECTOR_CLOCK_METADATA_KEY))
        with order_cache_lock:
            cached_order = order_cache.get(order_id)

            if not cached_order:
                clock = tick(merge_clocks(new_clock(), incoming_clock), "fraud_detection")
                self._log_clock(order_id, "initialize", clock)
                trace = []
                record_event(trace, clock, "fraud_detection", "fraud_order_cached")
                order_cache[order_id] = {
                    "card_number": request.card_number,
                    "order_amount": request.order_amount,
                    "clock": clock,
                    "trace": trace,
                }
                logging.info("Cached fraud order %s", order_id)
                return self._respond(context, trace, clock, False)

        clock = tick(
            merge_clocks(cached_order["clock"], incoming_clock),
            "fraud_detection",
        )
        trace = list(cached_order["trace"])
        self._log_clock(order_id, "execute", clock)

        record_event(trace, clock, "fraud_detection", "check_fraud_request_received")

        card_number = cached_order["card_number"]
        order_amount = cached_order["order_amount"]

        logging.info(
            f"Checking fraud for card ending in {card_number[-4:]} with amount {order_amount}"
        )

        prompt = f"Analyze this transaction for fraud. Card number: {card_number}, Quantity of items: {order_amount}. Respond with only 'not fraud' if it is not fraudulent, otherwise respond with 'fraud' and the reason."
        response = client.models.generate_content(
            model="gemma-3-27b-it", contents=prompt
        )
        result = response.text.strip().lower()
        logging.info(f"AI response: {result}")

        is_fraud = (result != "not fraud")
        if card_number == "4111111111111111":
            is_fraud = False  # Override for testing with a known card number
            logging.info("Override: Card number is a known test card, marking as not fraud.")

        if not is_fraud:
            downstream_clock = tick(clock, "fraud_detection")
            record_event(
                trace,
                downstream_clock,
                "fraud_detection",
                "dispatch_suggestions",
            )
            books, suggestions_clock, suggestions_trace = self._execute_suggestions(
                order_id, downstream_clock
            )
            trace.extend(suggestions_trace)
            clock = merge_clocks(downstream_clock, suggestions_clock)
            return self._respond(
                context,
                trace,
                clock,
                False,
                extra_metadata=((SUGGESTED_BOOKS_METADATA_KEY, json.dumps(books)),),
            )

        logging.info(f"Fraud check result: is_fraud={is_fraud}")
        return self._respond(context, trace, clock, is_fraud)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    fd_grpc.add_FraudDetectionServiceServicer_to_server(FraudDetectionService(), server)
    port = "50051"
    server.add_insecure_port("[::]:" + port)
    server.start()
    logging.info(f"Fraud Detection service started on port {port}")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

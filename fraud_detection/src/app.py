import sys
import os

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
    clock_le,
    deserialize_clock,
    deserialize_trace,
    merge_clocks,
    metadata_to_dict,
    new_clock,
    process_event,
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

logging.basicConfig(level=logging.INFO)

order_cache = {}
order_cache_lock = Lock()


def _order_metadata(order_id, clock):
    return (
        (ORDER_ID_METADATA_KEY, order_id),
        (VECTOR_CLOCK_METADATA_KEY, serialize_clock(clock)),
    )


def _set_trailing(context, clock, trace, extra=()):
    metadata = [
        (VECTOR_CLOCK_METADATA_KEY, serialize_clock(clock)),
        (EVENT_TRACE_METADATA_KEY, serialize_trace(trace)),
    ]
    metadata.extend(extra)
    context.set_trailing_metadata(tuple(metadata))


class FraudDetectionService(fd_grpc.FraudDetectionServiceServicer):

    @staticmethod
    def _log(order_id, event, clock):
        logging.info(
            "[%s] fraud_detection %s — VC: %s",
            order_id, event, serialize_clock(clock),
        )

    def _get_order(self, order_id, context):
        with order_cache_lock:
            order = order_cache.get(order_id)
        if not order:
            context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                f"Fraud order {order_id} not initialized",
            )
        return order

    # ── Init (cache only) ──

    def InitializeFraudOrder(self, request, context):
        metadata = metadata_to_dict(context.invocation_metadata())
        order_id = metadata.get(ORDER_ID_METADATA_KEY, "")
        incoming_clock = deserialize_clock(metadata.get(VECTOR_CLOCK_METADATA_KEY))

        clock = tick(merge_clocks(new_clock(), incoming_clock), "fraud_detection")
        self._log(order_id, "initialize", clock)

        cached = {
            "card_number": request.card_number,
            "order_amount": request.order_amount,
            "name": request.name,
            "email": request.email,
            "billing_address": {
                "street": request.billing_address.street if request.billing_address else "",
                "city": request.billing_address.city if request.billing_address else "",
                "state": request.billing_address.state if request.billing_address else "",
                "zip": request.billing_address.zip if request.billing_address else "",
                "country": request.billing_address.country if request.billing_address else "",
            },
            "clock": clock,
            "trace": [],
            "completed_events": set(),
        }
        record_event(cached["trace"], clock, "fraud_detection", "fraud_order_cached")

        with order_cache_lock:
            order_cache[order_id] = cached

        logging.info("Cached fraud order %s", order_id)
        _set_trailing(context, clock, cached["trace"])
        return fd_pb2.FraudResponse(is_fraud=False, message="Order cached")

    # ── Event d: check user data for fraud ──

    def CheckUserFraud(self, request, context):
        metadata = metadata_to_dict(context.invocation_metadata())
        order_id = metadata.get(ORDER_ID_METADATA_KEY, "")
        incoming_clock = deserialize_clock(metadata.get(VECTOR_CLOCK_METADATA_KEY))
        order = self._get_order(order_id, context)

        clock = process_event(order, "fraud_detection", "check_user_fraud", incoming_clock)
        self._log(order_id, "check_user_fraud", clock)
        order["completed_events"].add("d")

        # Deterministic user-fraud check
        name = order.get("name", "").lower()
        email = order.get("email", "").lower()

        is_fraud = False
        message = "User data clean"

        # Simple deterministic rules
        if "fraud" in name or "fraud" in email:
            is_fraud = True
            message = "Suspicious user identity detected"
        elif email.endswith(".suspicious"):
            is_fraud = True
            message = "Suspicious email domain"

        if is_fraud:
            logging.info("[%s] User fraud detected: %s", order_id, message)

        _set_trailing(context, clock, list(order["trace"]))
        return fd_pb2.FraudResponse(is_fraud=is_fraud, message=message)

    # ── Event e: check card data for fraud ──

    def CheckCardFraud(self, request, context):
        metadata = metadata_to_dict(context.invocation_metadata())
        order_id = metadata.get(ORDER_ID_METADATA_KEY, "")
        incoming_clock = deserialize_clock(metadata.get(VECTOR_CLOCK_METADATA_KEY))
        order = self._get_order(order_id, context)

        clock = process_event(order, "fraud_detection", "check_card_fraud", incoming_clock)
        self._log(order_id, "check_card_fraud", clock)
        order["completed_events"].add("e")

        card_number = order["card_number"]
        order_amount = order["order_amount"]

        is_fraud = False
        message = "Card data clean"

        # Deterministic card-fraud rules
        if card_number == "4111111111111111":
            is_fraud = False  # Known test card, always safe
            logging.info("[%s] Test card detected, marking as not fraud", order_id)
        elif card_number.startswith("999"):
            is_fraud = True
            message = "Card prefix flagged as fraudulent"
        else:
            try:
                amount = int(order_amount)
                if amount > 1000:
                    is_fraud = True
                    message = f"Order amount {amount} exceeds fraud threshold"
            except (ValueError, TypeError):
                pass

        if is_fraud:
            logging.info("[%s] Card fraud detected: %s", order_id, message)
            _set_trailing(context, clock, list(order["trace"]))
            return fd_pb2.FraudResponse(is_fraud=True, message=message)

        # Not fraud — call suggestions (event f)
        downstream_clock = tick(clock, "fraud_detection")
        record_event(order["trace"], downstream_clock, "fraud_detection", "dispatch_suggestions")
        self._log(order_id, "dispatch_suggestions", downstream_clock)

        try:
            with grpc.insecure_channel("suggestions:50053") as ch:
                stub = sg_grpc.SuggestionsServiceStub(ch)
                res_f, call_f = stub.GenerateSuggestions.with_call(
                    sg_pb2.Empty(),
                    metadata=_order_metadata(order_id, downstream_clock),
                )
            meta_f = metadata_to_dict(call_f.trailing_metadata())
            clock_f = deserialize_clock(meta_f.get(VECTOR_CLOCK_METADATA_KEY))
            trace_f = deserialize_trace(meta_f.get(EVENT_TRACE_METADATA_KEY))

            books = [
                {"bookId": book.bookId, "title": book.title, "author": book.author}
                for book in res_f.books
            ]

            final_clock = merge_clocks(downstream_clock, clock_f)
            final_clock = tick(final_clock, "fraud_detection")
            record_event(order["trace"], final_clock, "fraud_detection", "suggestions_received")
            self._log(order_id, "suggestions_received", final_clock)

            all_trace = list(order["trace"])
            all_trace.extend(trace_f)
            order["clock"] = final_clock

            _set_trailing(context, final_clock, all_trace,
                          extra=((SUGGESTED_BOOKS_METADATA_KEY, json.dumps(books)),))
            return fd_pb2.FraudResponse(is_fraud=False, message="Card data clean")

        except Exception as e:
            # Suggestions failure is non-fatal
            logging.warning("[%s] Suggestions failed (non-fatal): %s", order_id, e)
            final_clock = tick(downstream_clock, "fraud_detection")
            record_event(order["trace"], final_clock, "fraud_detection", "suggestions_failed")
            order["clock"] = final_clock
            _set_trailing(context, final_clock, list(order["trace"]),
                          extra=((SUGGESTED_BOOKS_METADATA_KEY, "[]"),))
            return fd_pb2.FraudResponse(is_fraud=False, message="Card data clean")

    # ── Clear (bonus) ──

    def ClearFraudOrder(self, request, context):
        metadata = metadata_to_dict(context.invocation_metadata())
        order_id = metadata.get(ORDER_ID_METADATA_KEY, "")
        incoming_clock = deserialize_clock(metadata.get(VECTOR_CLOCK_METADATA_KEY))

        with order_cache_lock:
            order = order_cache.get(order_id)
            if not order:
                logging.info("Clear: fraud order %s already cleared", order_id)
                _set_trailing(context, incoming_clock, [])
                return fd_pb2.FraudResponse(is_fraud=False, message="Already cleared")

            if clock_le(order["clock"], incoming_clock):
                del order_cache[order_id]
                logging.info("[%s] Cleared fraud order data", order_id)
                _set_trailing(context, incoming_clock, [])
                return fd_pb2.FraudResponse(is_fraud=False, message="Order cleared")
            else:
                logging.error(
                    "[%s] Clear rejected: local VC %s NOT <= final VC %s",
                    order_id, serialize_clock(order["clock"]), serialize_clock(incoming_clock),
                )
                _set_trailing(context, order["clock"], [])
                return fd_pb2.FraudResponse(is_fraud=False, message="Clock ordering violation")


def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    fd_grpc.add_FraudDetectionServiceServicer_to_server(FraudDetectionService(), server)
    port = "50051"
    server.add_insecure_port("[::]:" + port)
    server.start()
    logging.info("Fraud Detection service started on port %s", port)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

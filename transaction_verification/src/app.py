import sys
import os

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
tv_grpc_path = os.path.abspath(
    os.path.join(FILE, "../../../utils/pb/transaction_verification")
)
sys.path.insert(0, tv_grpc_path)
import transaction_verification_pb2 as tv_pb2
import transaction_verification_pb2_grpc as tv_grpc

fd_grpc_path = os.path.abspath(os.path.join(FILE, "../../../utils/pb/fraud_detection"))
sys.path.insert(0, fd_grpc_path)
import fraud_detection_pb2 as fd_pb2
import fraud_detection_pb2_grpc as fd_grpc

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

import logging
import re
from datetime import datetime
import grpc
from concurrent import futures
from threading import Lock
import time

logging.basicConfig(level=logging.INFO)

order_cache = {}
order_cache_lock = Lock()


class TransactionVerificationService(tv_grpc.TransactionVerificationServiceServicer):
    @staticmethod
    def _log_clock(order_id, event, clock):
        logging.info(
            "Order %s transaction_verification %s vector clock %s",
            order_id,
            event,
            serialize_clock(clock),
        )

    def _respond(self, context, trace, clock, is_valid, message, extra_metadata=()):
        clock = tick(clock, "transaction_verification")
        record_event(
            trace,
            clock,
            "transaction_verification",
            "verify_transaction_completed",
        )
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
        return tv_pb2.VerificationResponse(is_valid=is_valid, message=message)

    def _execute_fraud_detection(self, order_id, card_number, clock):
        deadline = time.monotonic() + 5
        while True:
            try:
                with grpc.insecure_channel("fraud_detection:50051") as channel:
                    stub = fd_grpc.FraudDetectionServiceStub(channel)
                    response, call = stub.InitializeFraudOrder.with_call(
                        fd_pb2.FraudRequest(card_number=card_number, order_amount="0"),
                        metadata=(
                            (ORDER_ID_METADATA_KEY, order_id),
                            (VECTOR_CLOCK_METADATA_KEY, serialize_clock(clock)),
                        ),
                    )
                metadata = metadata_to_dict(call.trailing_metadata())
                return (
                    response.is_fraud,
                    metadata.get(SUGGESTED_BOOKS_METADATA_KEY, "[]"),
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

    def _cache_order(self, order_id, request, clock):
        cached_order = {
            "email": request.email,
            "card_number": request.card_number,
            "expiration_date": request.expiration_date,
            "cvv": request.cvv,
            "billing_address": {
                "street": request.billing_address.street,
                "city": request.billing_address.city,
                "state": request.billing_address.state,
                "zip": request.billing_address.zip,
                "country": request.billing_address.country,
            },
            "clock": clock,
            "trace": [],
        }
        record_event(
            cached_order["trace"],
            clock,
            "transaction_verification",
            "verification_order_cached",
        )
        with order_cache_lock:
            order_cache[order_id] = cached_order
        return list(cached_order["trace"])

    def _load_order(self, order_id):
        with order_cache_lock:
            return order_cache.get(order_id)

    def _run_verification_flow(self, context, order_id, incoming_clock):
        cached_order = self._load_order(order_id)
        if not cached_order:
            context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                f"Verification order {order_id} not initialized",
            )

        clock = tick(
            merge_clocks(cached_order["clock"], incoming_clock),
            "transaction_verification",
        )
        trace = list(cached_order["trace"])
        self._log_clock(order_id, "execute", clock)

        record_event(
            trace,
            clock,
            "transaction_verification",
            "verify_transaction_request_received",
        )

        logging.info(
            f"Received verification request for order {order_id}, "
            f"card ending in {cached_order['card_number'][-4:] if cached_order['card_number'] else '????'}, "
            f"email={cached_order['email']}"
        )

        if not re.match(r"[^@]+@[^@]+\.[^@]+", cached_order["email"]):
            logging.info("Validation failed: invalid email format")
            return self._respond(context, trace, clock, False, "Invalid email format")

        if not cached_order["card_number"].isdigit() or len(cached_order["card_number"]) != 16:
            logging.info("Validation failed: invalid card number")
            return self._respond(context, trace, clock, False, "Invalid card number")

        if not cached_order["cvv"].isdigit() or len(cached_order["cvv"]) not in [3, 4]:
            logging.info("Validation failed: invalid CVV")
            return self._respond(context, trace, clock, False, "Invalid CVV")

        try:
            exp = datetime.strptime(cached_order["expiration_date"], "%m/%y")
            now = datetime.now()
            if (exp.year, exp.month) < (now.year, now.month):
                logging.info("Validation failed: card expired")
                return self._respond(context, trace, clock, False, "Card expired")
        except ValueError:
            logging.info("Validation failed: invalid expiration format")
            return self._respond(
                context, trace, clock, False, "Invalid expiration format"
            )

        addr = cached_order["billing_address"]

        if not addr["street"] or len(addr["street"].strip()) < 5:
            logging.info("Validation failed: invalid billing street")
            return self._respond(
                context, trace, clock, False, "Invalid billing street"
            )

        if not addr["city"] or len(addr["city"].strip()) < 2:
            logging.info("Validation failed: invalid billing city")
            return self._respond(context, trace, clock, False, "Invalid billing city")

        if not addr["state"].replace(" ", "").isalpha():
            logging.info("Validation failed: invalid billing state")
            return self._respond(
                context, trace, clock, False, "Invalid billing state"
            )

        if not addr["zip"].isdigit() or len(addr["zip"]) != 5:
            logging.info("Validation failed: invalid billing ZIP code")
            return self._respond(
                context, trace, clock, False, "Invalid billing ZIP code"
            )

        if not addr["country"] or len(addr["country"].strip()) < 2:
            logging.info("Validation failed: invalid billing country")
            return self._respond(
                context, trace, clock, False, "Invalid billing country"
            )

        downstream_clock = tick(clock, "transaction_verification")
        record_event(
            trace,
            downstream_clock,
            "transaction_verification",
            "dispatch_fraud_detection",
        )
        is_fraud, books_payload, fraud_clock, fraud_trace = self._execute_fraud_detection(
            order_id, cached_order["card_number"], downstream_clock
        )
        trace.extend(fraud_trace)
        clock = merge_clocks(downstream_clock, fraud_clock)

        if is_fraud:
            logging.info("Fraud detection denied order %s", order_id)
            return self._respond(context, trace, clock, False, "Fraud detected")

        logging.info("Transaction verification passed: all checks valid")
        return self._respond(
            context,
            trace,
            clock,
            True,
            "Transaction valid",
            extra_metadata=((SUGGESTED_BOOKS_METADATA_KEY, books_payload),),
        )

    def InitializeVerificationOrder(self, request, context):
        metadata = metadata_to_dict(context.invocation_metadata())
        order_id = metadata.get(ORDER_ID_METADATA_KEY, "")
        incoming_clock = deserialize_clock(metadata.get(VECTOR_CLOCK_METADATA_KEY))
        clock = tick(
            merge_clocks(new_clock(), incoming_clock), "transaction_verification"
        )
        self._log_clock(order_id, "initialize", clock)
        self._cache_order(order_id, request, clock)
        logging.info("Cached verification order %s", order_id)
        return self._run_verification_flow(context, order_id, clock)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    tv_grpc.add_TransactionVerificationServiceServicer_to_server(
        TransactionVerificationService(), server
    )
    port = "50052"
    server.add_insecure_port("[::]:" + port)
    server.start()
    logging.info(f"Transaction Verification service started on port {port}")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

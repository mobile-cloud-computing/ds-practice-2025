import sys
import os

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

import logging
import re
from datetime import datetime
import grpc
from concurrent import futures
from concurrent.futures import ThreadPoolExecutor
from threading import Lock, Event as ThreadEvent

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


class TransactionVerificationService(tv_grpc.TransactionVerificationServiceServicer):

    @staticmethod
    def _log(order_id, event, clock):
        logging.info(
            "[%s] transaction_verification %s — VC: %s",
            order_id, event, serialize_clock(clock),
        )

    def _get_order(self, order_id, context):
        with order_cache_lock:
            order = order_cache.get(order_id)
        if not order:
            context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                f"Verification order {order_id} not initialized",
            )
        return order

    # ── Init (cache only, no business logic) ──

    def InitializeVerificationOrder(self, request, context):
        metadata = metadata_to_dict(context.invocation_metadata())
        order_id = metadata.get(ORDER_ID_METADATA_KEY, "")
        incoming_clock = deserialize_clock(metadata.get(VECTOR_CLOCK_METADATA_KEY))

        clock = tick(merge_clocks(new_clock(), incoming_clock), "transaction_verification")
        self._log(order_id, "initialize", clock)

        cached = {
            "name": request.name,
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
            "items": [{"name": item.name, "quantity": item.quantity} for item in request.items],
            "clock": clock,
            "trace": [],
            "completed_events": set(),
        }
        record_event(cached["trace"], clock, "transaction_verification", "verification_order_cached")

        with order_cache_lock:
            order_cache[order_id] = cached

        logging.info("Cached verification order %s", order_id)
        _set_trailing(context, clock, cached["trace"])
        return tv_pb2.VerificationResponse(is_valid=True, message="Order cached")

    # ── Event a: check items not empty ──

    def CheckItemsNotEmpty(self, request, context):
        metadata = metadata_to_dict(context.invocation_metadata())
        order_id = metadata.get(ORDER_ID_METADATA_KEY, "")
        incoming_clock = deserialize_clock(metadata.get(VECTOR_CLOCK_METADATA_KEY))
        order = self._get_order(order_id, context)

        clock = process_event(order, "transaction_verification", "check_items_not_empty", incoming_clock)
        self._log(order_id, "check_items_not_empty", clock)
        order["completed_events"].add("a")

        is_valid = bool(order["items"]) and len(order["items"]) > 0
        message = "Items valid" if is_valid else "Order items list is empty"
        if not is_valid:
            logging.info("Event a failed: empty items list for order %s", order_id)

        _set_trailing(context, clock, list(order["trace"]))
        return tv_pb2.VerificationResponse(is_valid=is_valid, message=message)

    # ── Event b: check mandatory user data ──

    def CheckMandatoryUserData(self, request, context):
        metadata = metadata_to_dict(context.invocation_metadata())
        order_id = metadata.get(ORDER_ID_METADATA_KEY, "")
        incoming_clock = deserialize_clock(metadata.get(VECTOR_CLOCK_METADATA_KEY))
        order = self._get_order(order_id, context)

        clock = process_event(order, "transaction_verification", "check_mandatory_user_data", incoming_clock)
        self._log(order_id, "check_mandatory_user_data", clock)
        order["completed_events"].add("b")

        # Validate mandatory fields
        if not order["name"] or not order["name"].strip():
            _set_trailing(context, clock, list(order["trace"]))
            return tv_pb2.VerificationResponse(is_valid=False, message="Name is required")

        if not re.match(r"[^@]+@[^@]+\.[^@]+", order["email"]):
            _set_trailing(context, clock, list(order["trace"]))
            return tv_pb2.VerificationResponse(is_valid=False, message="Invalid email format")

        addr = order["billing_address"]
        if not addr["street"] or len(addr["street"].strip()) < 5:
            _set_trailing(context, clock, list(order["trace"]))
            return tv_pb2.VerificationResponse(is_valid=False, message="Invalid billing street")
        if not addr["city"] or len(addr["city"].strip()) < 2:
            _set_trailing(context, clock, list(order["trace"]))
            return tv_pb2.VerificationResponse(is_valid=False, message="Invalid billing city")
        if not addr["state"].replace(" ", "").isalpha():
            _set_trailing(context, clock, list(order["trace"]))
            return tv_pb2.VerificationResponse(is_valid=False, message="Invalid billing state")
        if not addr["zip"].isdigit() or len(addr["zip"]) != 5:
            _set_trailing(context, clock, list(order["trace"]))
            return tv_pb2.VerificationResponse(is_valid=False, message="Invalid billing ZIP code")
        if not addr["country"] or len(addr["country"].strip()) < 2:
            _set_trailing(context, clock, list(order["trace"]))
            return tv_pb2.VerificationResponse(is_valid=False, message="Invalid billing country")

        _set_trailing(context, clock, list(order["trace"]))
        return tv_pb2.VerificationResponse(is_valid=True, message="User data valid")

    # ── Event c: check card format ──

    def CheckCardFormat(self, request, context):
        metadata = metadata_to_dict(context.invocation_metadata())
        order_id = metadata.get(ORDER_ID_METADATA_KEY, "")
        incoming_clock = deserialize_clock(metadata.get(VECTOR_CLOCK_METADATA_KEY))
        order = self._get_order(order_id, context)

        clock = process_event(order, "transaction_verification", "check_card_format", incoming_clock)
        self._log(order_id, "check_card_format", clock)
        order["completed_events"].add("c")

        if not order["card_number"].isdigit() or len(order["card_number"]) != 16:
            _set_trailing(context, clock, list(order["trace"]))
            return tv_pb2.VerificationResponse(is_valid=False, message="Invalid card number")

        if not order["cvv"].isdigit() or len(order["cvv"]) not in [3, 4]:
            _set_trailing(context, clock, list(order["trace"]))
            return tv_pb2.VerificationResponse(is_valid=False, message="Invalid CVV")

        try:
            exp = datetime.strptime(order["expiration_date"], "%m/%y")
            now = datetime.now()
            if (exp.year, exp.month) < (now.year, now.month):
                _set_trailing(context, clock, list(order["trace"]))
                return tv_pb2.VerificationResponse(is_valid=False, message="Card expired")
        except ValueError:
            _set_trailing(context, clock, list(order["trace"]))
            return tv_pb2.VerificationResponse(is_valid=False, message="Invalid expiration format")

        _set_trailing(context, clock, list(order["trace"]))
        return tv_pb2.VerificationResponse(is_valid=True, message="Card format valid")

    # ── StartVerificationFlow: orchestrates a→c, b→d, join→e→f ──

    def StartVerificationFlow(self, request, context):
        metadata = metadata_to_dict(context.invocation_metadata())
        order_id = metadata.get(ORDER_ID_METADATA_KEY, "")
        incoming_clock = deserialize_clock(metadata.get(VECTOR_CLOCK_METADATA_KEY))
        order = self._get_order(order_id, context)

        clock = process_event(order, "transaction_verification", "start_verification_flow", incoming_clock)
        self._log(order_id, "start_verification_flow", clock)

        # Shared cancellation state
        failed = {"reason": None}
        cancel_flag = ThreadEvent()

        # Snapshot clock for parallel dispatch (same parent clock for a and b)
        parent_clock = dict(clock)

        def run_branch_a():
            """a → c (both in TV)"""
            try:
                # Event a
                with grpc.insecure_channel("localhost:50052") as ch:
                    stub = tv_grpc.TransactionVerificationServiceStub(ch)
                    res_a, call_a = stub.CheckItemsNotEmpty.with_call(
                        tv_pb2.Empty(), metadata=_order_metadata(order_id, parent_clock),
                    )
                meta_a = metadata_to_dict(call_a.trailing_metadata())
                clock_a = deserialize_clock(meta_a.get(VECTOR_CLOCK_METADATA_KEY))
                trace_a = deserialize_trace(meta_a.get(EVENT_TRACE_METADATA_KEY))

                if not res_a.is_valid:
                    failed["reason"] = res_a.message
                    cancel_flag.set()
                    return False, clock_a, trace_a

                if cancel_flag.is_set():
                    return False, clock_a, trace_a

                # Event c (depends on a)
                with grpc.insecure_channel("localhost:50052") as ch:
                    stub = tv_grpc.TransactionVerificationServiceStub(ch)
                    res_c, call_c = stub.CheckCardFormat.with_call(
                        tv_pb2.Empty(), metadata=_order_metadata(order_id, clock_a),
                    )
                meta_c = metadata_to_dict(call_c.trailing_metadata())
                clock_c = deserialize_clock(meta_c.get(VECTOR_CLOCK_METADATA_KEY))
                trace_c = deserialize_trace(meta_c.get(EVENT_TRACE_METADATA_KEY))

                if not res_c.is_valid:
                    failed["reason"] = res_c.message
                    cancel_flag.set()
                    return False, clock_c, trace_c

                return True, clock_c, trace_c
            except Exception as e:
                failed["reason"] = str(e)
                cancel_flag.set()
                return False, parent_clock, []

        def run_branch_b():
            """b (in TV) → d (calls FD)"""
            try:
                # Event b
                with grpc.insecure_channel("localhost:50052") as ch:
                    stub = tv_grpc.TransactionVerificationServiceStub(ch)
                    res_b, call_b = stub.CheckMandatoryUserData.with_call(
                        tv_pb2.Empty(), metadata=_order_metadata(order_id, parent_clock),
                    )
                meta_b = metadata_to_dict(call_b.trailing_metadata())
                clock_b = deserialize_clock(meta_b.get(VECTOR_CLOCK_METADATA_KEY))
                trace_b = deserialize_trace(meta_b.get(EVENT_TRACE_METADATA_KEY))

                if not res_b.is_valid:
                    failed["reason"] = res_b.message
                    cancel_flag.set()
                    return False, clock_b, trace_b

                if cancel_flag.is_set():
                    return False, clock_b, trace_b

                # Event d (calls FD CheckUserFraud, depends on b)
                with grpc.insecure_channel("fraud_detection:50051") as ch:
                    stub = fd_grpc.FraudDetectionServiceStub(ch)
                    res_d, call_d = stub.CheckUserFraud.with_call(
                        fd_pb2.Empty(), metadata=_order_metadata(order_id, clock_b),
                    )
                meta_d = metadata_to_dict(call_d.trailing_metadata())
                clock_d = deserialize_clock(meta_d.get(VECTOR_CLOCK_METADATA_KEY))
                trace_d = deserialize_trace(meta_d.get(EVENT_TRACE_METADATA_KEY))

                if res_d.is_fraud:
                    failed["reason"] = res_d.message or "User data fraud detected"
                    cancel_flag.set()
                    return False, clock_d, trace_d

                return True, clock_d, trace_d
            except Exception as e:
                failed["reason"] = str(e)
                cancel_flag.set()
                return False, parent_clock, []

        # Run a||b in parallel
        with ThreadPoolExecutor(max_workers=2) as pool:
            future_a = pool.submit(run_branch_a)
            future_b = pool.submit(run_branch_b)
            result_a = future_a.result()
            result_b = future_b.result()

        ok_a, clock_a, trace_a = result_a
        ok_b, clock_b, trace_b = result_b

        # Collect traces from both branches
        all_trace = list(order["trace"])
        all_trace.extend(trace_a)
        all_trace.extend(trace_b)

        if not ok_a or not ok_b:
            merged = merge_clocks(clock_a, clock_b)
            merged = tick(merged, "transaction_verification")
            record_event(all_trace, merged, "transaction_verification", "verification_flow_failed")
            self._log(order_id, "verification_flow_failed", merged)
            order["clock"] = merged
            order["trace"] = all_trace
            _set_trailing(context, merged, all_trace)
            return tv_pb2.VerificationResponse(
                is_valid=False,
                message=failed["reason"] or "Verification failed",
            )

        # Join point: merge clocks from c and d, tick before dispatching e
        join_clock = tick(merge_clocks(clock_a, clock_b), "transaction_verification")
        record_event(all_trace, join_clock, "transaction_verification", "join_branches_c_d")
        self._log(order_id, "join_branches_c_d", join_clock)

        # Event e: call FD CheckCardFraud (depends on c AND d)
        try:
            with grpc.insecure_channel("fraud_detection:50051") as ch:
                stub = fd_grpc.FraudDetectionServiceStub(ch)
                res_e, call_e = stub.CheckCardFraud.with_call(
                    fd_pb2.Empty(), metadata=_order_metadata(order_id, join_clock),
                )
            meta_e = metadata_to_dict(call_e.trailing_metadata())
            clock_e = deserialize_clock(meta_e.get(VECTOR_CLOCK_METADATA_KEY))
            trace_e = deserialize_trace(meta_e.get(EVENT_TRACE_METADATA_KEY))
            all_trace.extend(trace_e)

            if res_e.is_fraud:
                merged = merge_clocks(join_clock, clock_e)
                merged = tick(merged, "transaction_verification")
                record_event(all_trace, merged, "transaction_verification", "verification_flow_fraud_detected")
                self._log(order_id, "verification_flow_fraud_detected", merged)
                order["clock"] = merged
                order["trace"] = all_trace
                _set_trailing(context, merged, all_trace)
                return tv_pb2.VerificationResponse(
                    is_valid=False,
                    message=res_e.message or "Card fraud detected",
                )

            # e passed — check for suggested books from metadata (event f was called by FD)
            books_payload = meta_e.get(SUGGESTED_BOOKS_METADATA_KEY, "[]")
            final_clock = merge_clocks(join_clock, clock_e)
            final_clock = tick(final_clock, "transaction_verification")
            record_event(all_trace, final_clock, "transaction_verification", "verification_flow_completed")
            self._log(order_id, "verification_flow_completed", final_clock)
            order["clock"] = final_clock
            order["trace"] = all_trace

            _set_trailing(context, final_clock, all_trace,
                          extra=((SUGGESTED_BOOKS_METADATA_KEY, books_payload),))
            return tv_pb2.VerificationResponse(is_valid=True, message="Transaction valid")

        except Exception as e:
            logging.error("Error during event e/f: %s", e)
            merged = tick(join_clock, "transaction_verification")
            record_event(all_trace, merged, "transaction_verification", "verification_flow_error")
            order["clock"] = merged
            order["trace"] = all_trace
            _set_trailing(context, merged, all_trace)
            return tv_pb2.VerificationResponse(is_valid=False, message=str(e))

    # ── Clear (bonus) ──

    def ClearVerificationOrder(self, request, context):
        metadata = metadata_to_dict(context.invocation_metadata())
        order_id = metadata.get(ORDER_ID_METADATA_KEY, "")
        incoming_clock = deserialize_clock(metadata.get(VECTOR_CLOCK_METADATA_KEY))

        with order_cache_lock:
            order = order_cache.get(order_id)
            if not order:
                logging.info("Clear: order %s already cleared or never existed", order_id)
                _set_trailing(context, incoming_clock, [])
                return tv_pb2.VerificationResponse(is_valid=True, message="Already cleared")

            if clock_le(order["clock"], incoming_clock):
                del order_cache[order_id]
                logging.info("[%s] Cleared verification order data", order_id)
                _set_trailing(context, incoming_clock, [])
                return tv_pb2.VerificationResponse(is_valid=True, message="Order cleared")
            else:
                logging.error(
                    "[%s] Clear rejected: local VC %s NOT <= final VC %s",
                    order_id, serialize_clock(order["clock"]), serialize_clock(incoming_clock),
                )
                _set_trailing(context, order["clock"], [])
                return tv_pb2.VerificationResponse(is_valid=False, message="Clock ordering violation")


def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    tv_grpc.add_TransactionVerificationServiceServicer_to_server(
        TransactionVerificationService(), server
    )
    port = "50052"
    server.add_insecure_port("[::]:" + port)
    server.start()
    logging.info("Transaction Verification service started on port %s", port)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

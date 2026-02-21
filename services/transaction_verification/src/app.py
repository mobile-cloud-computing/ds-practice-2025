import sys
import os
import json
import re
import logging

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
pb_root = os.path.abspath(os.path.join(FILE, "../../../../utils/pb"))
sys.path.insert(0, pb_root)

from transaction_verification import transaction_verification_pb2 as tv_pb2
from transaction_verification import transaction_verification_pb2_grpc as tv_grpc

import grpc
from concurrent import futures

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("transaction_verification")


class TransactionVerificationService(tv_grpc.TransactionVerificationServiceServicer):
    def VerifyTransaction(self, request, context):
        log.info("VerifyTransaction called")

        try:
            order = json.loads(request.order_json)
        except Exception:
            return tv_pb2.TransactionResponse(is_valid=False, reason="Invalid JSON")

        items = order.get("items", [])
        user = order.get("user", {}) or {}
        credit = order.get("creditCard", {}) or {}

        # Validation rules
        # 1) Check if items list is not empty
        if not items or len(items) == 0:
            return tv_pb2.TransactionResponse(is_valid=False, reason="No items in order")

        # 2) Check if user info is complete
        if not user.get("name"):
            return tv_pb2.TransactionResponse(is_valid=False, reason="Missing user name")
        if not user.get("contact"):
            return tv_pb2.TransactionResponse(is_valid=False, reason="Missing user contact")

        # 3) Check if credit card info is complete
        if not credit.get("number"):
            return tv_pb2.TransactionResponse(is_valid=False, reason="Missing credit card number")
        if not credit.get("expirationDate"):
            return tv_pb2.TransactionResponse(is_valid=False, reason="Missing expiration date")
        if not credit.get("cvv"):
            return tv_pb2.TransactionResponse(is_valid=False, reason="Missing CVV")

        # 4) Validate credit card number format (13-19 digits)
        card_number = str(credit.get("number", ""))
        if not re.fullmatch(r"\d{13,19}", card_number):
            return tv_pb2.TransactionResponse(is_valid=False, reason="Invalid credit card format")

        # 5) Validate CVV format (3-4 digits)
        cvv = str(credit.get("cvv", ""))
        if not re.fullmatch(r"\d{3,4}", cvv):
            return tv_pb2.TransactionResponse(is_valid=False, reason="Invalid CVV format")

        # 6) Check each item has required fields
        for item in items:
            if not item.get("name"):
                return tv_pb2.TransactionResponse(is_valid=False, reason="Item missing name")
            quantity = item.get("quantity")
            if quantity is None or not isinstance(quantity, (int, float)) or quantity <= 0:
                return tv_pb2.TransactionResponse(is_valid=False, reason="Invalid item quantity")

        # All checks passed
        return tv_pb2.TransactionResponse(is_valid=True, reason="Transaction valid")


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    tv_grpc.add_TransactionVerificationServiceServicer_to_server(
        TransactionVerificationService(), server
    )

    port = "50052"
    server.add_insecure_port("[::]:" + port)
    server.start()
    log.info("Transaction verification service started on port %s", port)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

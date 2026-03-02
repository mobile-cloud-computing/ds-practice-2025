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

import logging
import re
from datetime import datetime
import grpc
from concurrent import futures

logging.basicConfig(level=logging.INFO)


class TransactionVerificationService(tv_grpc.TransactionVerificationServiceServicer):

    def VerifyTransaction(self, request, context):
        """Validate transaction fields: email format, card number, CVV, expiration date, and billing address."""
        logging.info(
            f"Received verification request for card ending in {request.card_number[-4:] if request.card_number else '????'}, email={request.email}"
        )

        if not re.match(r"[^@]+@[^@]+\.[^@]+", request.email):
            logging.info("Validation failed: invalid email format")
            return tv_pb2.VerificationResponse(
                is_valid=False, message="Invalid email format"
            )

        if not request.card_number.isdigit() or len(request.card_number) != 16:
            logging.info("Validation failed: invalid card number")
            return tv_pb2.VerificationResponse(
                is_valid=False, message="Invalid card number"
            )

        if not request.cvv.isdigit() or len(request.cvv) not in [3, 4]:
            logging.info("Validation failed: invalid CVV")
            return tv_pb2.VerificationResponse(is_valid=False, message="Invalid CVV")

        try:
            exp = datetime.strptime(request.expiration_date, "%m/%y")
            # Compare year/month only so a card valid through this month isn't rejected
            now = datetime.now()
            if (exp.year, exp.month) < (now.year, now.month):
                logging.info("Validation failed: card expired")
                return tv_pb2.VerificationResponse(
                    is_valid=False, message="Card expired"
                )
        except ValueError:
            logging.info("Validation failed: invalid expiration format")
            return tv_pb2.VerificationResponse(
                is_valid=False, message="Invalid expiration format"
            )

        # Billing Address Checks

        addr = request.billing_address

        if not addr.street or len(addr.street.strip()) < 5:
            logging.info("Validation failed: invalid billing street")
            return tv_pb2.VerificationResponse(
                is_valid=False, message="Invalid billing street"
            )

        if not addr.city or len(addr.city.strip()) < 2:
            logging.info("Validation failed: invalid billing city")
            return tv_pb2.VerificationResponse(
                is_valid=False, message="Invalid billing city"
            )

        if not addr.state.replace(" ", "").isalpha():
            logging.info("Validation failed: invalid billing state")
            return tv_pb2.VerificationResponse(
                is_valid=False, message="Invalid billing state"
            )

        if not addr.zip.isdigit() or len(addr.zip) != 5:
            logging.info("Validation failed: invalid billing ZIP code")
            return tv_pb2.VerificationResponse(
                is_valid=False, message="Invalid billing ZIP code"
            )

        if not addr.country or len(addr.country.strip()) < 2:
            logging.info("Validation failed: invalid billing country")
            return tv_pb2.VerificationResponse(
                is_valid=False, message="Invalid billing country"
            )

        logging.info("Transaction verification passed: all checks valid")
        return tv_pb2.VerificationResponse(is_valid=True, message="Transaction valid")


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

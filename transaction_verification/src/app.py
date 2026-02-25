import sys
import os
import re
from datetime import datetime

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
transaction_verification_grpc_path = os.path.abspath(
    os.path.join(FILE, '../../../utils/pb/transaction_verification')
)
sys.path.insert(0, transaction_verification_grpc_path)
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc

import grpc
from concurrent import futures


def _is_non_empty(value: str) -> bool:
    return bool(value and value.strip())


def _is_valid_email(email: str) -> bool:
    email = (email or "").strip()
    return re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) is not None


def _is_luhn_valid(card_number: str) -> bool:
    digits_only = "".join(ch for ch in card_number if ch.isdigit())
    if not 13 <= len(digits_only) <= 19:
        return False
    if len(set(digits_only)) == 1:
        return False

    checksum = 0
    should_double = False
    for digit in reversed(digits_only):
        value = int(digit)
        if should_double:
            value *= 2
            if value > 9:
                value -= 9
        checksum += value
        should_double = not should_double
    return checksum % 10 == 0


def _is_valid_expiration(expiration: str) -> bool:
    exp = (expiration or "").strip()
    # Accept MM/YY or MM/YYYY
    match = re.fullmatch(r"(0[1-9]|1[0-2])\/(\d{2}|\d{4})", exp)
    if not match:
        return False

    month = int(match.group(1))
    year_raw = match.group(2)
    year = int(year_raw) + 2000 if len(year_raw) == 2 else int(year_raw)

    now = datetime.utcnow()
    # Card valid through end of expiry month
    if year < now.year:
        return False
    if year == now.year and month < now.month:
        return False
    return True


def _is_valid_cvv(cvv: str) -> bool:
    cvv = (cvv or "").strip()
    return re.fullmatch(r"\d{3,4}", cvv) is not None


def _is_valid_billing_zip(zip_code: str) -> bool:
    zip_code = (zip_code or "").strip()
    # Simple international-safe check (3-10, letters/numbers/space/hyphen)
    if not re.fullmatch(r"[A-Za-z0-9 -]{3,10}", zip_code):
        return False
    return any(ch.isdigit() for ch in zip_code)


def _validate_items(items) -> list[str]:
    errors = []
    if len(items) == 0:
        # Reject empty cart
        errors.append("At least one item is required")
        return errors

    for idx, item in enumerate(items):
        if not _is_non_empty(item.name):
            # Reject item with blank name
            errors.append(f"Item at index {idx} must have a name")
        if item.quantity <= 0:
            # Reject item with non-positive quantity
            errors.append(f"Item '{item.name or idx}' must have quantity > 0")
    return errors


class TransactionVerificationService(
    transaction_verification_grpc.TransactionVerificationServiceServicer
):
    def VerifyTransaction(self, request, context):
        reasons = []

        if not _is_non_empty(request.transaction_id):
            reasons.append("Missing transaction ID")
        if not _is_non_empty(request.purchaser_name):
            reasons.append("Missing purchaser name")
        if not _is_non_empty(request.purchaser_email):
            reasons.append("Missing purchaser email")
        elif not _is_valid_email(request.purchaser_email):
            reasons.append("Purchaser email format is invalid")

        if not _is_non_empty(request.credit_card_number):
            reasons.append("Missing credit card number")
        elif not _is_luhn_valid(request.credit_card_number):
            reasons.append("Credit card number is invalid")

        if not _is_non_empty(request.credit_card_expiration):
            reasons.append("Missing credit card expiration")
        elif not _is_valid_expiration(request.credit_card_expiration):
            reasons.append("Credit card expiration is invalid or expired")

        if not _is_non_empty(request.credit_card_cvv):
            reasons.append("Missing credit card CVV")
        elif not _is_valid_cvv(request.credit_card_cvv):
            reasons.append("Credit card CVV is invalid")

        if not _is_non_empty(request.billing_street):
            reasons.append("Missing billing street")
        if not _is_non_empty(request.billing_city):
            reasons.append("Missing billing city")
        if not _is_non_empty(request.billing_state):
            reasons.append("Missing billing state")
        if not _is_non_empty(request.billing_zip):
            reasons.append("Missing billing zip")
        elif not _is_valid_billing_zip(request.billing_zip):
            reasons.append("Billing zip format is invalid")
        if not _is_non_empty(request.billing_country):
            reasons.append("Missing billing country")

        reasons.extend(_validate_items(request.items))

        if not request.terms_accepted:
            reasons.append("Terms and conditions must be accepted")

        is_valid = len(reasons) == 0
        return transaction_verification.TransactionVerificationResponse(
            is_valid=is_valid,
            reasons=reasons,
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    transaction_verification_grpc.add_TransactionVerificationServiceServicer_to_server(
        TransactionVerificationService(), server
    )
    port = "50052"
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Server started. Listening on port 50052.")
    server.wait_for_termination()


if __name__ == '__main__':
    serve()

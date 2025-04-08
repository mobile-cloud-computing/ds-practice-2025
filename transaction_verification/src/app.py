import logging
import sys
import os
import datetime
from datetime import datetime as dt

logger = logging.getLogger(__name__)

FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
models_path = os.path.abspath(os.path.join(FILE, "../../../utils/models"))
vector_clock_path = os.path.abspath(os.path.join(FILE, "../../../utils/vector_clock"))
grpc_path = os.path.abspath(
    os.path.join(FILE, "../../../utils/pb/transaction_verification")
)
sys.path.insert(0, grpc_path)
sys.path.insert(0, models_path)
sys.path.insert(0, vector_clock_path)

import grpc
from concurrent import futures
import re

import transaction_verification_pb2
import transaction_verification_pb2_grpc
import datetime

from vector_clock import OrderEventTracker


def check_luhn_algorithm(card_no):
    # unchanged from your code
    n_digits = len(card_no)
    n_sum = 0
    is_second = False
    for i in range(n_digits - 1, -1, -1):
        d = int(card_no[i])
        if is_second:
            d = d * 2
        n_sum += d // 10
        n_sum += d % 10
        is_second = not is_second
    return n_sum % 10 == 0


def check_billing_address_complete(city, country):
    """Return (bool, reason) indicating if address is complete."""
    if not (city and country):
        return False, "Billing address is incomplete"
    return True, "OK"


class TransactionVerificationServiceServicer(
    transaction_verification_pb2_grpc.TransactionVerificationServiceServicer
):
    def __init__(self):
        self.orders = {}
        self.service_name = "transaction_verification"

        self.order_event_tracker = OrderEventTracker()

    def InitializeOrder(self, request, context):
        order_id = request.order_id
        self.orders[order_id] = {
            "creditCardNumber": request.creditCardNumber,
            "expiryDate": request.expiryDate,
            "billingStreet": request.billingStreet,
            "billingCity": request.billingCity,
            "billingState": request.billingState,
            "billingZip": request.billingZip,
            "billingCountry": request.billingCountry,
        }

        print(f"[TransactionVerification] Initialized order {order_id} with data:")
        print(self.orders[order_id])

        return transaction_verification_pb2.TransactionInitResponse(success=True)

    def VerifyTransaction(self, request, context):
        """
        Retrieve the cached data from InitializeOrder if it exists;
        else fallback to the fields in 'request'.
        """
        order_id = request.order_id
        is_valid = True
        reason = "OK"

        received_clock = dict(request.vectorClock)
        if not self.order_event_tracker.order_exists(order_id):
            self.order_event_tracker.initialize_order(order_id)
            logger.info(
                f"[TransactionVerification]Initialized order {order_id} with vector clock"
            )

        cached = self.orders.get(order_id)
        if cached:
            credit_card_number = cached["creditCardNumber"]
            expiry_date = cached["expiryDate"]
            # billing_street = cached["billingStreet"]
            billing_city = cached["billingCity"]
            # billing_state = cached["billingState"]
            # billing_zip = cached["billingZip"]
            billing_country = cached["billingCountry"]
        else:
            logger.info(
                f"[TransactionVerification] No init data for {order_id}, fallback to request only."
            )
            credit_card_number = request.creditCardNumber
            expiry_date = request.expiryDate

            # billing_street = ""
            billing_city = ""
            # billing_state = ""
            # billing_zip = ""
            billing_country = ""

        # 1) Check card length
        if not (13 <= len(credit_card_number) <= 19):
            is_valid = False
            reason = f"Invalid credit card length: {len(credit_card_number)}"

        # 1a) Luhn
        if is_valid:
            if not check_luhn_algorithm(credit_card_number):
                is_valid = False
                reason = "Invalid credit card number (Luhn algorithm check failed)"

        # 2) Check expiry date
        if is_valid:
            pattern = r"^(0[1-9]|1[0-2])/(20)?\d{2}$"
            if not re.match(pattern, expiry_date):
                is_valid = False
                reason = f"Invalid expiry date format: {expiry_date}"
            else:
                try:
                    if len(expiry_date) == 5:  # MM/YY
                        month, year_short = expiry_date.split("/")
                        year = int("20" + year_short)
                    else:  # MM/YYYY
                        month, year = expiry_date.split("/")
                        year = int(year)

                    month = int(month)
                    if month == 12:
                        next_month = 1
                        next_year = year + 1
                    else:
                        next_month = month + 1
                        next_year = year

                    expiry_date_obj = dt(next_year, next_month, 1) - datetime.timedelta(
                        days=1
                    )
                    current_date = dt.now()
                    if expiry_date_obj < current_date:
                        reason = "Card has expired"
                        is_valid = False
                except ValueError:
                    is_valid = False
                    reason = "Invalid date values"

        # 3) Check billing address completeness
        if is_valid:
            billing_ok, addr_reason = check_billing_address_complete(
                billing_city, billing_country
            )
            if not billing_ok:
                is_valid = False
                reason = addr_reason

        print(
            f"[TransactionVerification] VerifyTransaction order {order_id} => {is_valid}, reason={reason}"
        )

        updated_clock = self.order_event_tracker.record_event(
            order_id=order_id,
            service=self.service_name,
            event_name="transaction_verification",
            received_clock=received_clock,
        )

        logger.info(
            f"[TransactionVerification] {self.service_name}, Order {order_id}, Event 'VerifyTransaction', Updated Clock: {updated_clock}"
        )

        return transaction_verification_pb2.TransactionResponse(
            isValid=is_valid, reason=reason, vectorClock=updated_clock
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    transaction_verification_pb2_grpc.add_TransactionVerificationServiceServicer_to_server(
        TransactionVerificationServiceServicer(), server
    )
    server.add_insecure_port("[::]:50052")
    server.start()
    print("[TransactionVerification] SERVICE listening on port 50052.")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

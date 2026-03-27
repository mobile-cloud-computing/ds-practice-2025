import sys
import os

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
utils_path = os.path.abspath(os.path.join(FILE, '../../../utils/'))
sys.path.insert(0, utils_path)
from log_utils.logger import setup_logger

from service_wrappers.base_service_wrapper import BaseServiceWrapper, init_grpc_pathes
init_grpc_pathes()


import pb.services.order_details_pb2 as order_details

import pb.services.transaction_verification_pb2 as transaction_verification
import pb.services.transaction_verification_pb2_grpc as transaction_verification_grpc

import pb.services.fraud_detection_pb2_grpc as fraud_detection_grpc
import pb.services.recommendation_system_pb2_grpc as recommendation_system_grpc

import grpc
from concurrent import futures
import datetime
from geopy.geocoders import Nominatim


logger = setup_logger("TransactionVerificationService")


def validate_credit_card(card_number):
    # credit card verification - Luhn's Algorithm
    # reference - https://dev.to/seraph776/validate-credit-card-numbers-using-python-37j9

    logger.info(f"Verification of credit card number {card_number}")

    if len(card_number) != 16:
        return False

    card_number = [int(num) for num in card_number]
    check_digit = card_number.pop(-1)
    card_number.reverse()
    card_number = [num * 2 if idx % 2 == 0 else num for idx, num in enumerate(card_number)]
    card_number = [num - 9 if idx % 2 == 0 and num > 9 else num for idx, num in enumerate(card_number)]
    card_number.append(check_digit)
    check_sum = sum(card_number)
    return check_sum % 10 == 0


def validate_credit_card_vendor(card_number):
    logger.info(f"Verification of credit card vendor {card_number}")
    is_mastercard = card_number[0] == "5" and (card_number[1] == "1" or card_number[1] == "5")
    is_visa = card_number[0] == "4"
    return is_mastercard or is_visa


def validate_expiration_date(in_date):
    logger.info(f"Verification of credit card date {in_date}")
    expr_month = in_date.split("/")[0].strip()
    expr_year = in_date.split("/")[1].strip()

    if len(expr_month) == 1:
        expr_month = f"0{expr_month}"
    if len(expr_year) == 2:
        expr_year = f"20{expr_year}"

    if len(expr_month) != 2 or len(expr_year) != 4:
        return False
    
    expr_month = int(expr_month)
    expr_year = int(expr_year)

    if expr_month < 1 or expr_month > 12:
        return False
    
    present = datetime.date.today()

    next_month = (expr_month + 1) % 13
    if next_month == 0:
        next_month += 1
        next_year = expr_year + 1
    else:
        next_year = expr_year
        
    next_expr_date = datetime.date(next_year, next_month, 1)

    if present >= next_expr_date:  # credit card expired
        return False
    
    age = (next_expr_date - present).days
    if age > 365 * 3:  # credit card cant have more than 3 years of validity
        return False
    
    return True


def validate_cvv(cvv):
    logger.info(f"Verification of credit card cvv {cvv}")
    return len(cvv) == 3 and cvv.isdigit()


def validate_location(location_obj):
    address = f"{location_obj.street} {location_obj.city} {location_obj.state} {location_obj.country}"
    logger.info(f"Verification of address {address}")

    n_tries = 5

    for i in range(n_tries):
        try:
            geolocator = Nominatim(user_agent="transaction_verification")
            location = geolocator.geocode(address)
            if location is None:
                logger.error("Location is not found")
                return False
            logger.info(f"Location is resolved: {location}")
            return True
        except Exception as e:
            logger.error(f"Location resolution iter {i} error: {e}")
    return False


def validate_order_list(orders):
    logger.info(f"Verification of order list: {orders}")
    
    if len(orders) == 0:
        return False
    
    for elem in orders:
        if elem.quantity < 0 or elem.quantity > 100:
            return False
        if len(elem.name) == 0:
            return False
    
    return True


def verify_transaction(input_data):
    if not validate_credit_card(input_data.credit_card.number):
        return transaction_verification.TransactionVerficationResponse(
            transaction_valid=False, 
            error_message=f"Luhn's Algorithm failed, wrong card number {input_data.credit_card.number}"
        )
    if not validate_credit_card_vendor(input_data.credit_card.number):
        return transaction_verification.TransactionVerficationResponse(
            transaction_valid=False, 
            error_message=f"Unrecognised credit card vendor of {input_data.credit_card.number}, supports only MasterCard or Visa"
        )
    if not validate_expiration_date(input_data.credit_card.expiration_date):
        return transaction_verification.TransactionVerficationResponse(
            transaction_valid=False, 
            error_message=f"Credit card expired {input_data.credit_card.expiration_date}"
        )
    if not validate_cvv(input_data.credit_card.cvv):
        return transaction_verification.TransactionVerficationResponse(
            transaction_valid=False, 
            error_message=f"Invalid CVV {input_data.credit_card.cvv}"
        )
    if not validate_location(input_data.billing_address):
        return transaction_verification.TransactionVerficationResponse(
            transaction_valid=False, 
            error_message=f"Invalid address {input_data.billing_address.street} {input_data.billing_address.city} {input_data.billing_address.state} {input_data.billing_address.country}"
        )
    if not validate_order_list(input_data.items):
        return transaction_verification.TransactionVerficationResponse(
            transaction_valid=False, 
            error_message=f"Invalid order list {input_data.items}"
        )
    return transaction_verification.TransactionVerficationResponse(transaction_valid=True)
    


class TransactionVerificationService(BaseServiceWrapper, transaction_verification_grpc.TransactionVerificationService):
    def _do_verification(self, request, verify_function):
        data = self.order_details.get(request.order_id, None)

        if data is None:
            logger.error(f"Order id {request.order_id} is not found")
            return False, f"Order id {request.order_id} is not found"

        for fn in verify_function:
            result = fn(data)
            if not result:
                return result, f"Verification failed for function {fn.__name__}"
        return True, ""
    
    def _method_template(self, request, verify_functions, stub_class, connection_string, method_name):
        status = order_details.StatusMessage(
            success=True,
            order_id=request.order_id,
            vector_clock=self.vector_clock
        )

        try:
            self._update_vector_clock(request.vector_clock)

            res, err_message = self._do_verification(request, verify_functions)
            status.success = res
            status.error_message = err_message

            if status.success:
                return self._send_request_to_service(
                    stub_class=stub_class,
                    connection_string=connection_string,
                    method_name=method_name,
                    message=request
                )
            else:
                result = order_details.OrderResponce()
                result.status.CopyFrom(status)
                return result

        except Exception as e:
            logger.error(f"Failed to do items verification: {str(e)}")
            status.success = False
            status.error_message = f"Failed to do items verification: {str(e)}"

            result = order_details.OrderResponce()
            result.status.CopyFrom(status)
            return result


    def VerifyItems(self, request, context):
        return self._method_template(
            request=request,
            verify_functions=[lambda data: validate_order_list(data.items)],
            stub_class=transaction_verification_grpc.TransactionVerificationServiceStub,
            connection_string="transaction_verification:50052",
            method_name="VerifyCreditCard"
        )


    def VerifyCreditCard(self, request, context):
        return self._method_template(
            request=request,
            verify_functions=[
                lambda data: validate_credit_card(data.credit_card.number),
                lambda data: validate_credit_card_vendor(data.credit_card.number),
                lambda data: validate_expiration_date(data.credit_card.expiration_date),
                lambda data: validate_cvv(data.credit_card.cvv)
            ],
            stub_class=transaction_verification_grpc.TransactionVerificationServiceStub,
            connection_string="transaction_verification:50052",
            method_name="VerifyBillingAddress"
        )
    
    def VerifyBillingAddress(self, request, context):
        return self._method_template(
            request=request,
            verify_functions=[lambda data: validate_location(data.billing_address)],
            stub_class=transaction_verification_grpc.TransactionVerificationServiceStub,
            connection_string="transaction_verification:50052",
            method_name="SuccessfullVerify"
        )
    
    def SuccessfullVerify(self, request, context):
        status = order_details.StatusMessage(
            success=True,
            order_id=request.order_id,
            vector_clock=self.vector_clock
        )

        result = order_details.OrderResponce()
        result.status.CopyFrom(status)
        return result
    
def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    transaction_verification_grpc.add_TransactionVerificationServiceServicer_to_server(TransactionVerificationService(0, 3), server)
    port = "50052"
    server.add_insecure_port("[::]:" + port)
    server.start()
    logger.info(f"Server started. Listening on port {port}.")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
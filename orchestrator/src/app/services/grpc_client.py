import utils.pb.fraud_detection.fraud_detection_pb2 as fraud_detection
import utils.pb.fraud_detection.fraud_detection_pb2_grpc as fraud_detection_grpc
import utils.pb.transaction_verification.transaction_verification_pb2 as transaction_verification
import utils.pb.transaction_verification.transaction_verification_pb2_grpc as transaction_verification_grpc
import utils.pb.suggestions_service.suggestions_service_pb2 as suggestions_service
import utils.pb.suggestions_service.suggestions_service_pb2_grpc as suggestions_service_grpc
from utils.pb.transaction_verification.transaction_verification_pb2 import *
from utils.vector_clock.vector_clock import VectorClock

import grpc
from utils.logger import logger

logs = logger.get_module_logger("GRPC CLIENT")

def verify_transaction(vc_message: VectorClockMessage):
    logs.info("verify_transaction function triggered")
    with grpc.insecure_channel('transaction_verification:50052') as channel:
        stub = transaction_verification_grpc.TransactionServiceStub(channel)
        response = stub.verifyTransaction(vc_message)
    return response

def send_data(checkout_request, vector_clock: VectorClock):
    logs.info("send_data function triggered")
    user_info = checkout_request.get("user")
    credit_card_info = checkout_request.get("creditCard")
    billing_address_info = checkout_request.get("billingAddress")
    device_info = checkout_request.get("device")
    browser_info = checkout_request.get("browser")
    items_info = checkout_request.get("items", [])
    referrer_info = checkout_request.get("referrer")

    user_info_instance = UserData(name=user_info["name"], contact=user_info["contact"]) if user_info else None
    credit_card_info_instance = CreditCardData(number=credit_card_info["number"], expirationDate=credit_card_info["expirationDate"], cvv=credit_card_info["cvv"]) if credit_card_info else None
    billing_address_info_instance = BillingAddressData(street=billing_address_info["street"], city=billing_address_info["city"], state=billing_address_info["state"], zip=billing_address_info["zip"], country=billing_address_info["country"]) if billing_address_info else None
    device_info_instance = DeviceData(type=device_info["type"], model=device_info["model"], os=device_info["os"]) if device_info else None
    browser_info_instance = BrowserData(name=browser_info["name"], version=browser_info["version"]) if browser_info else None
    items_info_instance = [ItemData(name="suva", quantity="quantity")] if items_info else []
    vector_clock_message = VectorClockMessage(process_id=vector_clock.process_id, clock=vector_clock.clock, order_id=vector_clock.order_id)

    request = CheckoutRequest(
        user=user_info_instance,
        creditCard=credit_card_info_instance,
        billingAddress=billing_address_info_instance,
        device=device_info_instance,
        browser=browser_info_instance,
        items=items_info_instance,
        referrer=referrer_info,
        vector_clock=vector_clock_message
    )
    logs.info("Request compiled: %s", request)

    with grpc.insecure_channel('transaction_verification:50052') as channel:
        stub = transaction_verification_grpc.TransactionServiceStub(channel)
        response1: Determination = stub.sendData(request)
        logs.info("Transaction_verification replied")
    vc_1 = vc_msg_2_object(response1.vector_clock)
    vector_clock.merge(vc_1)
    vector_clock.update()

    logs.info("Data sent to transaction_verification")

    with grpc.insecure_channel('fraud_detection:50051') as channel:
        stub = fraud_detection_grpc.FraudServiceStub(channel)
        response2: Determination = stub.sendData(request)  # type Determination
    vc_2 = vc_msg_2_object(response2.vector_clock)
    vector_clock.merge(vc_2)
    vector_clock.update()

    with grpc.insecure_channel('suggestions_service:50053') as channel:
        stub = suggestions_service_grpc.SuggestionServiceStub(channel)
        response3: Determination = stub.sendData(request)
    vc_3 = vc_msg_2_object(response3.vector_clock)

    vector_clock.merge(vc_3)
    vector_clock.update()

    logs.info("Merging received vector clocks and local vector clock: %s %s", vc_1, vector_clock)
    logs.info("Merged 3 vector clocks")

    return vector_clock

def vc_msg_2_object(vcm: VectorClockMessage):
    logs.info("vc_msg_2_object called")
    logs.info("VectorClockMessage received: %s", vcm)
    vc = VectorClock(process_id=3, num_processes=4, order_id=vcm.order_id, clocks=vcm.clock)
    logs.info("VectorClock created from VectorClockMessage: %s", vc)
    return vc

def object_2_vc_msg(vc: VectorClock):
    vcm = VectorClockMessage()
    vcm.process_id = 1
    vcm.order_id = vc.order_id
    vcm.clock.extend(vc.clock)
    return vcm
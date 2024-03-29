import grpc

import utils.pb.fraud_detection.fraud_detection_pb2 as fraud_detection
import utils.pb.fraud_detection.fraud_detection_pb2_grpc as fraud_detection_grpc
import utils.pb.mq.mq_pb2 as mq
import utils.pb.mq.mq_pb2_grpc as mq_grpc
import utils.pb.suggestions_service.suggestions_service_pb2 as suggestions_service
import utils.pb.suggestions_service.suggestions_service_pb2_grpc as suggestions_service_grpc
import utils.pb.transaction_verification.transaction_verification_pb2 as transaction_verification
import utils.pb.transaction_verification.transaction_verification_pb2_grpc as transaction_verification_grpc
from utils.logger import logger
from utils.pb.fraud_detection.fraud_detection_pb2 import *

logs = logger.get_module_logger("GRPC CLIENT")


def greet(name='you'):
    # Establish a connection with the fraud-detection gRPC service.
    with grpc.insecure_channel('fraud_detection:50051') as channel:
        # Create a stub object.
        stub = fraud_detection_grpc.HelloServiceStub(channel)
        # Call the service through the stub object.
        response = stub.SayHello(fraud_detection.HelloRequest(name=name))
    return response.greeting


async def fraud(checkout_request):
    # Assuming you have the necessary import statements for the classes

    # Log the original checkout request
    logs.info("Original checkout request: %s", checkout_request)

    # Fetch values from checkout_request using get()
    user_info = checkout_request.get("user")
    credit_card_info = checkout_request.get("creditCard")
    billing_address_info = checkout_request.get("billingAddress")
    device_info = checkout_request.get("device")
    browser_info = checkout_request.get("browser")
    items_info = checkout_request.get("items", [])
    referrer_info = checkout_request.get("referrer")

    # Log the extracted information
    logs.info("User information: %s", user_info)
    logs.info("Credit Card information: %s", credit_card_info)
    logs.info("Billing Address information: %s", billing_address_info)
    logs.info("Device information: %s", device_info)
    logs.info("Browser information: %s", browser_info)
    logs.info("Items information: %s", items_info)
    logs.info("Referrer information: %s", referrer_info)

    user_info_instance = UserData(name=user_info["name"], contact=user_info["contact"]) if user_info else None
    logs.info("User information instance: %s", user_info_instance)

    credit_card_info_instance = CreditCardData(number=credit_card_info["number"], expirationDate=credit_card_info["expirationDate"],
                                               cvv=credit_card_info["cvv"]) if credit_card_info else None
    logs.info("Credit Card information instance: %s", credit_card_info_instance)
    billing_address_info_instance = BillingAddressData(street=billing_address_info["street"], city=billing_address_info["city"],
                                                       state=billing_address_info["state"], zip=billing_address_info["zip"],
                                                       country=billing_address_info["country"]) if billing_address_info else None
    logs.info("Billing Address information instance: %s", billing_address_info_instance)

    device_info_instance = DeviceData(type=device_info["type"], model=device_info["model"], os=device_info["os"]) if device_info else None
    logs.info("Device information instance: %s", device_info_instance)
    browser_info_instance = BrowserData(name=browser_info["name"], version=browser_info["version"]) if browser_info else None
    logs.info("Browser information instance: %s", browser_info_instance)

    items_info_instance = [ItemData(name="suva", quantity="quantity")] if items_info else []
    logs.info("Items information instances: %s", items_info_instance)

    request = CheckoutRequest(user=user_info_instance, creditCard=credit_card_info_instance, billingAddress=billing_address_info_instance,
        device=device_info_instance, browser=browser_info_instance, items=items_info_instance, referrer=referrer_info)

    # Log the created CheckoutRequest instance
    logs.info("Request compiled: %s", request)

    async with grpc.aio.insecure_channel('fraud_detection:50051') as channel:
        stub = fraud_detection_grpc.FraudServiceStub(channel)
        response = await stub.DetectFraud(request)
    return response.determination


async def verify_transaction(creditcard):
    async with grpc.aio.insecure_channel('transaction_verification:50052') as channel:
        stub = transaction_verification_grpc.TransactionServiceStub(channel)
        response = await stub.verifyTransaction(transaction_verification.CheckoutRequest(creditcard=creditcard))
    return response.determination


async def suggest(book_titles):
    async with grpc.aio.insecure_channel('suggestions_service:50053') as channel:
        stub = suggestions_service_grpc.SuggestionServiceStub(channel)
        response = await stub.Suggest(suggestions_service.SuggestionRequest(book_titles=["123", "233"]))
    return response.book_suggestions


async def order(creditcard, priority=1000):
    async with grpc.aio.insecure_channel('queue:50055') as channel:
        stub = mq_grpc.MQServiceStub(channel)
        response = await stub.enqueue(mq.CheckoutRequest(priority=priority, creditcard=creditcard))
    return response.error, response.error_message

# Import Flask.
# Flask is a web framework for Python.
# It allows you to build a web application quickly.
# For more information, see https://flask.palletsprojects.com/en/latest/
from flask import Flask, request
from flask_cors import CORS
from flask.logging import default_handler

import json
import asyncio
import sys
import os
import uuid

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
utils_path = os.path.abspath(os.path.join(FILE, '../../../utils/'))
sys.path.insert(0, utils_path)
from log_utils.logger import setup_logger
logger = setup_logger("Orchestrator")
logger.addHandler(default_handler)

# import pb.transaction_verification.transaction_verification_pb2 as transaction_verification
# import pb.transaction_verification.transaction_verification_pb2_grpc as transaction_verification_grpc
# import pb.order_details.order_details_pb2 as order_details

import pb.services.transaction_verification_pb2 as transaction_verification
import pb.services.transaction_verification_pb2_grpc as transaction_verification_grpc
import pb.services.fraud_detection_pb2 as fraud_detection
import pb.services.fraud_detection_pb2_grpc as fraud_detection_grpc
import pb.services.recommendation_system_pb2 as recommendation_system
import pb.services.recommendation_system_pb2_grpc as recommendation_system_grpc
import pb.services.order_queue_pb2 as order_queue
import pb.services.order_queue_pb2_grpc as order_queue_grpc
import pb.services.order_details_pb2 as order_details

import grpc

# Create a simple Flask app.
app = Flask(__name__)
# Enable CORS for the app.
CORS(app, resources={r'/*': {'origins': '*'}})


# Define a GET endpoint.
@app.route('/', methods=['GET'])
def index():
    """
    Responds with 'Hello, [name]' when a GET request is made to '/' endpoint.
    """
    # Test the fraud-detection gRPC service.
    # response = greet(name='orchestrator')
    # # Return the response.
    # return response
    return "hello from orchestrator"

def create_input_order_details(request_data, order_id):
    user_info = order_details.User(**request_data["user"])
    credit_card_info = order_details.CreditCard(
        number=request_data["creditCard"]["number"],
        expiration_date=request_data["creditCard"]["expirationDate"],
        cvv=request_data["creditCard"]["cvv"]
    )
    items = [order_details.OrderItem(**item) for item in request_data["items"]]
    billing_address_info = order_details.BillingAddress(**request_data["billingAddress"])
    return order_details.InputOrderDetails(
        order_id=order_id,
        user=user_info,
        credit_card=credit_card_info,
        user_comment=request_data["userComment"] or "",
        items=items,
        billing_address=billing_address_info,
        shipping_method=request_data["shippingMethod"],
        gift_wrapping=request_data["giftWrapping"],
        terms_accepted=request_data["termsAccepted"]
    )

async def add_to_order_queue(order_details):
    async with grpc.aio.insecure_channel('order_queue:50054') as channel:
        stub = order_queue_grpc.OrderQueueServiceStub(channel)
        response = await stub.Enqueue(order_details)
    logger.info(f"Added order with ID: {order_details.order_id} to the queue")
    return response

async def init_transaction(request_data, order_id, connection_string, stub_class):
    async with grpc.aio.insecure_channel(connection_string) as channel:
        stub = stub_class(channel)
        input_order_details = create_input_order_details(request_data, order_id)
        response = await stub.InitTransaction(input_order_details)
    logger.info(f"InitTransaction - Order ID: {order_id}, Service: {connection_string}, Done")
    return response

async def clear_transaction(order_id, connection_string, stub_class):
    async with grpc.aio.insecure_channel(connection_string) as channel:
        stub = stub_class(channel)
        request = order_details.OperationalMessage(
            order_id=order_id,
        )
        response = await stub.ClearTransaction(request)
    logger.info(f"ClearTransaction - Order ID: {order_id}, Service: {connection_string}, Done")
    return response

async def call_action(order_id, connection_string, stub_class, method_name, vector_clock=[0,0,0]):
    async with grpc.aio.insecure_channel(connection_string) as channel:
        stub = stub_class(channel)
        fraud_request = order_details.OperationalMessage(
            order_id=order_id,
            vector_clock=vector_clock,
        )
        method = getattr(stub, method_name)
        response = await method(fraud_request)

    return response

def merge_into_general_vector_clock(general_vector_clock, *results):
    for result in results:
        general_vector_clock = [max(general_vector_clock[i], result.status.vector_clock[i]) for i in range(len(general_vector_clock))]
    logger.info(f"Vector clock after operations: {general_vector_clock}")
    return general_vector_clock

async def call_parallel_services(general_vector_clock, *services):
    results = await asyncio.gather(*services)
    all_success = all(result.status.success for result in results)
    if not all_success:
        error_messages = [result.status.error_message for result in results if not result.status.success]
        return general_vector_clock, "; ".join(error_messages)
    general_vector_clock = merge_into_general_vector_clock(general_vector_clock, *results)
    return general_vector_clock, ""

async def clear_parallel_services(order_id):
    return await asyncio.gather(
        clear_transaction(order_id, "transaction_verification:50052", transaction_verification_grpc.TransactionVerificationServiceStub),
        clear_transaction(order_id, "fraud_detection:50051", fraud_detection_grpc.FraudDetectionServiceStub),
        #clear_transaction(order_id, "recommendation_system:50053", recommendation_system_grpc.RecommendationServiceStub),
    )

@app.route('/checkout', methods=['POST'])
async def checkout():
    """
    Responds with a JSON object containing the order ID, status, and suggested books.
    """
    request_data = json.loads(request.data)
    logger.info(f"Request Data: {request_data.get('items')}")

    general_vector_clock = [0, 0, 0]
    order_id = str(uuid.uuid4())
    suggested_books = []
    order_response = {
        'orderId': order_id,
        'suggestedBooks': suggested_books
    }

    _ = await asyncio.gather(
        init_transaction(request_data, order_id, "transaction_verification:50052", transaction_verification_grpc.TransactionVerificationServiceStub),
        init_transaction(request_data, order_id, "fraud_detection:50051", fraud_detection_grpc.FraudDetectionServiceStub),
        #init_transaction(request_data, order_id, "recommendation_system:50053", recommendation_system_grpc.RecommendationServiceStub),
    )
    
    general_vector_clock, error_message = await call_parallel_services(
        general_vector_clock,
        call_action(order_id, "transaction_verification:50052", transaction_verification_grpc.TransactionVerificationServiceStub, "VerifyItems", vector_clock=general_vector_clock),
        call_action(order_id, "fraud_detection:50051", fraud_detection_grpc.FraudDetectionServiceStub, "CheckKnownFraudUsers", vector_clock=general_vector_clock),
        call_action(order_id, "fraud_detection:50051", fraud_detection_grpc.FraudDetectionServiceStub, "CheckKnownFraudLocations", vector_clock=general_vector_clock),
    )
    if error_message:
        _ = await clear_parallel_services(order_id)
        order_response["status"] = "Order Denied"
        order_response["errorMessage"] = error_message
        return order_response
    
    general_vector_clock, error_message = await call_parallel_services(
        general_vector_clock,
        call_action(order_id, "transaction_verification:50052", transaction_verification_grpc.TransactionVerificationServiceStub, "VerifyCreditCard", vector_clock=general_vector_clock),
        call_action(order_id, "transaction_verification:50052", transaction_verification_grpc.TransactionVerificationServiceStub, "VerifyBillingAddress", vector_clock=general_vector_clock),
        call_action(order_id, "fraud_detection:50051", fraud_detection_grpc.FraudDetectionServiceStub, "CheckGeneralFraud", vector_clock=general_vector_clock),
    )
    if error_message:
        _ = await clear_parallel_services(order_id)
        order_response["status"] = "Order Denied"
        order_response["errorMessage"] = error_message
        return order_response
    
    order_response["status"] = "Order Approved"
    """
    results = await asyncio.gather(
        call_action(order_id, "recommendation_system:50053", recommendation_system_grpc.RecommendationServiceStub, "GetRecommendations", vector_clock=general_vector_clock),
    )
    general_vector_clock = merge_into_general_vector_clock(general_vector_clock, *results)
    recommended_books = results[0].recommended_books
    order_response["suggestedBooks"] = [book.title for book in recommended_books]
    """
    _ = await clear_parallel_services(order_id)
    await add_to_order_queue(create_input_order_details(request_data, order_id))
    return order_response



if __name__ == '__main__':
    # Run the app in debug mode to enable hot reloading.
    # This is useful for development.
    # The default port is 5000.
    app.run(host='0.0.0.0')

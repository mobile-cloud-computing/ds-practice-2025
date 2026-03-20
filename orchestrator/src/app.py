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

# from fraud_detection import check_fraud
# from transaction_verification import verify_transaction
# from recommendation import get_recommendations

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
utils_path = os.path.abspath(os.path.join(FILE, '../../../utils/'))
sys.path.insert(0, utils_path)
from log_utils.logger import setup_logger
logger = setup_logger("Orchestrator")
logger.addHandler(default_handler)

# import pb.transaction_verification.transaction_verification_pb2 as transaction_verification
# import pb.transaction_verification.transaction_verification_pb2_grpc as transaction_verification_grpc
# import pb.order_details.order_details_pb2 as order_details

import pb.transaction_verification_pb2 as transaction_verification
import pb.transaction_verification_pb2_grpc as transaction_verification_grpc
import pb.order_details_pb2 as order_details

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

def transform_results(results: list[dict]):
    return {
        result["service"]: result["data"]
        for result in results
    }


async def init_transaction(request_data, order_id, connection_string, stub_class):
    async with grpc.aio.insecure_channel(connection_string) as channel:
        stub = stub_class(channel)
        user_info = order_details.User(**request_data["user"])
        credit_card_info = order_details.CreditCard(
            number=request_data["creditCard"]["number"],
            expiration_date=request_data["creditCard"]["expirationDate"],
            cvv=request_data["creditCard"]["cvv"]
        )
        items = [order_details.OrderItem(**item) for item in request_data["items"]]
        billing_address_info = order_details.BillingAddress(**request_data["billingAddress"])
        fraud_request = order_details.InputOrderDetails(
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
        response = await stub.InitTransaction(fraud_request)
    
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



@app.route('/checkout', methods=['POST'])
async def checkout():
    """
    Responds with a JSON object containing the order ID, status, and suggested books.
    """
    # Get request object data to json
    request_data = json.loads(request.data)
    # Print request object data
    logger.info(f"Request Data: {request_data.get('items')}")

    order_id = '12345'
    suggested_books = []

    # parallel_results = await asyncio.gather(
    #     check_fraud(request_data),
    #     verify_transaction(request_data),
    # )
    # results = transform_results(parallel_results)

    statuses = await asyncio.gather(
        init_transaction(request_data, order_id, "transaction_verification:50052", transaction_verification_grpc.TransactionVerificationServiceStub)
    )


    order_response = {
        'orderId': order_id,
        'suggestedBooks': suggested_books
    }

    # Call the action with the appropriate parameters.
    results = await asyncio.gather(
        call_action(order_id, "transaction_verification:50052", transaction_verification_grpc.TransactionVerificationServiceStub, "VerifyItems", vector_clock=[0,0,0])
    )
    result = results[0]

    if not result.status.success:
        order_response["status"] = "Order Denied"
        order_response["errorMessage"] = result.status.error_message
    else:
        order_response["status"] = "Order Approved"

    # if results["fraud_detection"]["is_fraud"]:
    #     order_response["status"] = "Order Denied"
    #     order_response["errorMessage"] = results['fraud_detection']['error_message']
    # elif not results["transaction_verification"]["transaction_valid"]:
    #     order_response["status"] = "Order Denied"
    #     order_response["errorMessage"] = results['transaction_verification']['error_message']
    # else:
    #     order_response["status"] = "Order Approved"
    #     recommendation_result = await get_recommendations(request_data)
    #     order_response["suggestedBooks"] = recommendation_result["data"]["suggested_books"]


    
    return order_response



if __name__ == '__main__':
    # Run the app in debug mode to enable hot reloading.
    # This is useful for development.
    # The default port is 5000.
    app.run(host='0.0.0.0')

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

from fraud_detection import check_fraud
from transaction_verification import verify_transaction
from recommendation import get_recommendations

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
utils_path = os.path.abspath(os.path.join(FILE, '../../../utils/'))
sys.path.insert(0, utils_path)
from log_utils.logger import setup_logger
logger = setup_logger("Orchestrator")
logger.addHandler(default_handler)

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

    parallel_results = await asyncio.gather(
        check_fraud(request_data),
        verify_transaction(request_data),
    )
    results = transform_results(parallel_results)

    order_response = {
        'orderId': order_id,
        'suggestedBooks': suggested_books
    }

    if results["fraud_detection"]["is_fraud"]:
        order_response["status"] = "Order Denied"
        order_response["errorMessage"] = results['fraud_detection']['error_message']
    elif not results["transaction_verification"]["transaction_valid"]:
        order_response["status"] = "Order Denied"
        order_response["errorMessage"] = results['transaction_verification']['error_message']
    else:
        order_response["status"] = "Order Approved"
        recommendation_result = await get_recommendations(request_data)
        order_response["suggestedBooks"] = recommendation_result["data"]["suggested_books"]
    
    return order_response



if __name__ == '__main__':
    # Run the app in debug mode to enable hot reloading.
    # This is useful for development.
    # The default port is 5000.
    app.run(host='0.0.0.0')

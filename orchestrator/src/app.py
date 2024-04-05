import json
import os
import sys

# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")

# NOTE: The following lines are added to resolve module resolution issue
# DO NOT REMOVE 
sys.path.insert(0, os.path.abspath(os.path.join(FILE, "../../../utils/pb/order_mq")))
import order_mq_pb2 as order_mq
import order_mq_pb2_grpc as order_mq_grpc

sys.path.insert(0, os.path.abspath(os.path.join(FILE, "../../../utils/pb/book_recommendation")))
import book_recommendation_pb2 as book_recommendation
import book_recommendation_pb2_grpc as book_recommendation_grpc

sys.path.insert(0, os.path.abspath(os.path.join(FILE, "../../../utils/pb/fraud_detection")))
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc

sys.path.insert(0, os.path.abspath(os.path.join(FILE, "../../../utils/pb/transaction_verification")))
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc


clients_path = os.path.abspath(os.path.join(FILE, "../../../utils/clients"))
sys.path.insert(0, clients_path)

import order_mq as order_mq_client
import book_recommendation as book_recommendation_client
import fraud_detection as fraud_detection_client
import transaction_verification as transaction_verification_client

config_path = os.path.abspath(os.path.join(FILE, "../../../utils/config"))
sys.path.insert(0, config_path)

import log_configurator

import logging

# ruff : noqa: E402
import traceback
from concurrent.futures import ThreadPoolExecutor

relative_modules_path = os.path.abspath(
    os.path.join(FILE, "../../../orchestrator/src")
)
sys.path.insert(0, relative_modules_path)
import data_store as store
from exceptions import FraudActivityException
from flask import Flask, jsonify, request
from flask_cors import CORS
from google.protobuf.json_format import MessageToJson

_TRANSACTION_VC_INDEX = 0
_FRAUD_DETECTION_VC_INDEX = 1
_BOOK_RECOMMENDATION_VC_INDEX = 2

_VECTOR_CLOCK = [0,0,0]

# read comma sepatrated ORDER_EXECUTORS from environment variable
ORDER_EXECUTORS = os.getenv("ORDER_EXECUTORS", "").split(",")
logging.info(f"ORDER_EXECUTORS: {ORDER_EXECUTORS}")
ignored_paths = ["favicon.ico"]
log_configurator.configure(
    "/app/logs/orchestrator.info.log", "/app/logs/orchestrator.error.log"
)


def is_ignored_path(path):
    return any([path in request.path for path in ignored_paths])


app = Flask(__name__)
CORS(app)


@app.before_request
def before_request():
    if is_ignored_path(request.path):
        return
    logging.info("Received request: %s %s", request.method, request.path)


@app.after_request
def after_request(response):
    if is_ignored_path(request.path):
        return response

    if request.path in ignored_paths:
        return response

    logging.info(
        "path: %s | method: %s | scheme: %s | status: %s | size: %s | remote addr: %s",
        request.path,
        request.method,
        request.scheme,
        response.status,
        response.content_length,
        request.remote_addr
    )
    return response


@app.errorhandler(Exception)
def exceptions(e):
    if is_ignored_path(request.path):
        return "Internal Server Error", 500

    tb = traceback.format_exc()
    logging.error(
        "%s %s %s %s \n%s",
        request.remote_addr,
        request.method,
        request.scheme,
        request.full_path,
        tb,
    )
    if isinstance(e, FraudActivityException):
        return "Fraudulent activity detected", 400
    return "Internal Server Error", 500


@app.route("/", methods=["GET"])
def index():
    """
    Responds with a list of books.
    """
    return jsonify(store.get_books())


@app.route("/books", methods=["GET"])
def books():
    """
    Responds with a list of books.
    """
    return jsonify(store.get_books())


@app.route("/order_executors", methods=["GET"])
def order_executors():
    """
    Responds with a list of executors.
    """
    print(f"ORDER_EXECUTORS: {ORDER_EXECUTORS}")
    return jsonify(ORDER_EXECUTORS)


@app.route("/books/<book_id>", methods=["GET"])
def book(book_id):
    """
    Responds with a book.
    """
    return jsonify(store.get_book_by_id(book_id))


@app.route("/checkout", methods=["POST"])
def checkout():
    """
    Responds with a JSON object containing the order ID, status, and suggested books.
    """

    jsonRequest = request.json
    bookNames = [book["name"] for book in jsonRequest["items"]]
    books = store.get_books_by_names(bookNames)
    bookIds = [book["id"] for book in books]
    if bookIds is None or len(bookIds) == 0:
        raise Exception("No books found")

  
    transaction = transaction_verification_client.verify_transaction(
        {
            "cardNumber": jsonRequest["creditCard"]["number"],
            "expirationDate": jsonRequest["creditCard"]["expirationDate"],
            "cvv": jsonRequest["creditCard"]["cvv"],
        }
    )
    book_res = book_recommendation_client.get_recommendations(bookIds)
    fraud_res = fraud_detection_client.check_fraud(request.json)

    if fraud_res.isFraud:
        raise FraudActivityException()

    msg_obj = json.loads(MessageToJson(book_res))

    order_mq_client.enqueue_order(
        {
            "order_id": transaction.transactionId,
            "order_data": json.dumps(jsonRequest),
        }
    )

    order_status_response = {
        "orderId": transaction.transactionId,
        "status": "Order Approved",
        "suggestedBooks": msg_obj["recommendations"],
    }

    return jsonify(order_status_response)


@app.route("/error", methods=["GET"])
def error():
    """
    Responds with a 500 error.
    """
    raise Exception("Internal Server Error")


@app.route("/health", methods=["GET"])
def health():
    """
    Responds with the health status of the orchestrator and the fraud-detection and recommendation gRPC services.
    """

    def run_health_check(service, name):
        status = service.health_check()
        return name, status

    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(
                run_health_check, fraud_detection_client, "fraud_detection"
            ),
            executor.submit(
                run_health_check, book_recommendation_client, "book_recommendation"
            ),
            executor.submit(
                run_health_check,
                transaction_verification_client,
                "transaction_verification",
            ),
        ]
        statuses = {future.result()[0]: future.result()[1] for future in futures}

    statuses["orchestrator"] = "Healthy"

    # Overall status is healthy if all the services are healthy, otherwise it's unhealthy
    overall_status = (
        "Healthy"
        if all(status == "Healthy" for status in statuses.values())
        else "Unhealthy"
    )

    health = {
        "status": overall_status,
        "services": statuses,
    }

    return jsonify(health)


if __name__ == "__main__":
    # Run the app in debug mode to enable hot reloading.
    # This is useful for development.
    # The default port is 5000.
    app.run(host="0.0.0.0")

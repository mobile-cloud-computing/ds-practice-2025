import os
import sys

# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
relative_modules_path = os.path.abspath(os.path.join(FILE, "../../../orchestrator/src"))
sys.path.insert(0, relative_modules_path)

import logging

# ruff : noqa: E402
import traceback
from concurrent.futures import ThreadPoolExecutor
from logging.config import dictConfig

import data_store as store
from flask import Flask, jsonify, request
from flask_cors import CORS

import book_recommendation
import fraud_detection
import transaction_verification

dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": True,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
            },
            "access": {
                "format": "%(message)s",
            },
        },
        "handlers": {
            "console": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "default",
                "filename": "/app/logs/orchestrator.error.log",
                "maxBytes": 10000,
                "backupCount": 10,
                "delay": "True",
                "level": "ERROR",
            },
            "info_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "access",
                "filename": "/app/logs/orchestrator.access.log",
                "maxBytes": 10000,
                "backupCount": 10,
                "delay": "True",
                "level": "INFO",
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["console", "info_file", "error_file"],
        },
    }
)

app = Flask(__name__)
CORS(app)


@app.before_request
def before_request():
    logging.info("Before handling the request")


@app.after_request
def after_request(response):
    logging.info(
        "path: %s | method: %s | scheme: %s | status: %s | size: %s | remote addr: %s",
        request.path,
        request.method,
        request.scheme,
        response.status,
        response.content_length,
        request.remote_addr,
    )
    return response


@app.errorhandler(Exception)
def exceptions(e):
    tb = traceback.format_exc()
    logging.error(
        "%s %s %s %s \n%s",
        request.remote_addr,
        request.method,
        request.scheme,
        request.full_path,
        tb,
    )
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


@app.route("/books/<book_id>", methods=["GET"])
def book(book_id):
    """
    Responds with a book.
    """
    return jsonify(store.get_book_by_id(book_id))


@app.route("/recommendations", methods=["POST"])
def recommendations():
    """
    Responds with a list of recommended books.
    """
    return jsonify(book_recommendation.get_recommendations())


@app.route("/checkout", methods=["POST"])
def checkout():
    """
    Responds with a JSON object containing the order ID, status, and suggested books.
    """
    # Dummy response following the provided YAML specification for the bookstore
    # TODO:
    # 1. Check fraud
    # 2. Verify transaction
    # 3. Get recommendations
    # 2,3 can be done in parallel

    fraud_detection_response = fraud_detection.check_fraud(request.json)
    logging.info("fraud detection resultL %s", fraud_detection_response)
    requestJson = request.json
    order_status_response = {
        "orderId": "1234567890",
        "status": "Order Approved",
        "suggestedBooks": [
            {"bookId": "123", "title": "Dummy Book 1", "author": "Author 1"},
            {"bookId": "456", "title": "Dummy Book 2", "author": "Author 2"},
        ],
    }

    return order_status_response


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
        # Run the health checks in separate threads
        futures = [
            executor.submit(run_health_check, fraud_detection, "fraud_detection"),
            executor.submit(
                run_health_check, book_recommendation, "book_recommendation"
            ),
            executor.submit(
                run_health_check, transaction_verification, "transaction_verification"
            ),
        ]

        # Collect the results
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

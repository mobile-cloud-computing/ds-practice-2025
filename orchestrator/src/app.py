import os
import sys

# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")

relative_modules_path = os.path.abspath(os.path.join(FILE, "../../../orchestrator/src"))
sys.path.insert(0, relative_modules_path)

# ruff : noqa: E402
from flask import Flask
from flask_cors import CORS

import book_recommendation
import fraud_detection

app = Flask(__name__)
# Enable CORS for the app.
CORS(app)


@app.route("/", methods=["GET"])
def index():
    """
    Responds with 'Hello, [name]' when a GET request is made to '/' endpoint.
    """
    # Test the fraud-detection gRPC service.
    response = fraud_detection.greet(name="orchestrator")
    # Return the response.
    return response


@app.route("/checkout", methods=["POST"])
def checkout():
    """
    Responds with a JSON object containing the order ID, status, and suggested books.
    """
    # Dummy response following the provided YAML specification for the bookstore
    order_status_response = {
        "orderId": "12345",
        "status": "Order Approved",
        "suggestedBooks": [
            {"bookId": "123", "title": "Dummy Book 1", "author": "Author 1"},
            {"bookId": "456", "title": "Dummy Book 2", "author": "Author 2"},
        ],
    }

    return order_status_response


@app.route("/health", methods=["GET"])
def health():
    """
    Responds with the health status of the orchestrator and the fraud-detection and recommendation gRPC services.
    """
    fraud_detection_status = fraud_detection.health_check()
    recommendation_status = book_recommendation.health_check()

    return {
        "fraudDetection": fraud_detection_status,
        "recommendation": recommendation_status,
        "orchestrator": "Healthy",
    }


if __name__ == "__main__":
    # Run the app in debug mode to enable hot reloading.
    # This is useful for development.
    # The default port is 5000.
    app.run(host="0.0.0.0")

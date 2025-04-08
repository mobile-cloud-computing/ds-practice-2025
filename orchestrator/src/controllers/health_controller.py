import logging
from flask import Blueprint, request, current_app, jsonify

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "ok"}), 200


@api_bp.route("/greet", methods=["GET"])
def greet():
    """
    Greet endpoint that calls the fraud detection gRPC service.

    Returns:
        A greeting message from the fraud detection service.
    """
    try:
        # Get parameters
        username = request.args.get("name", "Guest")

        # Return response
        return jsonify({"greeting": username}), 200

    except Exception as e:
        logging.exception(f"Unexpected error in greet endpoint: {str(e)}")
        return jsonify(
            {
                "error": "Internal server error",
                "message": "An unexpected error occurred",
            }
        ), 500


@api_bp.route("/", methods=["GET"])
def index():
    """Root endpoint that redirects to the greet endpoint."""
    return greet()

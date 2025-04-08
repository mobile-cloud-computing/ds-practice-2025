import os
import sys
import logging

from flask import Flask
from flask_cors import CORS

from error_handlers import register_error_handlers
from grpc_client_factory import GrpcClientFactory

from utils.logging import configure_logging

logger = logging.getLogger(__name__)

FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
grpc_path = os.path.abspath(os.path.join(FILE, "../../../utils/pb/fraud_detection"))
vector_clock_path = os.path.abspath(os.path.join(FILE, "../../../utils/vector_clock"))
sys.path.insert(0, grpc_path)
sys.path.insert(0, vector_clock_path)

import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc

def greet(grpc_factory, name="you"):
    try:
        # Get the appropriate stub
        stub = grpc_factory.get_stub(
            "fraud_detection", fraud_detection_grpc.FraudDetectionServiceStub, secure=False
        )

        # Make the call with timeout
        response = stub.SayHello(
            fraud_detection.HelloRequest(name=name),
            timeout=grpc_factory.default_timeout,
        )
        return response.greeting
    except fraud_detection_grpc.RpcError as e:
        logging.error(f"gRPC error: {e.code()}: {e.details()}")
        raise


def create_app(config_object="config.default"):
    app = Flask(__name__)

    configure_logging(app)

    configure_cors(app)

    app.config.from_object(config_object)

    register_blueprints(app)

    register_grpc(app)

    register_vector_clock(app)

    register_error_handlers(app)

    return app


def register_grpc(app):
    app.grpc_factory = GrpcClientFactory()


def register_vector_clock(app):
    FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
    vector_clock_path = os.path.abspath(
        os.path.join(FILE, f"../../../utils/vector_clock")
    )
    sys.path.insert(0, vector_clock_path)

    from vector_clock import OrderEventTracker

    app.order_event_tracker = OrderEventTracker()


def register_blueprints(app):
    blueprints = [
        ("controllers.bookstore_controller", "bookstore_bp"),
        ("controllers.fintech_controller", "fintech_bp"),
        ("controllers.health_controller", "api_bp"),
    ]

    for module_path, bp_name in blueprints:
        module = __import__(module_path, fromlist=[bp_name])
        blueprint = getattr(module, bp_name)
        app.register_blueprint(blueprint)


def configure_cors(app):
    """Configure CORS."""
    origins = app.config.get("CORS_ORIGINS", "*")
    CORS(app, resources={r"/*": {"origins": origins}})
    logging.info(f"CORS configured with origins: {origins}")


app = create_app()


if __name__ == "__main__":
    # Run the app in debug mode to enable hot reloading.
    # This is useful for development.
    # The default port is 5000.
    app.run(host="0.0.0.0")

import os
import sys

import grpc

FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
utils_path = os.path.abspath(os.path.join(FILE, "../pb/fraud_detection"))
sys.path.insert(0, utils_path)

# ruff : noqa: E402
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc

_FRAUD_DETECTION_SERVICE = "fraud_detection:50051"


def greet(name="you"):
    try:
        with grpc.insecure_channel(_FRAUD_DETECTION_SERVICE) as channel:
            stub = fraud_detection_grpc.HelloServiceStub(channel)
            response = stub.SayHello(fraud_detection.HelloRequest(name=name))
        return response.greeting
    except Exception as e:
        return f"Unhealthy: {e}"


def health_check():
    with grpc.insecure_channel(_FRAUD_DETECTION_SERVICE) as channel:
        stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
        response = stub.HealthCheck(fraud_detection.HealthCheckRequest())
    return response.status


def check_fraud(transaction, vector_clock = []):
    transaction["vector_clock"] = vector_clock
    with grpc.insecure_channel(_FRAUD_DETECTION_SERVICE) as channel:
        stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
        response = stub.CheckFraud(fraud_detection.FraudRequest(**transaction))
    return response

import os
import sys

FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")

relative_modules_path = os.path.abspath(
    os.path.join(FILE, "../../../fraud_detection/src")
)
sys.path.insert(0, relative_modules_path)
from model import FraudDetectionModel

utils_path = os.path.abspath(os.path.join(FILE, "../../../utils/pb/fraud_detection"))
sys.path.insert(0, utils_path)
# ruff : noqa: E402
from concurrent import futures

import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc
import grpc

fraud_detection_model = FraudDetectionModel()


def fraud_check(input):
    return fraud_detection_model.check_fraud(input)


class FraudDetectionService(fraud_detection_grpc.FraudDetectionServiceServicer):
    def CheckFraud(self, request, context):
        response = fraud_detection.FraudResponse()
        cardInfo = request.creditCard.number
        fraud = fraud_check(cardInfo)
        response.isFraud = fraud["is_fraud"]
        response.message = (
            "Fraud Detected" if fraud["is_fraud"] else "No Fraud Detected"
        )
        return response

    def HealthCheck(self, request, context):
        return fraud_detection.HealthCheckResponse(status="Healthy")


def serve():
    sample = fraud_detection_model.check_fraud("1234567890")
    print(f"fraud detection model is ready check: {sample}")
    server = grpc.server(futures.ThreadPoolExecutor())
    fraud_detection_grpc.add_FraudDetectionServiceServicer_to_server(
        FraudDetectionService(), server
    )
    port = "50051"
    server.add_insecure_port("[::]:" + port)
    server.start()
    print(f"Server started. Listening on port {port}.")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

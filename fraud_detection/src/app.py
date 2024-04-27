import os
import sys
from pathlib import Path

FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
APP_DIR = Path(FILE).resolve().parents[2]

sys.path.append(str(APP_DIR / "utils/config"))
sys.path.append(str(APP_DIR / "utils/pb/fraud_detection"))
sys.path.append(str(APP_DIR / "fraud_detection/src"))


import log_configurator
from model import FraudDetectionModel

# ruff : noqa: E402
from concurrent import futures

import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc
import grpc

log_configurator.configure(
    "/app/logs/fraud_detection.info.log", "/app/logs/fraud_detection.error.log"
)


_VECTOR_CLOCK_INDEX = 1
_CURRENT_VECTOR_CLOCK = [0, 0, 0]

fraud_detection_model = FraudDetectionModel()


def fraud_check(input):
    return fraud_detection_model.check_fraud(input)


class FraudDetectionService(fraud_detection_grpc.FraudDetectionServiceServicer):
    def CheckFraud(self, request, context):
        global _CURRENT_VECTOR_CLOCK
        vector_clock = request.vector_clock
        if vector_clock is not None and len(vector_clock) > 0:
            _CURRENT_VECTOR_CLOCK = [
                max(a, b) for a, b in zip(_CURRENT_VECTOR_CLOCK, vector_clock)
            ]
        _CURRENT_VECTOR_CLOCK[_VECTOR_CLOCK_INDEX] += 1

        response = fraud_detection.FraudResponse()
        cardInfo = request.creditCard.number
        fraud = fraud_check(cardInfo)
        response.isFraud = fraud["is_fraud"]
        response.message = (
            "Fraud Detected" if fraud["is_fraud"] else "No Fraud Detected"
        )
        response.vector_clock.extend(vector_clock)
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

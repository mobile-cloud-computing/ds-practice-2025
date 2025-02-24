import sys
import os

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
fraud_detection_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/fraud_detection'))
sys.path.insert(0, fraud_detection_grpc_path)
from fraud_detection_pb2 import FraudDetectionRequest, FraudDetectionResponse
from fraud_detection_pb2_grpc import FraudDetectionServiceServicer, add_FraudDetectionServiceServicer_to_server
import grpc
from concurrent import futures

class FraudDetectionServiceService(FraudDetectionServiceServicer):
     def DetectFraud(self, request: FraudDetectionRequest, context):
        print(f"Incoming request {request}")
        response = FraudDetectionResponse()
        response.isFraudulent = request.telemetry.browser.name == "IE"
        response.reason = "We do not support IE (based)"
        return response

def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor())
    add_FraudDetectionServiceServicer_to_server(FraudDetectionServiceService(), server)
    port = "50051"
    server.add_insecure_port("[::]:" + port)
    server.start()
    print(f"Server started. Listening on port {port}.")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
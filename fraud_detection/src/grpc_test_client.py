import grpc
import os
import sys

FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
grpc_path = os.path.abspath(os.path.join(FILE, "../../../utils/pb/fraud_detection"))
sys.path.insert(0, grpc_path)


import fraud_detection_pb2 as fd_pb2
import fraud_detection_pb2_grpc as fd_pb2_grpc

def run():
    channel = grpc.insecure_channel("localhost:50051")  # Connect to gRPC server
    stub = fd_pb2_grpc.FraudDetectionStub(channel)

    request = fd_pb2.FraudRequest(
        order_id="12345",
        user_id="user_789",
        amount=10000,  # Large amount to trigger fraud
        payment_method="Crypto",
        location="North Korea"
    )

    response = stub.CheckFraud(request)
    print(f"Fraudulent: {response.is_fraudulent}, Reason: {response.reason}")

if __name__ == "__main__":
    run()

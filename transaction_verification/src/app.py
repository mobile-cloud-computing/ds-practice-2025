import os
import sys

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
utils_path = os.path.abspath(
    os.path.join(FILE, "../../../utils/pb/transaction_verification")
)
sys.path.insert(0, utils_path)

# ruff : noqa: E402
from concurrent import futures

import grpc
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc


class TransactionVerificationService(
    transaction_verification_grpc.TransactionServiceServicer
):
    def VerifyTransaction(self, request, context):
        dummy_response = transaction_verification.TransactionResponse()
        dummy_response.status = "Success"
        return dummy_response

    def HealthCheck(self, request, context):
        return transaction_verification.HealthCheckResponse(status="Healthy")


def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    transaction_verification_grpc.add_TransactionServiceServicer_to_server(
        TransactionVerificationService(), server
    )
    port = "50052"
    server.add_insecure_port("[::]:" + port)
    server.start()
    print(f"Server started. Listening on port {port}.")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

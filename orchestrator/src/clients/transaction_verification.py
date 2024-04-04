import os
import sys

FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
book_recommendation_path = os.path.abspath(
    os.path.join(FILE, "../../../../utils/pb/transaction_verification")
)

sys.path.insert(0, book_recommendation_path)

# ruff : noqa: E402
import grpc
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc

_TRANSACTION_VERIFICATION_SERVICE = "transaction_verification:50052"


def health_check():
    try:
        with grpc.insecure_channel(_TRANSACTION_VERIFICATION_SERVICE) as channel:
            stub = transaction_verification_grpc.TransactionServiceStub(channel)
            print("Sending health check request to transaction_verification service")
            response = stub.HealthCheck(transaction_verification.HealthCheckRequest())

        return response.status
    except Exception as e:
        return f"Unhealthy: {e}"


def verify_transaction(transaction):
    with grpc.insecure_channel(_TRANSACTION_VERIFICATION_SERVICE) as channel:
        stub = transaction_verification_grpc.TransactionServiceStub(channel)
        response = stub.VerifyTransaction(
            transaction_verification.TransactionRequest(**transaction)
        )
    return response

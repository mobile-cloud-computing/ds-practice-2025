import sys
import os
import grpc
from concurrent import futures

# Import the generated gRPC stubs
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
transaction_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/transaction_verification'))
sys.path.insert(0, transaction_grpc_path)

import transaction_verification_pb2 as tx_pb2
import transaction_verification_pb2_grpc as tx_pb2_grpc

class TransactionVerificationServiceServicer(tx_pb2_grpc.TransactionVerificationServiceServicer):
    """
    Implements the TransactionVerificationService gRPC methods.
    """

    def VerifyTransaction(self, request, context):
        """
        Validate the transaction based on simple logic.
        - If creditCardNumber is empty, invalid transaction.
        - If there are no items in the order, invalid transaction.
        """

        response = tx_pb2.TransactionResponse()

        if not request.creditCardNumber or len(request.items) == 0:
            response.valid = False
            response.reason = "Invalid transaction: Missing card details or empty cart."
        else:
            response.valid = True
            response.reason = "Transaction is valid."

        print(f"[Transaction Verification] VerifyTransaction called. valid={response.valid}, reason={response.reason}")
        return response

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    tx_pb2_grpc.add_TransactionVerificationServiceServicer_to_server(
        TransactionVerificationServiceServicer(), server
    )

    port = "50052"
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"[Transaction Verification] Listening on port {port}...")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()

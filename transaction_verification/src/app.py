import sys
import os

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
transaction_verification_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/transaction_verification'))
sys.path.insert(0, transaction_verification_grpc_path)
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc

import grpc
from concurrent import futures

# Create a class to define the server functions, derived from
# transaction_verification_pb2_grpc.TransactionVerificationServiceServicer
class TransactionVerificationService(transaction_verification_grpc.TransactionVerificationServiceServicer):
    # Create an RPC function to verify transaction
    def VerifyTransaction(self, request, context):
        print(f"Verifying transaction for card: {request.card_number}")

        # Check 1: items list must not be empty
        if len(request.items) == 0:
            print("Verification failed: No items in order")
            return transaction_verification.TransactionResponse(
                is_valid=False,
                reason="Order must contain at least one item"
            )

        # Check 2: user data must be filled in
        if not request.user_name or not request.user_contact:
            print("Verification failed: Missing user data")
            return transaction_verification.TransactionResponse(
                is_valid=False,
                reason="User name and contact are required"
            )

        # Check 3: card number must be 16 digits
        card_number = request.card_number.replace(" ", "")
        if not card_number.isdigit() or len(card_number) != 16:
            print("Verification failed: Invalid card number")
            return transaction_verification.TransactionResponse(
                is_valid=False,
                reason="Invalid card number format, must be 16 digits"
            )

        # Check 4: CVV must be 3 digits
        if not request.card_cvv.isdigit() or len(request.card_cvv) != 3:
            print("Verification failed: Invalid CVV")
            return transaction_verification.TransactionResponse(
                is_valid=False,
                reason="Invalid CVV, must be 3 digits"
            )

        # Check 5: expiration date format MM/YY
        expiration = request.card_expiration
        if len(expiration) != 5 or expiration[2] != '/' or \
           not expiration[:2].isdigit() or not expiration[3:].isdigit():
            print("Verification failed: Invalid expiration date")
            return transaction_verification.TransactionResponse(
                is_valid=False,
                reason="Invalid expiration date, use MM/YY format"
            )

        print("Transaction verified successfully")
        return transaction_verification.TransactionResponse(
            is_valid=True,
            reason="Transaction is valid"
        )

def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor())
    # Add TransactionVerificationService
    transaction_verification_grpc.add_TransactionVerificationServiceServicer_to_server(
        TransactionVerificationService(), server
    )
    # Listen on port 50052
    port = "50052"
    server.add_insecure_port("[::]:" + port)
    # Start the server
    server.start()
    print("Transaction verification server started. Listening on port 50052.")
    # Keep thread alive
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
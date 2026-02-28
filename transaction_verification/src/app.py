import sys
import os

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
fraud_detection_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/transaction_verification'))
sys.path.insert(0, fraud_detection_grpc_path)
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc

import grpc
from concurrent import futures

class TransactionVerificationService(transaction_verification_grpc.TransactionVerificationServiceServicer):
    def VerifyTransaction(self, request, context):
        print(f"Verifying transaction for card number: {request.card_number}")

        #Check 1: items list must not be empty
        if len(request.items) == 0:
            return transaction_verification.TransactionResponse(
                is_valid=False,
                reason="Order must contain at least one item"
            )
        #Check 2: user data must be filled in
        if not request.user_name or not request.user_contact:
            return transaction_verification.TransactionResponse(
                is_valid=False,
                reason="User name and contact are required"
            )

        #Check 3: card number must be 16 digits
        card_number = request.card_number.replace(" ", "")
        if not card_number.isdigit() or len(card_number) != 16:
            return transaction_verification.TransactionResponse(
                is_valid=False,
                reason="Invalid card number format"
            )

        #Check 4: CVV must be 3 digits
        if not request.cvv.isdigit() or len(request.cvv) != 3:
            return transaction_verification.TransactionResponse(
                is_valid=False,
                reason="Invalid CVV format"
            )

        # Check 5: expiration date format MM/YY
        expiration = request.card_expiration
        if len(expiration) != 5 or expiration[2] != '/' or \
           not expiration[:2].isdigit() or not expiration[3:].isdigit():
            return transaction_verification.TransactionResponse(
                is_valid=False,
                reason="Invalid expiration date format. Use MM/YY"
            )
        
        # Check 6: expiration date must be in the future
        month = int(expiration[:2])
        year = int(expiration[3:])
        
        current_year = datetime.now().year % 100
        current_month = datetime.now().month
        
        if year < current_year or (year == current_year and month < current_month):
            return transaction_verification.TransactionResponse(
                is_valid=False,
                reason="Card has expired"
            )
        
        print("Transaction verified successfully")
        return transaction_verification.TransactionResponse(
            is_valid=True,
            reason="Transaction is valid"
        )

def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    transaction_verification_grpc.add_TransactionVerificationServiceServicer_to_server(
        TransactionVerificationService(), server
    )
    port = "50052"
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Server started. Listening on port 50052.")
    server.wait_for_termination()
            
if __name__ == '__main__':
    serve()
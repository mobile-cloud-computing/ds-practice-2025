import sys
import os
from concurrent import futures

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
transaction_verification_grpc_path = os.path.abspath(
    os.path.join(FILE, '../../../utils/pb/transaction_verification')
)
sys.path.insert(0, transaction_verification_grpc_path)

import grpc
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc


class TransactionVerificationService(
    transaction_verification_grpc.TransactionVerificationServiceServicer
):
    def VerifyTransaction(self, request, context):
        print("Received transaction verification request")
        print("user_name:", request.user_name)
        print("user_contact:", request.user_contact)
        print("item_count:", request.item_count)
        print("terms_accepted:", request.terms_accepted)

        is_valid = True
        message = "Transaction is valid."

        if not request.user_name:
            is_valid = False
            message = "Missing user name."
        elif not request.user_contact:
            is_valid = False
            message = "Missing user contact."
        elif request.item_count <= 0:
            is_valid = False
            message = "No items in order."
        elif not request.terms_accepted:
            is_valid = False
            message = "Terms and conditions not accepted."
        elif not request.card_number or not request.expiration_date or not request.cvv:
            is_valid = False
            message = "Missing credit card information."

        response = transaction_verification.TransactionVerificationResponse()
        response.is_valid = is_valid
        response.message = message

        print("Returning verification result:", response.is_valid, response.message)
        return response


def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    transaction_verification_grpc.add_TransactionVerificationServiceServicer_to_server(
        TransactionVerificationService(), server
    )

    port = "50052"
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Transaction verification server started. Listening on port 50052.")
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
import sys
import os
import logging
logging.basicConfig(level=logging.INFO)

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
class TransactionVerificationService(transaction_verification_grpc.TransactionVerificationServiceServicer):

    def VerifyTransaction(self, request, context):
        logging.info("VerifyTransaction called for OrderID: test1")

        required_fields = [
            request.user_name,
            request.contact,
            request.card_number,
            request.street,
            request.city,
            request.state,
            request.zip_code,
            request.country,
            request.shipping_method
        ]
        

        # Dummy logic: check if all fields have SOMETHING in them
        #TODO: Luhn's algorithm for credit card number
        #TODO: some more interesting checking for fields
        if all(required_fields) and request.terms_accepted:
            is_valid = True
        else:
            is_valid = False
        
        logging.info(f"TransactionVerification completed | OrderID: test1 | Is valid?: {is_valid}")
        
        return transaction_verification.VerifyResponse(is_valid=is_valid)



def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    transaction_verification_grpc.add_TransactionVerificationServiceServicer_to_server(TransactionVerificationService(), server)
    # Listen on port 50052
    port = "50052"
    server.add_insecure_port("[::]:" + port)
    # Start the server
    server.start()
    logging.info(f"TransactionVerification started. Listening on port {port}.")
    # Keep thread alive
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
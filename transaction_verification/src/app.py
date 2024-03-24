import sys
import os
from datetime import datetime

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
utils_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/transaction_verification'))
sys.path.insert(0, utils_path)
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc

from concurrent import futures
import grpc

# Get the server index for the vector clock.
SERVER_INDEX = int(os.getenv("SERVER_INDEX_FOR_VECTOR_CLOCK"))

class TransactionVerificationService(transaction_verification_grpc.TransactionVerificationServiceServicer):
    # Increment the value in the server index.
    # If the index isn't in the vc_array, append 0 until the index.
    def increment_vector_clock(self, vc_array):
        if SERVER_INDEX <= len(vc_array) - 1:
            vc_array[SERVER_INDEX] += 1
        else:
            while len(vc_array) != SERVER_INDEX:
                vc_array.append(0)
            vc_array.append(1)
    
    def VerifyTransaction(self, request, context):
        print("Transaction verification request received")
        print(f"[Transaction verification] Server index: {SERVER_INDEX}")
        vector_clock = request.vectorClock
        vc_array = vector_clock.vcArray
        timestamp = vector_clock.timestamp

        print(f"[Transaction verification] VCArray from orchestrator: {vc_array}")
        print(f"[Transaction verification] Timestamp from orchestrator: {timestamp}")

        self.increment_vector_clock(vc_array)
        print(f"[Transaction verification] VCArray in Transaction verification: {vc_array}")
        print(f"[Transaction verification] Timestamp in Transaction verification: {datetime.now().timestamp()}")
        # order items empty?
        item_name = request.item.name
        item_quantity = request.item.quantity
        items_exist = bool(item_name) and (item_quantity >0)

        # user data filled?
        user_name = request.user.name
        contact_number = request.user.contact
        user_data_filled = bool(user_name and contact_number)

        # card info is correct format?
        card_number = request.creditCard.number
        card_expiration_date = request.creditCard.expirationDate
        card_cvv = request.creditCard.cvv
        
        is_valid_date = True
        if "/" not in card_expiration_date:
            is_valid_date = False
        else:
            mm, yy = card_expiration_date.split("/")
            is_valid_date = (mm.isdigit() and int(mm) > 0 and int(mm) <= 12) and (yy.isdigit() and int(yy) > 23 and int(yy) < 50)

        correct_card_format = is_valid_date and ((len(card_number) >= 10 and len(card_number) <= 19) and card_number.isdigit()) \
            and ((len(card_cvv) == 3 or len(card_cvv) == 4) and card_cvv.isdigit())


        is_valid = user_data_filled and items_exist and correct_card_format
        
        print(f"Transaction verification response: {'Valid' if is_valid else 'Invalid'}")
        return transaction_verification.TransactionVerificationResponse(is_valid=is_valid )

    
def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    transaction_verification_grpc.add_TransactionVerificationServiceServicer_to_server(TransactionVerificationService(), server)
    server.add_insecure_port('[::]:50052')
    server.start()
    print("Transaction Verification Service started on port 50052")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
import sys
import os

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
tv_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/transaction_verification'))
sys.path.insert(0, tv_path)

import transaction_verification_pb2 as tv_pb2
import transaction_verification_pb2_grpc as tv_grpc

import re
from datetime import datetime
import grpc
from concurrent import futures

class TransactionVerificationService(tv_grpc.TransactionVerificationServiceServicer):

    def VerifyTransaction(self, request, context):

        if not re.match(r"[^@]+@[^@]+\.[^@]+", request.email):
            return tv_pb2.VerificationResponse(
                is_valid=False,
                message="Invalid email format"
            )

        if not request.card_number.isdigit() or len(request.card_number) != 16:
            return tv_pb2.VerificationResponse(
                is_valid=False,
                message="Invalid card number"
            )
        
        if not request.cvv.isdigit() or len(request.cvv) not in [3, 4]:
            return tv_pb2.VerificationResponse(
                is_valid=False,
                message="Invalid CVV"
            )

        try:
            exp = datetime.strptime(request.expiration_date, "%m/%Y")
            if exp < datetime.now():
                return tv_pb2.VerificationResponse(
                    is_valid=False,
                    message="Card expired"
                )
        except:
            return tv_pb2.VerificationResponse(
                is_valid=False,
                message="Invalid expiration format"
            )

        return tv_pb2.VerificationResponse(
            is_valid=True,
            message="Transaction valid"
        )
    
def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    tv_grpc.add_TransactionVerificationServiceServicer_to_server(TransactionVerificationService(), server)
    server.add_insecure_port("[::]:50052")
    server.start()
    print("Transaction Verification started on port 50052")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
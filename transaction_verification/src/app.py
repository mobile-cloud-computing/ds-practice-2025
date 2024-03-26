import sys
import os
from datetime import datetime
from google.protobuf.json_format import MessageToDict

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
utils_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb'))
sys.path.insert(0, utils_path)
from fraud_detection import fraud_detection_pb2 as fraud_detection
from fraud_detection import fraud_detection_pb2_grpc as fraud_detection_grpc
from transaction_verification import transaction_verification_pb2 as transaction_verification
from transaction_verification import transaction_verification_pb2_grpc as transaction_verification_grpc

from concurrent import futures
import grpc

# Get the server index for the vector clock.
SERVER_INDEX = int(os.getenv("SERVER_INDEX_FOR_VECTOR_CLOCK"))

def userdata_fraud_detection_service(data, vector_clock):
    with grpc.insecure_channel('fraud_detection:50051') as channel:
        stub = fraud_detection_grpc.UserdataFraudDetectionServiceStub(channel)
        attr = MessageToDict(data)
        attr["vectorClock"] = vector_clock
        response = stub.DetectUserdataFraud(fraud_detection.UserdataFraudDetectionRequest(**attr))
        return response

def cardinfo_fraud_detection_service(data, vector_clock):
    with grpc.insecure_channel('fraud_detection:50051') as channel:
        stub = fraud_detection_grpc.CardinfoFraudDetectionServiceStub(channel)
        attr = MessageToDict(data)
        attr["vectorClock"] = vector_clock
        response = stub.DetectCardinfoFraud(fraud_detection.CardinfoFraudDetectionRequest(**attr))
        return response
    
# Increment the value in the server index, and update the timestamp.
# If the index isn't in the vc_array, append 0 until the index.
def increment_vector_clock(vector_clock):
    vc_array = vector_clock.vcArray
    timestamp = datetime.now().timestamp()

    if SERVER_INDEX <= len(vc_array) - 1:
        vc_array[SERVER_INDEX] += 1
    else:
        while len(vc_array) != SERVER_INDEX:
            vc_array.append(0)
        vc_array.append(1)

    return {"vcArray": vc_array, "timestamp": timestamp}

class ItemAndUserdataVerificationService(transaction_verification_grpc.ItemAndUserdataVerificationServiceServicer):
    
    def VerifyItemAndUserdata(self, request, context):
        print("Transaction verification request received")
        print(f"[Transaction verification] Server index: {SERVER_INDEX}")
        vector_clock = request.vectorClock
        vector_clock = increment_vector_clock(vector_clock)
        print(f"[Transaction verification] VCArray updated in Transaction verification: {vector_clock['vcArray']}")
        print(f"[Transaction verification] Timestamp updated in Transaction verification: {vector_clock['timestamp']}")

        user = request.user
        item = request.item

        # order items empty?
        items_exist = bool(item.name) and (item.quantity > 0)
        # user data filled?
        user_data_filled = bool(user.name and user.contact)

        is_valid = user_data_filled and items_exist

        print(f"Transaction verification about item and userdata response: {'Valid' if is_valid else 'Invalid'}")
        if is_valid:
            with futures.ThreadPoolExecutor() as executor:
                userdata_fraud_future = executor.submit(userdata_fraud_detection_service, request, vector_clock)
            message = userdata_fraud_future.result()
            response = MessageToDict(message)
        else:
            response = {
                "isValid": False,
                "errorMessage": "Transaction Invalid. Couldn't verify your order and user information.",
                "books": None
            }
        return transaction_verification.ItemAndUserdataVerificationResponse(**response)
    
class CardinfoVerificationService(transaction_verification_grpc.CardinfoVerificationServiceServicer):
    
    def VerifyCardinfo(self, request, context):
        print("Transaction verification request received")
        print(f"[Transaction verification] Server index: {SERVER_INDEX}")
        vector_clock = request.vectorClock
        vector_clock = increment_vector_clock(vector_clock)
        print(f"[Transaction verification] VCArray updated in Transaction verification: {vector_clock['vcArray']}")
        print(f"[Transaction verification] Timestamp updated in Transaction verification: {vector_clock['timestamp']}")

        credit_card = request.creditCard

        # card info is correct format?
        card_number = credit_card.number
        card_expiration_date = credit_card.expirationDate
        card_cvv = credit_card.cvv
        
        is_valid_date = True
        if "/" not in card_expiration_date:
            is_valid_date = False
        else:
            mm, yy = card_expiration_date.split("/")
            is_valid_date = (mm.isdigit() and int(mm) > 0 and int(mm) <= 12) and (yy.isdigit() and int(yy) > 23 and int(yy) < 50)

        correct_card_format = is_valid_date and ((len(card_number) >= 10 and len(card_number) <= 19) and card_number.isdigit()) \
            and ((len(card_cvv) == 3 or len(card_cvv) == 4) and card_cvv.isdigit())

        
        is_valid = correct_card_format

        print(f"Transaction verification about cardinfo response: {'Valid' if is_valid else 'Invalid'}")
        if is_valid:
            with futures.ThreadPoolExecutor() as executor:
                cardinfo_fraud_future = executor.submit(cardinfo_fraud_detection_service, request, vector_clock)
            message = cardinfo_fraud_future.result()
            response = MessageToDict(message)
        else:
            response = {
                "isValid": False,
                "errorMessage": "Transaction Invalid. Couldn't verify your payment details.",
                "books": None
            }
        return transaction_verification.CardinfoVerificationResponse(**response)

    
def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    transaction_verification_grpc.add_ItemAndUserdataVerificationServiceServicer_to_server(ItemAndUserdataVerificationService(), server)
    transaction_verification_grpc.add_CardinfoVerificationServiceServicer_to_server(CardinfoVerificationService(), server)
    server.add_insecure_port('[::]:50052')
    server.start()
    print("Transaction Verification Service started on port 50052")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
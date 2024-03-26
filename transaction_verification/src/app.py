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

# Set the server index for the vector clock.
# Frontend: 0, Orchestrator: 1, TransactionVerification: 2, FraudDetection: 3, BookSuggestion: 4
SERVER_INDEX = 2
NUM_SERVERS = 5
LOCAL_VC_CORRECT_AFTER_ORCHESTRATOR = [0, 0, 0, 0, 0]
VC_CORRECT_AFTER_ORCHESTRATOR = [0, 1, 0, 0, 0]
LOCAL_VC_CORRECT_AFTER_ITEM_VERIFICATION = [0, 0, 1, 0, 0]
VC_CORRECT_AFTER_ITEM_VERIFICATION = [0, 1, 1, 0, 0]
LOCAL_VC_CORRECT_AFTER_USERDATA_FRAUD_DETECTION = [0, 0, 2, 0, 0]
VC_CORRECT_AFTER_USERDATA_FRAUD_DETECTION = [0, 1, 2, 1, 0]

# Create the global local vector clock.
local_vector_clock = {}

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
    vc_array = [0 for _ in range(NUM_SERVERS)] if not "vcArray" in vector_clock else vector_clock["vcArray"]
    timestamp = datetime.now().timestamp()

    vc_array[SERVER_INDEX] += 1

    return {"vcArray": vc_array, "timestamp": timestamp}

class ItemAndUserdataVerificationService(transaction_verification_grpc.ItemAndUserdataVerificationServiceServicer):

    def __init__(self):
        global local_vector_clock
        local_vector_clock = {"vcArray": [0 for _ in range(NUM_SERVERS)], "timestamp": datetime.now().timestamp()}

    def check_vc_after_orchestrator(self, vector_clock, local_vector_clock):
        request_vc_check = bool(vector_clock['vcArray'] == VC_CORRECT_AFTER_ORCHESTRATOR)
        local_vc_check = bool(local_vector_clock['vcArray'] == LOCAL_VC_CORRECT_AFTER_ORCHESTRATOR)
        timestamp_check = bool(vector_clock['timestamp'] < datetime.now().timestamp())
        return request_vc_check and local_vc_check and timestamp_check
    
    def check_vc_after_item_verification(self, vector_clock, local_vector_clock):
        request_vc_check = bool(vector_clock['vcArray'] == VC_CORRECT_AFTER_ITEM_VERIFICATION)
        local_vc_check = bool(local_vector_clock['vcArray'] == LOCAL_VC_CORRECT_AFTER_ITEM_VERIFICATION)
        timestamp_check = bool(vector_clock['timestamp'] < datetime.now().timestamp())
        return request_vc_check and local_vc_check and timestamp_check
    
    def VerifyItemAndUserdata(self, request, context):
        global local_vector_clock
        print("Transaction verification request received")
        print(f"[Transaction verification] Server index: {SERVER_INDEX}")
        
        is_valid = False
        error_message = "Transaction Invalid. Couldn't verify your order and user information."
        
        vector_clock = MessageToDict(request.vectorClock)
        user = request.user
        item = request.item

        if self.check_vc_after_orchestrator(vector_clock, local_vector_clock):
            print('[Transaction verification] VC is correct after orchestrator.')

            # a: order items empty?
            item_exist = bool(item.name) and (item.quantity > 0)
            if item_exist:
                local_vector_clock = increment_vector_clock(local_vector_clock)
                vector_clock = increment_vector_clock(vector_clock)
                print(f"[Transaction verification] VCArray updated (item exists) in Transaction verification: {vector_clock['vcArray']}")
                # print(f"[Transaction verification] Timestamp updated (item exists) in Transaction verification: {vector_clock['timestamp']}")
            else:
                error_message = "Transaction Invalid. Couldn't verify your order information.",

        if self.check_vc_after_item_verification(vector_clock, local_vector_clock):
            print('[Transaction verification] VC is correct after item verification.')

            # b: user data filled?
            user_data_filled = bool(user.name and user.contact)
            if user_data_filled:
                local_vector_clock = increment_vector_clock(local_vector_clock)
                vector_clock = increment_vector_clock(vector_clock)
                print(f"[Transaction verification] VCArray updated (userdata exists) in Transaction verification: {vector_clock['vcArray']}")
                # print(f"[Transaction verification] Timestamp updated (userdata exists) in Transaction verification: {vector_clock['timestamp']}")
                is_valid = True
            else:
                error_message = "Transaction Invalid. Couldn't verify your user information."
    
        print(f"Transaction verification about item and userdata response: {'Valid' if is_valid else 'Invalid'}")
        if is_valid:
            with futures.ThreadPoolExecutor() as executor:
                userdata_fraud_future = executor.submit(userdata_fraud_detection_service, request, vector_clock)
            message = userdata_fraud_future.result()
            response = MessageToDict(message)
        else:
            response = {
                "isValid": False,
                "errorMessage": {error_message},
                "books": None
            }
            
        return transaction_verification.ItemAndUserdataVerificationResponse(**response)
    
class CardinfoVerificationService(transaction_verification_grpc.CardinfoVerificationServiceServicer):

    def check_vc_after_usredata_fraud_detection(self, vector_clock, local_vector_clock):
        request_vc_check = bool(vector_clock['vcArray'] == VC_CORRECT_AFTER_USERDATA_FRAUD_DETECTION)
        local_vc_check = bool(local_vector_clock['vcArray'] == LOCAL_VC_CORRECT_AFTER_USERDATA_FRAUD_DETECTION)
        timestamp_check = bool(vector_clock['timestamp'] < datetime.now().timestamp())
        return request_vc_check and local_vc_check and timestamp_check
    
    def is_creditcard_valid(self, credit_card):
        card_number = credit_card.number
        card_expiration_date = credit_card.expirationDate
        card_cvv = credit_card.cvv
        
        is_valid_date = True
        if "/" not in card_expiration_date:
            is_valid_date = False
        else:
            mm, yy = card_expiration_date.split("/")
            is_valid_date = (mm.isdigit() and int(mm) > 0 and int(mm) <= 12) and (yy.isdigit() and int(yy) > 23 and int(yy) < 50)

        is_correct_card_format = is_valid_date and ((len(card_number) >= 10 and len(card_number) <= 19) and card_number.isdigit()) \
            and ((len(card_cvv) == 3 or len(card_cvv) == 4) and card_cvv.isdigit())

        return is_correct_card_format
    
    def VerifyCardinfo(self, request, context):
        global local_vector_clock
        print("Transaction verification request received")
        print(f"[Transaction verification] Server index: {SERVER_INDEX}")

        is_creditcard_valid = False

        vector_clock = MessageToDict(request.vectorClock)
        credit_card = request.creditCard
        

        if self.check_vc_after_usredata_fraud_detection(vector_clock, local_vector_clock):
            print('[Transaction verification] VC is correct after userdata fraud detection.')

            # c: card info is correct format?
            is_creditcard_valid = self.is_creditcard_valid(credit_card)
            if is_creditcard_valid:
                local_vector_clock = increment_vector_clock(local_vector_clock)
                vector_clock = increment_vector_clock(vector_clock)
                print(f"[Transaction verification] VCArray updated (valid creditcard) in Transaction verification: {vector_clock['vcArray']}")
                # print(f"[Transaction verification] Timestamp updated (valid creditcard) in Transaction verification: {vector_clock['timestamp']}")
    
        
        print(f"Transaction verification about cardinfo response: {'Valid' if is_creditcard_valid else 'Invalid'}")
        if is_creditcard_valid:
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
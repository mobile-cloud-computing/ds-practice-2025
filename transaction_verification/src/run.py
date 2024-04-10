import sys
from pathlib import Path

current_dir = Path(__file__).parent.absolute()
app_dir = current_dir.parent.parent
sys.path.insert(0, str(app_dir))

import utils.pb.transaction_verification.transaction_verification_pb2 as transaction_verification
import utils.pb.transaction_verification.transaction_verification_pb2_grpc as transaction_verification_grpc
from utils.logger import logger 
import grpc
from concurrent import futures
from utils.pb.transaction_verification.transaction_verification_pb2 import *
from utils.pb.transaction_verification.grpc_client.grpc_client import fraud

from utils.vector_clock.vector_clock import VectorClock

# Datatype of cache is {order_id: CheckoutRequest}
cache = {}

logs = logger.get_module_logger("VERIFICATION") 

class TransactionVerification(transaction_verification_grpc.TransactionServiceServicer):
    # Transaction verification is handled here.
    def verifyTransaction(self, vcm: VectorClockMessage, context):
        logs.info("verifyTransaction called")
        order_id = vcm.order_id
        vc_received = vc_msg_2_object(vcm)
        logs.info("Received vector clock: " + str(vc_received))
        logs.info("Cache state: " + str(cache))
        
        try:
            local_vc = vc_msg_2_object(cache[order_id].vector_clock)
            
        except Exception as e:
            logs.error("Error retrieving local vector clock: " + str(e))
            det = Determination()
            det.vector_clock.CopyFrom(vcm)
            det.suggestion_response.CopyFrom(SuggestionResponse())
            return det
        

        local_vc.merge(vc_received)
        logs.info("Merged vector clocks: " + str(local_vc))
        local_vc.update()
        request: CheckoutRequest = cache[order_id]

        logs.info("Handling request: " + str(request))
        
        # Check whether mandatory fields are filled in
        if check_mandatory_fields(request):
            local_vc.update()
            logs.info("Mandatory fields filled")
        else:
            logs.error("Mandatory field check failed")
            det = Determination()
            det.vector_clock.CopyFrom(object_2_vc_msg(local_vc))
            det.suggestion_response.CopyFrom(SuggestionResponse())
            return det 
        
        # Check whether credit card is valid
        if check_credit_cards(request):
            local_vc.update()
            logs.info("Credit card check passed")
        else:
            logs.error("Credit card check failed")
            det = Determination()
            det.vector_clock.CopyFrom(object_2_vc_msg(local_vc))
            det.suggestion_response.CopyFrom(SuggestionResponse())
            return det 
        
        local_vc.update()
        vcm = object_2_vc_msg(local_vc)

        logs.info("Updated cache: " + str(cache))
        
        return fraud(vcm)

    def sendData(self, request: CheckoutRequest, context):
        try:

            logs.info("sendData triggered in transaction_verification")
            order_id = request.vector_clock.order_id
            cache[order_id] = request
            local_vc = vc_msg_2_object(request.vector_clock)
            local_vc.update()

            det = Determination()
            local_vc.update()
            det.vector_clock.CopyFrom(object_2_vc_msg(local_vc))
            det.suggestion_response.CopyFrom(SuggestionResponse())
            logs.info("Determination composed")
            
            return det 
        except Exception as e:
            logs.error("Error sending data: " + str(e))

def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor())

    transaction_verification_grpc.add_TransactionServiceServicer_to_server(TransactionVerification(), server)

    port = "50052"
    server.add_insecure_port("[::]:" + port)
    server.start()
    logs.info(f"Server started. Listening on port {port}.")
    server.wait_for_termination()

def vc_msg_2_object(vcm: VectorClockMessage):
    logs.info("vc_msg_2_object called")
    vc = VectorClock(process_id=1, num_processes=4, order_id=vcm.order_id, clocks=vcm.clock)
    logs.info("Converted vector clock: " + str(vc))
    return vc

def object_2_vc_msg(vc: VectorClock):
    vcm = VectorClockMessage()
    vcm.process_id = 1 
    vcm.order_id = vc.order_id
    vcm.clock.extend(vc.clock)
    return vcm

def check_mandatory_fields(request: CheckoutRequest):
    name = request.user.name
    contact = request.user.contact
    address = [request.billingAddress.street, request.billingAddress.city, request.billingAddress.state, request.billingAddress.zip, request.billingAddress.country]
    logs.info(f"Checking mandatory fields: name={name}, contact={contact}, address={address}")
    if not name or not contact or not all(address):
        logs.warning("Name, contact, or address missing")
        return False
    return True

def check_credit_cards(request: CheckoutRequest):
    # Check if credit card number is correct length.
    if not 20 > len(str(request.creditCard.number)) > 15:
        logs.warning("Invalid credit card number")
        return False 

    # Check if expiration date is valid and in the future.
    try:
        import datetime
        datetime.datetime.strptime(request.creditCard.expirationDate, "%M/%y")
    except ValueError:
        logs.warning("Invalid credit card expiration date")
        return False 

    # Check if CVV is valid.
    if not 1000 > int(request.creditCard.cvv) > 0 or len(str(request.creditCard.cvv)) != 3:
        logs.warning("Invalid credit card CVV")
        return False 

    return True


if __name__ == '__main__':
    serve()

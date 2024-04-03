import sys
import os

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
utils_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/fraud_detection'))
sys.path.insert(0, utils_path)

import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc
from utils.logger import logger
import grpc
from concurrent import futures
import pickle
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from utils.pb.fraud_detection.fraud_detection_pb2 import *
from utils.vector_clock.vector_clock import *
from utils.pb.fraud_detection.grpc_client.grpc_client import suggest

cache = {}

logs = logger.get_module_logger("FRAUD")

# Create a class to define the server functions, derived from
# fraud_detection_pb2_grpc.HelloServiceServicer
class HelloService(fraud_detection_grpc.HelloServiceServicer):
    # Create an RPC function to say hello
    def SayHello(self, request, context):
        response = fraud_detection.HelloResponse()
        response.greeting = "Hello, " + request.name
        logs.info(f"Said hello to {request.name}")
        return response

class FraudService(fraud_detection_grpc.FraudServiceServicer):

    def DetectFraud(self, vcm: VectorClockMessage, context):

        order_id = vcm.order_id
        vc_received = vc_msg_2_object(vcm)
        try:
            local_vc = vc_msg_2_object(cache[order_id].vector_clock)
        except:
            det = Determination()
            det.vector_clock.CopyFrom(object_2_vc_msg(vc_received))
            det.suggestion_response.CopyFrom(SuggestionResponse())
            return det

        local_vc.merge(vc_received)
        local_vc.update()

        request = cache[order_id]
        
        response = predict(request)[0]
        
        if not response:
            logs.warning("Fraud suspected")
            det = Determination()
            det.vector_clock.CopyFrom(object_2_vc_msg(vc_received))
            det.suggestion_response.CopyFrom(SuggestionResponse())
            return det
        else: 
            local_vc.update()
        
        local_vc.update()
        vcm = object_2_vc_msg(local_vc)
        
        return suggest(vcm)

    
    def sendData(self, request:CheckoutRequest, context):
        order_id = request.vector_clock.order_id
        cache[order_id] = request
        local_vc = vc_msg_2_object(request.vector_clock)
        local_vc.update()

        det = Determination()
        local_vc.update()
        det.vector_clock.CopyFrom(object_2_vc_msg(local_vc))
        det.suggestion_response.CopyFrom (SuggestionResponse())
        
        return det 

def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    fraud_detection_grpc.add_HelloServiceServicer_to_server(HelloService(), server)
    fraud_detection_grpc.add_FraudServiceServicer_to_server(FraudService(), server)
    port = "50051"
    server.add_insecure_port("[::]:" + port)
    server.start()
    logs.info(f"Server started. Listening on port {port}.")
    server.wait_for_termination()

def predict(request):

    name = request.user.name
    contact = request.user.contact
    credit_card_number = request.creditCard.number
    expiration_date = request.creditCard.expirationDate
    cvv = request.creditCard.cvv
    street = request.billingAddress.street
    city = request.billingAddress.city
    state = request.billingAddress.state
    zip_code = request.billingAddress.zip
    country = request.billingAddress.country
    device_type = request.device.type
    device_model = request.device.model
    device_os = request.device.os
    browser_name = request.browser.name
    browser_version = request.browser.version
    items_name = "blank"
    items_quantity = "1"
    referrer = request.referrer

    # Create the new_data dictionary
    new_data = {
        'name': name,
        'contact': contact,
        'creditCard_number': credit_card_number,
        'creditCard_expirationDate': expiration_date,
        'creditCard_cvv': cvv,
        'billingAddress_street': street,
        'billingAddress_city': city,
        'billingAddress_state': state,
        'billingAddress_zip': zip_code,
        'billingAddress_country': country,
        'device_type': device_type,
        'device_model': device_model,
        'device_os': device_os,
        'browser_name': browser_name,
        'browser_version': browser_version,
        'items_name': items_name,
        'items_quantity': items_quantity,
        'referrer': referrer
    }


    with open('/app/fraud_detection/src/random_forest_model.pkl', 'rb') as model_file:
        loaded_model = pickle.load(model_file)

    new_data_df = pd.DataFrame([new_data])
    label_encoder = LabelEncoder()
    new_data_encoded = new_data_df.apply(label_encoder.fit_transform)

    prediction = loaded_model.predict(new_data_encoded)

    return prediction

def vc_msg_2_object(vc: VectorClockMessage):
    logs.info("Converting VectorClockMessage to VectorClock")
    return VectorClock(process_id=2, num_processes=4, order_id=vc.order_id, clocks = vc.clock)

def object_2_vc_msg(vc: VectorClock):
    logs.info("Converting VectorClock to VectorClockMessage")
    vcm = VectorClockMessage()
    vcm.process_id = 2
    vcm.order_id = vc.order_id
    vcm.clock.extend(vc.clock)

    return VectorClockMessage(process_id= vc.process_id, order_id= vc.order_id, clock=vc.clock)

if __name__ == '__main__':
    serve()

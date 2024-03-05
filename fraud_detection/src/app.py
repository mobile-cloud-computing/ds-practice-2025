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
    # Extremely simplistic fraud detection is handled here.
    def DetectFraud(self, request, context):

        response = fraud_detection.Determination()
        response.determination = True

        # Check if credit card number is correct length.
        if not 20 > len(str(request.creditCard.number)) > 15:
            logs.warning("Invalid credit card number")
            response.determination = False

        # Check if expiration date is valid and in the future.
        try:
            import datetime
            datetime.datetime.strptime(request.creditCard.expirationDate, "%M/%y")
        except ValueError:
            logs.warning("Invalid credit card expiration date")
            response.determination = False

        # Check if CVV is valid.
        if not 1000 > int(request.creditCard.cvv) > 0 or len(str(request.creditCard.cvv)) != 3:
            logs.warning("Invalid credit card CVV")
            response.determination = False

        response_2 = predict(request)[0]
        if not response_2:
            logs.warning("Fraud suspected")
            response.determination = False

        return response

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





    


if __name__ == '__main__':
    serve()

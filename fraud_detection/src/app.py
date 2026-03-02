import sys
import os
from concurrent import futures

# This set of lines are needed to import the gRPC stubs.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
fraud_detection_grpc_path = os.path.abspath(
    os.path.join(FILE, '../../../utils/pb/fraud_detection')
)
sys.path.insert(0, fraud_detection_grpc_path)

import grpc
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc


class HelloService(fraud_detection_grpc.HelloServiceServicer):
    def SayHello(self, request, context):
        response = fraud_detection.HelloResponse()
        response.greeting = "Hello, " + request.name
        print(response.greeting)
        return response

    def CheckFraud(self, request, context):
        print("Received fraud check request")
        print("user_name:", request.user_name)
        print("card_number:", request.card_number)
        print("item_count:", request.item_count)

        is_fraud = False
        message = "No fraud detected."

        # Very simple dummy rules for now
        if request.item_count > 10:
            is_fraud = True
            message = "Too many items in order."
        elif request.card_number.endswith("0000"):
            is_fraud = True
            message = "Suspicious card number pattern."
        elif "fraud" in request.user_name.lower():
            is_fraud = True
            message = "Suspicious user name."

        response = fraud_detection.FraudCheckResponse()
        response.is_fraud = is_fraud
        response.message = message

        print("Returning fraud result:", response.is_fraud, response.message)
        return response


def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    fraud_detection_grpc.add_HelloServiceServicer_to_server(HelloService(), server)

    port = "50051"
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Fraud detection server started. Listening on port 50051.")
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
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
        if not 20 > len(str(request.creditcard.number)) > 15:
            logs.warning("Invalid credit card number")
            response.determination = False

        # Check if expiration date is valid and in the future.
        try:
            import datetime
            datetime.datetime.strptime(request.creditcard.expirationDate, "%M/%y")
        except ValueError:
            logs.warning("Invalid credit card expiration date")
            response.determination = False

        # Check if CVV is valid.
        if not 1000 > int(request.creditcard.cvv) > 0 or len(str(request.creditcard.cvv)) != 3:
            logs.warning("Invalid credit card CVV")
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

if __name__ == '__main__':
    serve()

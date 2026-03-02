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
        masked_card_number = mask_fixed(request.card_number)
        print("card_number:", masked_card_number)
        print("item_count:", request.item_count)

        # Compute length based on digits only to avoid counting spaces or other characters
        card_digits = extract_card_digits(request.card_number)
        print("card length (digits only):", len(card_digits))
        is_fraud = False
        message = "No fraud detected."

        # Very simple dummy rules for now
        if request.item_count > 20:
            is_fraud = True
            message = "Too many items in order."

        # Treat any non-16-digit card number as invalid
        elif len(card_digits) != 16:
            is_fraud = True
            message = "Invalid card number."

        elif card_digits.startswith("0000"):
            is_fraud = True
            message = "Suspicious card number pattern."

        elif card_digits.endswith("0000"):
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


def extract_card_digits(card: str) -> str:
    """
    Return only the digit characters from the given card number.
    """
    return ''.join(c for c in str(card) if c.isdigit())


def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    fraud_detection_grpc.add_HelloServiceServicer_to_server(HelloService(), server)

    port = "50051"
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Fraud detection server started. Listening on port 50051.")
    server.wait_for_termination()

def mask_fixed(card: str) -> str:
    digits = ''.join(c for c in str(card) if c.isdigit())
    masked = '*' * 12 + digits[-4:].rjust(4, '*')
    return ' '.join(masked[i:i+4] for i in range(0, 16, 4))

if __name__ == '__main__':
    serve()
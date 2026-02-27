import sys
import os
import re

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
fraud_detection_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/fraud_detection'))
sys.path.insert(0, fraud_detection_grpc_path)
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc

import grpc
from concurrent import futures

# Create a class to define the server functions, derived from
# fraud_detection_pb2_grpc.HelloServiceServicer
class HelloService(fraud_detection_grpc.HelloServiceServicer):
    # Create an RPC function to say hello
    def SayHello(self, request, context):
        # Create a HelloResponse object
        response = fraud_detection.HelloResponse()
        # Set the greeting field of the response object
        response.greeting = "Hello, " + request.name
        # Print the greeting message
        print(response.greeting)
        # Return the response object
        return response


def _looks_like_real_name(name):
    cleaned_name = name.strip()

    tokens = [token for token in cleaned_name.split() if token]
    if len(tokens) < 2:
        return False

    blocked_tokens = {"test", "unknown", "n/a", "na", "asdf", "qwerty"}
    for token in tokens:
        token_lower = token.lower()
        if token_lower in blocked_tokens:
            return False
        # 2 letter minimum, only letters, hyphens, apostrophes, spaces
        if not re.fullmatch(r"[A-Za-z][A-Za-z'\- ]{1,}", token):
            return False

    return True


def _is_luhn_valid(card_number):
    digits_only = "".join(ch for ch in card_number if ch.isdigit())
    if not 13 <= len(digits_only) <= 19:
        return False
    if len(set(digits_only)) == 1:
        return False

    checksum = 0
    should_double = False
    for digit in reversed(digits_only):
        value = int(digit)
        if should_double:
            value *= 2
            if value > 9:
                value -= 9
        checksum += value
        should_double = not should_double

    return checksum % 10 == 0


def _looks_like_real_address(street, city, state, zip_code, country):
    # Require all fields
    if not street or not city or not state or not zip_code or not country:
        return False

    street_clean = street.strip()
    city_clean = city.strip()
    state_clean = state.strip()
    zip_clean = zip_code.strip()
    country_clean = country.strip()

    if len(city_clean) < 2 or not re.fullmatch(r"[A-Za-z][A-Za-z \.'\-]{1,}", city_clean):
        return False
    if len(state_clean) < 2 or not re.fullmatch(r"[A-Za-z][A-Za-z \.'\-]{1,}", state_clean):
        return False

    if not re.fullmatch(r"[A-Za-z0-9 -]{3,10}", zip_clean):
        return False
    if not re.search(r"\d", zip_clean):
        return False

    blocked_values = {"test", "unknown", "n/a", "na", "asdf", "qwerty"}
    if city_clean.lower() in blocked_values or street_clean.lower() in blocked_values:
        return False

    return True


class FraudDetectionService(fraud_detection_grpc.FraudDetectionServiceServicer):
    def DetectFraud(self, request, context):
        reasons = []

        if not _looks_like_real_name(request.purchaser_name):
            reasons.append("Name does not look realistic")

        if not _is_luhn_valid(request.credit_card_number):
            reasons.append("Credit card number is invalid")

        if not _looks_like_real_address(
            request.billing_street,
            request.billing_city,
            request.billing_state,
            request.billing_zip,
            request.billing_country,
        ):
            reasons.append("Billing address does not look realistic")

        is_fraud = len(reasons) > 0
        return fraud_detection.FraudDetectionResponse(
            is_fraud=is_fraud,
            reasons=reasons,
        )


def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor())
    # Add HelloService
    fraud_detection_grpc.add_HelloServiceServicer_to_server(HelloService(), server)
    fraud_detection_grpc.add_FraudDetectionServiceServicer_to_server(FraudDetectionService(), server)
    # Listen on port 50051
    port = "50051"
    server.add_insecure_port("[::]:" + port)
    # Start the server
    server.start()
    print("Server started. Listening on port 50051.")
    # Keep thread alive
    server.wait_for_termination()

if __name__ == '__main__':
    serve()

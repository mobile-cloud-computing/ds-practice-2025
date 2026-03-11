import sys
import os
import logging
import json
import threading


# Import the gRPC stubs for transaction verification
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
transaction_verification_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/transaction_verification'))
sys.path.insert(0, transaction_verification_grpc_path)
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc

import grpc
from concurrent import futures

SERVICE_NAME = 'transaction_verification'
ORDER_CACHE = {}
ORDER_CACHE_LOCK = threading.Lock()


def _cache_initialized_order(order_id, order_payload_json, incoming_clock):
    order_data = json.loads(order_payload_json or '{}')
    vector_clock = dict(incoming_clock)
    vector_clock[SERVICE_NAME] = vector_clock.get(SERVICE_NAME, 0) + 1

    with ORDER_CACHE_LOCK:
        ORDER_CACHE[order_id] = {
            'order_data': order_data,
            'vector_clock': vector_clock,
        }

    return vector_clock


def _touch_order(order_id):
    with ORDER_CACHE_LOCK:
        cached_order = ORDER_CACHE.get(order_id)
        if not cached_order:
            return None

        cached_order['vector_clock'][SERVICE_NAME] = cached_order['vector_clock'].get(SERVICE_NAME, 0) + 1
        return {
            'order_data': cached_order['order_data'],
            'vector_clock': dict(cached_order['vector_clock']),
        }
    
class TransactionVerificationService(transaction_verification_grpc.TransactionVerificationServiceServicer):
    def InitOrder(self, request, context):
        try:
            vector_clock = _cache_initialized_order(request.order_id, request.order_payload_json, request.vector_clock)
        except json.JSONDecodeError:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details('Invalid order payload JSON.')
            return transaction_verification.InitOrderResponse(acknowledged=False)

        print(f"Initialized order {request.order_id} with vector clock {vector_clock}")
        return transaction_verification.InitOrderResponse(acknowledged=True)

    # Create an RPC function to verify transaction
    def VerifyTransaction(self, request, context):
        cached_order = _touch_order(request.order_id) if request.order_id else None
        # Extract transaction details from the request object
        user = request.user
        items = request.items
        card_number = request.card_number
        card_expiry = request.card_expiry
        card_cvv = request.card_cvv

        is_valid = True
        reasons = []
        #Simple validation logic for demonstration purposes
        if not user.name or not user.email or not user.address:
            is_valid = False
            reasons.append("Missing user data.")
        if not items or len(items) == 0:
            is_valid = False
            reasons.append("No items in transaction.")
        if not card_number or len(card_number) < 12 or not card_number.isdigit():
            is_valid = False
            reasons.append("Invalid card number format.")
        if not card_expiry or len(card_expiry) != 5 or card_expiry[2] != '/':
            is_valid = False
            reasons.append("Invalid card expiry format.") 
        if not card_cvv or len(card_cvv) != 3 or not card_cvv.isdigit():
            is_valid = False
            reasons.append("Invalid card CVV format. Must be 3 digits.")

        response = transaction_verification.TransactionVerificationResponse()
        response.is_verified = is_valid
        print(
            f"Received transaction: order_id={request.order_id or '[none]'}, user={user.name}, "
            f"is_verified={response.is_verified}, reasons={reasons}, "
            f"vector_clock={cached_order['vector_clock'] if cached_order else {SERVICE_NAME: 1}}"
        )
        return response


def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor())
    # Add TransactionVerificationService
    transaction_verification_grpc.add_TransactionVerificationServiceServicer_to_server(TransactionVerificationService(), server)
    # Listen on port 50052
    port = "50052"
    server.add_insecure_port("[::]:" + port)
    # Start the server
    server.start()
    print("Transaction Verification Server started. Listening on port 50052.")
    # Keep thread alive
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
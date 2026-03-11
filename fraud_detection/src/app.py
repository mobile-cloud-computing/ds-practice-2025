import sys
import os
import json
import joblib
import pandas as pd
import numpy as np
import threading
from sklearn.ensemble import RandomForestClassifier

# load
fraud_ai = joblib.load("./fraud_detection/ai/fraud_model.joblib")

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

SERVICE_NAME = 'fraud_detection'
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
    
class FraudDetectionService(fraud_detection_grpc.FraudDetectionServiceServicer):
    def InitOrder(self, request, context):
        try:
            vector_clock = _cache_initialized_order(request.order_id, request.order_payload_json, request.vector_clock)
        except json.JSONDecodeError:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details('Invalid order payload JSON.')
            return fraud_detection.InitOrderResponse(acknowledged=False)

        print(f"Initialized order {request.order_id} with vector clock {vector_clock}")
        return fraud_detection.InitOrderResponse(acknowledged=True)

    # Create an RPC function to detect fraud
    def DetectFraud(self, request, context):
        cached_order = _touch_order(request.order_id) if request.order_id else None
        card_number = request.card_number
        order_amount = request.order_amount
        # Create a FraudDetectionResponse object
        response = fraud_detection.FraudDetectionResponse()
        # Set the is_fraud field of the response object
        response.is_fraud = True if fraud_ai.predict([[order_amount, card_number]])[0] else False

        # Print the transaction details and the fraud detection result
        print(
            f"Received transaction: order_id={request.order_id or '[none]'}, amount: {order_amount}, "
            f"is_fraud: {response.is_fraud}, vector_clock={cached_order['vector_clock'] if cached_order else {SERVICE_NAME: 1}}"
        )
        # Return the response object
        return response

def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor())
    # Add FraudDetectionService
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
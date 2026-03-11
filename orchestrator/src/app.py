import sys
import os
import grpc
import json
import logging
from flask import Flask, request
from flask_cors import CORS
from concurrent.futures import ThreadPoolExecutor
import uuid

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")

fraud_detection_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/fraud_detection'))
sys.path.insert(0, fraud_detection_grpc_path)
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc

transaction_verification_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/transaction_verification'))
sys.path.insert(0, transaction_verification_grpc_path)
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc

suggestions_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/suggestions'))
sys.path.insert(0, suggestions_grpc_path)
import suggestions_pb2 as suggestions
import suggestions_pb2_grpc as suggestions_grpc

# Global in-memory cache to track order states and vector clocks for simplicity
def initialize_order(order_id, order_data, service_name):
    payload = json.dumps(order_data)
    initial_vc = [0, 0, 0]

    if service_name == "transaction_verification":
        # Initialize the order with the transaction verification service
        with grpc.insecure_channel("transaction_verification:50052") as channel:
            # Call the InitOrder method on the transaction verification service to set up the initial state for this order
            stub = transaction_verification_grpc.TransactionVerificationServiceStub(channel)
            return stub.InitOrder(
                transaction_verification.InitOrderRequest(
                    order_id=order_id,
                    order_payload_json=payload,
                    vector_clock=initial_vc
                )
            ).acknowledged

    if service_name == "fraud_detection":
        with grpc.insecure_channel("fraud_detection:50051") as channel:
            stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
            return stub.InitOrder(
                fraud_detection.InitOrderRequest(
                    order_id=order_id,
                    order_payload_json=payload,
                    vector_clock=initial_vc
                )
            ).acknowledged

    if service_name == "suggestions":
        with grpc.insecure_channel("suggestions:50053") as channel:
            stub = suggestions_grpc.SuggestionsServiceStub(channel)
            return stub.InitOrder(
                suggestions.InitOrderRequest(
                    order_id=order_id,
                    order_payload_json=payload,
                    vector_clock=initial_vc
                )
            ).acknowledged

    raise ValueError(f"Unknown service {service_name}")


app = Flask(__name__)
CORS(app, resources={r'/*': {'origins': '*'}})


@app.route("/checkout", methods=["POST"])
def checkout():
   
    request_data = json.loads(request.data)
    print(f"[ORCH] Checkout request payload={request_data}")
    try:
        # Generate a unique order ID for this checkout flow and initialize all services in parallel
        order_id = str(uuid.uuid4())

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(initialize_order, order_id, request_data, "transaction_verification"),
                executor.submit(initialize_order, order_id, request_data, "fraud_detection"),
                executor.submit(initialize_order, order_id, request_data, "suggestions"),
            ]
            if not all(f.result() for f in futures):
                return {"error": "Failed to initialize all services"}, 500

        # Start the checkout flow by calling transaction verification, which will orchestrate the rest of the flow
        with grpc.insecure_channel("transaction_verification:50052") as channel:
            stub = transaction_verification_grpc.TransactionVerificationServiceStub(channel)
            final_resp = stub.StartCheckoutFlow(
                transaction_verification.StartCheckoutFlowRequest(order_id=order_id)
            )

        return {
            "orderId": order_id,
            "success": final_resp.success,
            "status": final_resp.message,
            "finalVectorClock": list(final_resp.vector_clock),
            "suggestedBooks": [
                {"title": s.title, "author": s.author}
                for s in final_resp.suggestions
            ]
        }

    except Exception as e:
        logging.exception("Checkout failed")
        return {"error": str(e)}, 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
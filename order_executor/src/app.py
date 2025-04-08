import grpc
import time
import os
import socket
import logging
import redis
import uuid
import json
import sys

# Microservice gRPC stub discovery
microservices = ["suggestions", "transaction_verification", "fraud_detection"]
base_dir = os.path.dirname(__file__)
for service in microservices:
    grpc_path = os.path.abspath(os.path.join(base_dir, f"../../utils/pb/{service}"))
    if os.path.exists(grpc_path):
        print(f"[OrderExecutor] ✅ Path exists: {grpc_path} — adding to sys.path")
        sys.path.insert(0, grpc_path)
    else:
        print(f"[OrderExecutor] ❌ Path does NOT exist: {grpc_path} — not adding")

# Import stubs
import suggestions_pb2 as suggestions
import suggestions_pb2_grpc as suggestions_grpc
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc
import fraud_detection_pb2 as fraud_pb2
import fraud_detection_pb2_grpc as fraud_pb2_grpc

# Setup
logging.basicConfig(level=logging.INFO)
NODE_ID = os.getenv("NODE_ID") or socket.gethostname()
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = 6379
LEADER_KEY = "leader_lock"

print(f"[OrderExecutor] Node ID: {NODE_ID}")
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# ----------------------------
# Leader Election Logic
# ----------------------------
def try_become_leader(ttl=10):
    return r.set(LEADER_KEY, NODE_ID, nx=True, ex=ttl)

def am_i_leader():
    return r.get(LEADER_KEY) == NODE_ID

def renew_leadership(ttl=10):
    if am_i_leader():
        r.expire(LEADER_KEY, ttl)
        print(f"[{NODE_ID}] Renewed leadership")

def get_current_leader():
    return r.get(LEADER_KEY)

# ----------------------------
# Order Queue and Worker Logic
# ----------------------------
def dequeue_order():
    return r.lpop("order_queue")

def leader_loop():
    while True:
        if try_become_leader():
            print(f"[{NODE_ID}] Became leader")

        if am_i_leader():
            order_raw = dequeue_order()
            if order_raw:
                print(f"[{NODE_ID}] Order is being executed... {order_raw}")
                try:
                    order = json.loads(order_raw)
                    dispatch_order(order)
                except Exception as e:
                    logging.exception(f"[{NODE_ID}] Failed to parse or dispatch order: {e}")
            else:
                print(f"[{NODE_ID}] No orders. Sleeping.")
        else:
            print(f"[{NODE_ID}] Not leader. Waiting...")

        renew_leadership()
        time.sleep(5)

# ----------------------------
# gRPC Dispatchers
# ----------------------------
def call_fraud_detection(order):
    logging.info(f"[OrderExecutor] Calling fraud detection for order: {order['order_id']}")
    channel = grpc.insecure_channel("fraud_detection:50051")
    stub = fraud_pb2_grpc.FraudDetectionServiceStub(channel)
    init_req = fraud_pb2.FraudInitRequest(**order["payload"], order_id=order["order_id"])
    stub.InitializeOrder(init_req)
    fraud_req = fraud_pb2.FraudRequest(order_id=order["order_id"])
    response = stub.CheckFraud(fraud_req)
    logging.info(f"[OrderExecutor] Fraud Result: {response.action}, Reasons: {list(response.reasons)}")

def call_suggestions(order):
    logging.info(f"[OrderExecutor] Calling suggestions for order: {order['order_id']}")
    channel = grpc.insecure_channel("suggestions:50053")
    stub = suggestions_grpc.BookSuggestionStub(channel)
    init_req = suggestions.SuggestionInitRequest(**order["payload"], order_id=order["order_id"])
    stub.InitializeOrder(init_req)
    sug_req = suggestions.SuggestionRequest(**order["payload"], order_id=order["order_id"])
    response = stub.GetSuggestions(sug_req)
    for rec in response.recommendations:
        print(f"  🔹 {rec.book.description} by {rec.book.author}")

def call_transaction_verification(order):
    logging.info(f"[OrderExecutor] Calling transaction verification for order: {order['order_id']}")
    channel = grpc.insecure_channel("transaction_verification:50052")
    stub = transaction_verification_grpc.TransactionVerificationServiceStub(channel)
    init_req = transaction_verification.TransactionInitRequest(**order["payload"], order_id=order["order_id"])
    stub.InitializeOrder(init_req)
    verify_req = transaction_verification.TransactionRequest(order_id=order["order_id"])
    response = stub.VerifyTransaction(verify_req)
    logging.info(f"[OrderExecutor] Transaction Valid: {response.isValid}, Reason: {response.reason}")

def dispatch_order(order):
    if not order.get("type") or not order.get("payload"):
        logging.warning(f"[{NODE_ID}] Invalid order structure: {order}")
        return

    if order["type"] == "fraud_check":
        call_fraud_detection(order)
    elif order["type"] == "suggestion":
        call_suggestions(order)
    elif order["type"] == "verify_transaction":
        call_transaction_verification(order)
    else:
        logging.warning(f"[{NODE_ID}] Unknown order type: {order['type']}")

# ----------------------------
# Optional Flask Debug Server
# ----------------------------
def start_debug_server():
    from flask import Flask, jsonify
    app = Flask(__name__)

    @app.route("/status")
    def status():
        return jsonify({
            "node_id": NODE_ID,
            "is_leader": am_i_leader(),
            "current_leader": get_current_leader()
        })

    app.run(host="0.0.0.0", port=6000)

# ----------------------------
# Entrypoint
# ----------------------------
if __name__ == "__main__":
    if os.getenv("DEBUG_SERVER") == "1":
        start_debug_server()
    else:
        print(f"[{NODE_ID}] Starting order executor...")
        leader_loop()

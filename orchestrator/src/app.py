import sys
import os
import json
import logging
import time
import threading
import uuid
import grpc
from flask import Flask, request, jsonify
from flask_cors import CORS

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure gRPC stub paths - 3 MSs by now
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
fraud_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/fraud_detection'))
tx_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/transaction_verification'))
sugg_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/suggestions'))
queue_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/order_queue'))

# Add directories to system path
sys.path.insert(0, fraud_path)
sys.path.insert(0, tx_path)
sys.path.insert(0, sugg_path)
sys.path.insert(0, queue_path)

# Import gRPC modules for Fraud Detection, Transaction Verification, and Suggestions
import fraud_detection_pb2 as fd_pb2
import fraud_detection_pb2_grpc as fd_grpc

import transaction_verification_pb2 as tv_pb2
import transaction_verification_pb2_grpc as tv_grpc

import suggestions_pb2 as sugg_pb2
import suggestions_pb2_grpc as sugg_grpc

import order_queue_pb2 as oq_pb2
import order_queue_pb2_grpc as oq_grpc

app = Flask(__name__)
CORS(app)

# gRPC service addresses
FRAUD_ADDR = "fraud_detection:50051"
TX_ADDR = "transaction_verification:50052"
SUGG_ADDR = "suggestions:50053"
QUEUE_ADDR = "order_queue:50054"

# Merge multiple vector clocks into a single one
def merge_clocks(*clock_strings):
    merged = {"transaction": 0, "fraud": 0, "suggestions": 0}
    for cs in clock_strings:
        if cs:
            try:
                c = json.loads(cs)
                for k, v in c.items():
                    merged[k] = max(merged.get(k, 0), v)
            except Exception as e:
                logger.error(f"Error parsing clock: {e}")
    return json.dumps(merged)

### Threading ###
class WorkerThread(threading.Thread):
    def __init__(self, target, args=()):
        super().__init__()
        self._target = target
        self._args = args
        self.result = None

    def run(self):
        # Call the target function
        self.result = self._target(*self._args)

def enqueue_order(order_id, items, user_data, credit_card):
    with grpc.insecure_channel(QUEUE_ADDR) as channel:
        stub = oq_grpc.OrderQueueServiceStub(channel)
        order_data = oq_pb2.OrderData(
            orderId=order_id,
            userData=oq_pb2.UserData(
                name=user_data["name"],
                contact=user_data["contact"],
                address=oq_pb2.Address(**user_data["address"])
            ),
            creditCard=oq_pb2.CreditCard(**credit_card),
            items=[oq_pb2.OrderItem(name=item["name"], quantity=item["quantity"]) for item in items]
        )
        stub.EnqueueOrder(order_data)
        logger.info(f"[Orchestrator] Order {order_id} sent to order queue.")

### Flask Routes ###
@app.route("/", methods=["GET"])
def index():
    return "Orchestrator is running."

@app.route("/checkout", methods=["POST"])
def checkout():
    # Parse payload from the request
    checkout_data = request.get_json()
    if not checkout_data:
        return jsonify({"error": "Invalid request, JSON expected.", "suggestedBooks": []}), 400

    # Generate a unique OrderID using UUID - more prominent than timestamp
    order_id = str(uuid.uuid4())
    logger.info(f"[Orchestrator] Received checkout request for order {order_id}")

    # 1. Initialization: initialize data cache and vector clock
    init_results = {}

    def init_tx():  # transaction verification
        with grpc.insecure_channel(TX_ADDR) as channel:
            stub = tv_grpc.VerificationServiceStub(channel)
            resp = stub.InitOrder(tv_pb2.InitOrderRequest(orderId=order_id, checkoutData=json.dumps(checkout_data)))
            init_results["tx"] = resp.clock

    def init_fd():  # fraud detection
        with grpc.insecure_channel(FRAUD_ADDR) as channel:
            stub = fd_grpc.FraudDetectionServiceStub(channel)
            resp = stub.InitOrder(fd_pb2.FraudInitRequest(orderId=order_id, checkoutData=json.dumps(checkout_data)))
            init_results["fd"] = resp.clock

    def init_sugg(): # suggestions
        with grpc.insecure_channel(SUGG_ADDR) as channel:
            stub = sugg_grpc.SuggestionServiceStub(channel)
            resp = stub.InitOrder(sugg_pb2.SuggestionInitRequest(orderId=order_id, checkoutData=json.dumps(checkout_data)))
            init_results["sugg"] = resp.clock

    # Start initialization parallelly using threads.
    t1 = threading.Thread(target=init_tx)
    t2 = threading.Thread(target=init_fd)
    t3 = threading.Thread(target=init_sugg)
    t1.start(); t2.start(); t3.start()
    t1.join(); t2.join(); t3.join()

    # Merge the vector clocks
    init_clock = merge_clocks(init_results.get("tx"), init_results.get("fd"), init_results.get("sugg"))
    logger.info(f"[Orchestrator] Init clock: {init_clock}")

    # 2. Transaction Verification events - VerifyItems and VerifyUserData
    tv_results = {}

    def verify_items():
        with grpc.insecure_channel(TX_ADDR) as channel:
            stub = tv_grpc.VerificationServiceStub(channel)
            resp = stub.VerifyItems(tv_pb2.VerificationRequest(orderId=order_id, clock=init_clock))
            tv_results["items"] = resp

    def verify_user():
        with grpc.insecure_channel(TX_ADDR) as channel:
            stub = tv_grpc.VerificationServiceStub(channel)
            resp = stub.VerifyUserData(tv_pb2.VerificationRequest(orderId=order_id, clock=init_clock))
            tv_results["user"] = resp

    # Run two verification checks concurrently
    ta = WorkerThread(target=verify_items)
    tb = WorkerThread(target=verify_user)
    ta.start(); tb.start()
    ta.join(); tb.join()

    # Check results
    if not tv_results["items"].success:
        return jsonify({
            "orderId": order_id,
            "status": "Order Rejected",
            "message": tv_results["items"].message,
            "suggestedBooks": []
        }), 200

    if not tv_results["user"].success:
        return jsonify({
            "orderId": order_id,
            "status": "Order Rejected",
            "message": tv_results["user"].message,
            "suggestedBooks": []
        }), 200

    # Merge the clocks
    ab_clock = merge_clocks(tv_results["items"].clock, tv_results["user"].clock)

    # 3. Transaction Verification event - VerifyCreditCard
    with grpc.insecure_channel(TX_ADDR) as channel:
        stub = tv_grpc.VerificationServiceStub(channel)
        resp_cc = stub.VerifyCreditCard(tv_pb2.VerificationRequest(orderId=order_id, clock=ab_clock))
    if not resp_cc.success:
        return jsonify({
            "orderId": order_id,
            "status": "Order Rejected",
            "message": resp_cc.message,
            "suggestedBooks": []
        }), 200
    tv_clock = merge_clocks(ab_clock, resp_cc.clock)

    # 4. Fraud Detection event - CheckUserDataFraud
    with grpc.insecure_channel(FRAUD_ADDR) as channel:
        stub = fd_grpc.FraudDetectionServiceStub(channel)
        resp_fd_user = stub.CheckUserDataFraud(fd_pb2.FraudRequest(orderId=order_id, clock=ab_clock))
    if resp_fd_user.isFraud:
        return jsonify({
            "orderId": order_id,
            "status": "Order Rejected",
            "message": resp_fd_user.message,
            "suggestedBooks": []
        }), 200
    fd_clock_1 = merge_clocks(ab_clock, resp_fd_user.clock)

    # 5: Fraud Detection event - CheckCreditCardFraud
    with grpc.insecure_channel(FRAUD_ADDR) as channel:
        stub = fd_grpc.FraudDetectionServiceStub(channel)
        resp_fd_cc = stub.CheckCreditCardFraud(fd_pb2.FraudRequest(orderId=order_id, clock=fd_clock_1))
    if resp_fd_cc.isFraud:
        return jsonify({
            "orderId": order_id,
            "status": "Order Rejected",
            "message": resp_fd_cc.message,
            "suggestedBooks": []
        }), 200
    # Merge clocks after fraud card check
    fd_clock_final = merge_clocks(fd_clock_1, resp_fd_cc.clock)

    # Step 6: Suggestions event - GenerateSuggestions
    with grpc.insecure_channel(SUGG_ADDR) as channel:
        stub = sugg_grpc.SuggestionServiceStub(channel)
        # Extract book title from the items list
        book_title = checkout_data.get("items", [{}])[0].get("name", "Default Book")
        resp_sugg = stub.GenerateSuggestions(sugg_pb2.SuggestionRequest(orderId=order_id, clock=fd_clock_final, book_title=book_title))
    sugg_clock = resp_sugg.clock
     # Build the suggestions list
    suggestions_list = [{"title": s.title, "author": s.author} for s in resp_sugg.suggestions]

    # Final merge - combine all clocks from initialization and each event.
    final_clock = merge_clocks(init_clock, tv_results["items"].clock, 
                               tv_results["user"].clock,
                               resp_cc.clock, resp_fd_user.clock, 
                               resp_fd_cc.clock, sugg_clock)
    logger.info(f"[Orchestrator] Final merged clock: {final_clock}")

    # Build the response payload
    response_payload = {
        "orderId": order_id,
        "status": "Order Approved",
        "suggestedBooks": suggestions_list,
        "finalClock": json.loads(final_clock)
    }
    logger.info(f"[Orchestrator] Final decision for order {order_id}: Order Approved")
    return jsonify(response_payload), 200

    

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

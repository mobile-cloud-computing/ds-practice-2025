import sys
import os
import uuid
import threading
import grpc
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

# Setup paths
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
root_path = os.path.abspath(os.path.join(FILE, '../../..'))
sys.path.insert(0, root_path)

import utils.pb.fraud_detection.fraud_detection_pb2 as fraud_detection
import utils.pb.fraud_detection.fraud_detection_pb2_grpc as fraud_detection_grpc
import utils.pb.transaction_verification.transaction_verification_pb2 as transaction_verification
import utils.pb.transaction_verification.transaction_verification_pb2_grpc as transaction_verification_grpc
import utils.pb.suggestions.suggestions_pb2 as suggestions
import utils.pb.suggestions.suggestions_pb2_grpc as suggestions_grpc

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r'/*': {'origins': '*'}})

# --- gRPC Callers ---

def init_fraud_detection(order_id, card_nr, amount):
    """Cache data and init vector clock in Fraud Detection."""
    with grpc.insecure_channel('fraud_detection:50051') as channel:
        stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
        stub.initOrder(fraud_detection.InitRequest(
            order_id=order_id,
            orderData=fraud_detection.OdrerData(card_nr=str(card_nr), order_ammount=float(amount))
        ))

def trigger_book_check(order_id):
    """Send the first trigger (bookCheck) to Fraud Detection."""
    with grpc.insecure_channel('fraud_detection:50051') as channel:
        stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
        stub.bookCheck(fraud_detection.BookCheckRequest(order_id=order_id))

def verify_transaction(card_nr, order_id, amount):
    """Verify transaction. It will trigger userCheck in Fraud Detection."""
    with grpc.insecure_channel('transaction_verification:50052') as channel:
        stub = transaction_verification_grpc.transactionServiceStub(channel)
        response = stub.verifyTransaction(
            transaction_verification.PayRequest(card_nr=str(card_nr), order_id=order_id, money=amount)
        )
        return response.verified

def get_suggestions(books):
    """Fetch book suggestions."""
    with grpc.insecure_channel("suggestions:50053") as channel:
        stub = suggestions_grpc.SuggestionsServiceStub(channel)
        response = stub.suggest(suggestions.SuggestRequest(ordered_books=books))
        return response.suggested_books

@app.route('/', methods=['GET'])
def index():
    return "hello orchestrator"

@app.route('/checkout', methods=['POST'])
def checkout():
    data = request.get_json()

    # Generate unique IDs
    order_id_uuid = str(uuid.uuid4())
    order_id_int = int(uuid.uuid4().int & (1<<63)-1) 
    logger.info(f"OrderID: {order_id_uuid}")

    items = data["items"]
    card = data["creditCard"]["number"]
    quantity = sum([i["quantity"] for i in items])
    book_names = [i["name"] for i in items]

    result = {"fail": False, "verified": False}

    def event_a():
        if len(items) == 0:
            result["fail"] = True
            logger.warning("Event A failed: empty items")

    def event_b():
        if not card:
            result["fail"] = True
            logger.warning("Event B failed: no card")

    # --- Event Ordering Flow ---

    # 1. Init state in Fraud Detection
    try:
        init_fraud_detection(order_id_int, card, quantity)
    except Exception as e:
        logger.error(f"Failed to init Fraud Detection: {e}")
        return jsonify({"status": "Order Rejected", "orderId": order_id_uuid, "error": "Internal Error"})

    # 2. Parallel events
    t1 = threading.Thread(target=event_a)
    t2 = threading.Thread(target=event_b)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    if result["fail"]:
        return jsonify({"status": "Order Rejected", "orderId": order_id_uuid})

    # 3. Trigger bookCheck
    try:
        trigger_book_check(order_id_int)
    except Exception as e:
        logger.error(f"Failed to trigger book check: {e}")

    # 4. Verify transaction (triggers userCheck internally)
    try:
        result["verified"] = verify_transaction(card, order_id_int, quantity)
    except Exception as e:
        logger.error(f"Transaction Verification failed/aborted: {e}")
        result["verified"] = False

    if not result["verified"]:
        return jsonify({"status": "Order Rejected", "orderId": order_id_uuid})

    # 5. Fetch suggestions
    try:
        books = get_suggestions(book_names)
        suggestions_list = [{"bookId": b.bookId, "title": b.title, "author": b.author} for b in books]
    except Exception as e:
        logger.error(f"Failed to get suggestions: {e}")
        suggestions_list = []

    return jsonify({
        "orderId": order_id_uuid,
        "status": "Order Approved",
        "suggestedBooks": suggestions_list
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0')
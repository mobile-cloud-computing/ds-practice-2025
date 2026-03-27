import sys
import os
import uuid
import threading

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
root_path = os.path.abspath(os.path.join(FILE, '../../..'))
sys.path.insert(0, root_path)
import utils.pb.fraud_detection.fraud_detection_pb2 as fraud_detection
import utils.pb.fraud_detection.fraud_detection_pb2_grpc as fraud_detection_grpc

import utils.pb.transaction_verification.transaction_verification_pb2 as transaction_verification
import utils.pb.transaction_verification.transaction_verification_pb2_grpc as transaction_verification_grpc

import utils.pb.suggestions.suggestions_pb2 as suggestions
import utils.pb.suggestions.suggestions_pb2_grpc as suggestions_grpc

import utils.pb.orchestrator.orchestrator_pb2 as orchestrator
import utils.pb.orchestrator.orchestrator_pb2_grpc as orchestrator_grpc

import grpc
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)

from flask import Flask, request, jsonify
from flask_cors import CORS
import json

app = Flask(__name__)
CORS(app, resources={r'/*': {'origins': '*'}})


def detect_fraud(card_nr, amount):
    with grpc.insecure_channel('fraud_detection:50051') as channel:
        stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
        response = stub.checkFraud(
            fraud_detection.FraudRequest(
                card_nr=card_nr,
                order_ammount=amount
            )
        )
        return response.is_fraud


def verify_transaction(card_nr, order_id, amount):
    with grpc.insecure_channel('transaction_verification:50052') as channel:
        stub = transaction_verification_grpc.transactionServiceStub(channel)
        response = stub.verifyTransaction(
            transaction_verification.PayRequest(
                card_nr=str(card_nr),
                order_id=order_id,
                money=amount
            )
        )
        return response.verified


def get_suggestions(books):
    with grpc.insecure_channel("suggestions:50053") as channel:
        stub = suggestions_grpc.SuggestionsServiceStub(channel)
        response = stub.suggest(
            suggestions.SuggestRequest(ordered_books=books)
        )
        return response.suggested_books


@app.route('/', methods=['GET'])
def index():
    return "hello orchestrator"


@app.route('/checkout', methods=['POST'])
def checkout():
    data = request.get_json()

    order_id = str(uuid.uuid4())
    logger.info(f"OrderID: {order_id}")

    items = data["items"]
    card = data["creditCard"]["number"]

    quantity = sum([i["quantity"] for i in items])
    book_names = [i["name"] for i in items]

    result = {
        "fail": False,
        "fraud": False,
        "verified": False,
        "suggestions": []
    }

    #verify items
    def event_a():
        if len(items) == 0:
            result["fail"] = True
            logger.warning("Event A failed: empty items")


    #verify user data
    def event_b():
        if not card:
            result["fail"] = True
            logger.warning("Event B failed: no card")

    # RUN A || B
    t1 = threading.Thread(target=event_a)
    t2 = threading.Thread(target=event_b)

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    if result["fail"]:
        return jsonify({"status": "Order Rejected", "orderId": order_id})

    #transaction verification
    result["verified"] = verify_transaction(card, int(uuid.uuid4().int & (1<<32)-1), quantity)

    if not result["verified"]:
        return jsonify({"status": "Order Rejected", "orderId": order_id})

    #fraud check
    result["fraud"] = detect_fraud(card, quantity)

    if result["fraud"]:
        return jsonify({"status": "Order Rejected", "orderId": order_id})

    #suggestions
    books = get_suggestions(book_names)

    suggestions_list = []
    for b in books:
        suggestions_list.append({
            "bookId": b.bookId,
            "title": b.title,
            "author": b.author
        })

    return jsonify({
        "orderId": order_id,
        "status": "Order Approved",
        "suggestedBooks": suggestions_list
    })

suggestion_channel.close()
verification_channel.close()
fraud_channel.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0')
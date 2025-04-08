from flask import Blueprint, request, jsonify
from marshmallow import ValidationError
from schema import *
import uuid
import random

transfer_db = [
    {
        "sender": {"name": "John Doe", "accountNumber": "123456789012"},
        "recipient": {"name": "Jane Smith", "accountNumber": "987654321098"},
        "amount": 250.75,
        "currency": "USD",
        "paymentMethod": "Credit Card",
        "transferNote": "Payment for services rendered",
        "notificationPreferences": ["Email", "SMS"],
        "device": {"type": "Mobile", "model": "iPhone 13", "os": "iOS 16.2"},
        "browser": {"name": "Safari", "version": "16.2"},
        "appVersion": "5.3.1",
        "screenResolution": "1170x2532",
        "referrer": "BankingApp",
        "deviceLanguage": "en-US",
    }
]

transfer_status_db = [
    {
        "transactionId": "TXN202402220001",
        "status": "Transfer Approved",
        "suggestedProducts": [
            {"productId": "PROD001", "title": "Platinum Credit Card"},
            {"productId": "PROD002", "title": "High-Yield Savings Account"},
            {"productId": "PROD003", "title": "International Travel Insurance"},
        ],
    }
]

rejected_transfer = [
    {
        "transactionId": "TXN202402220002",
        "status": "Transfer Rejected",
        "suggestedProducts": [],
    }
]

fintech_bp = Blueprint("fintech", __name__)


@fintech_bp.route("/transfer", methods=["POST"])
def transfer():
    try:
        # Validate incoming request
        schema = TransferRequestSchema()
        data = schema.load(request.json)

        # Simulate transfer approval/rejection (for demo purposes)
        status = random.choice(["Transfer Approved", "Transfer Rejected"])
        transaction_id = str(uuid.uuid4())

        # If approved, suggest products; otherwise, suggestProducts is empty
        suggested_products = []
        if status == "Transfer Approved":
            suggested_products = [
                {"productId": "PROD001", "title": "Premium Savings Account"},
                {"productId": "PROD002", "title": "Travel Rewards Card"},
                {"productId": "PROD003", "title": "Personal Loan Offer"}
            ]

        response = {
            "transactionId": transaction_id,
            "status": status,
            "suggestedProducts": suggested_products
        }

        return jsonify(TransferStatusResponseSchema().dump(response)), 200

    except ValidationError as err:
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": err.messages
            }
        }), 400

    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({
            "error": {
                "code": "SERVER_ERROR",
                "message": "An internal server error occurred."
            }
        }), 500
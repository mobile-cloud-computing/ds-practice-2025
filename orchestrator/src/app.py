import sys
import os
import uuid
import concurrent.futures
import time
# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
fraud_detection_grpc_path = os.path.abspath(
    os.path.join(FILE, "../../../utils/pb/bookstore/fraud_detection")
)
suggestions_path = os.path.abspath(os.path.join(FILE, "../../../utils/pb/bookstore/suggestions"))
transaction_verficiation_path = os.path.abspath(os.path.join(FILE, "../../../utils/pb/bookstore/transaction_verification"))
sys.path.insert(0, fraud_detection_grpc_path)
sys.path.insert(1, suggestions_path)
sys.path.insert(2, transaction_verficiation_path)
import fraud_detection_pb2_grpc as fraud_detection_grpc
import fraud_detection_pb2 as fraud_detection
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc
import suggestions_pb2 as suggestions
import suggestions_pb2_grpc as suggestions_grpc
import grpc

from datetime import datetime




 
# Import Flask.
# Flask is a web framework for Python.
# It allows you to build a web application quickly.
# For more information, see https://flask.palletsprojects.com/en/latest/
from flask import Flask, request,jsonify
from flask_cors import CORS
import json

# Create a simple Flask app.
app = Flask(__name__)
# Enable CORS for the app.
CORS(app, resources={r"/*": {"origins": "*"}})

def verifyTransaction(verification_info):
   try: 
    print("Verification Info:", verification_info)
    # Create the Trasnaction Verification Request
    verification_request = transaction_verification.TransactionVerificationRequest(
        user=transaction_verification.TransactionUser(
            name=verification_info.get('user', {}).get('name', ''),
            contact=verification_info.get('user', {}).get('contact', '')
        ),
        creditCard= transaction_verification.TransactionCreditCard(
            number=verification_info.get('creditCard', {}).get('number', ''),
            expirationDate=verification_info.get('creditCard', {}).get('expirationDate', ''),
            cvv=verification_info.get('creditCard', {}).get('cvv', '')
        ),
        items=[
                transaction_verification.TransactionItem(
                    name=item.get('name', ''),
                    quantity=item.get('quantity', 0)
                ) for item in verification_info.get('items', [])
            ],
        billingAddress=transaction_verification.TransactionBillingAddress(
            street=verification_info.get('billingAddress', {}).get('street', ''),
            city=verification_info.get('billingAddress', {}).get('city', ''),
            country=verification_info.get('billingAddress', {}).get('country', '')
        ),
        termsAndConditionsAccepted=verification_info.get('termsAccepted', False)
    )
    with grpc.insecure_channel("transaction_verification:50052") as channel:
        stub = transaction_verification_grpc.TransactionVerificationServiceStub(channel)
        response = stub.VerifyTransaction(verification_request)
        print("Transaction Verification Response:", response)
        return response
   except Exception as e:
        print(f"Error in verifyTransaction: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise


def detectUserFraud(order_info):
    print("Order Info received in detectUserFraud:", order_info)
    try:
        # Create the request using constructor-style initialization
        request = fraud_detection.OrderInfo(
            user=fraud_detection.User(
                name=order_info.get('user', {}).get('name', ''),
                contact=order_info.get('user', {}).get('contact', ''),
                cardHolderName=order_info.get('user', {}).get('cardHolderName', '')
            ),
            creditCard=fraud_detection.CreditCard(
                number=order_info.get('creditCard', {}).get('number', ''),
                expirationDate=order_info.get('creditCard', {}).get('expirationDate', ''),
                cvv=order_info.get('creditCard', {}).get('cvv', '')
            ),
            items=[
                fraud_detection.OrderItem(
                    name=item.get('name', ''),
                    quantity=item.get('quantity', 0)
                ) for item in order_info.get('items', [])
            ],
            billingAddress=fraud_detection.Address(
                street=order_info.get('billingAddress', {}).get('street', ''),
                city=order_info.get('billingAddress', {}).get('city', ''),
                country=order_info.get('billingAddress', {}).get('country', '')
            ),
            shippingAddress=fraud_detection.Address(
                street=order_info.get('shippingAddress', {}).get('street', ''),
                city=order_info.get('shippingAddress', {}).get('city', ''),
                country=order_info.get('shippingAddress', {}).get('country', '')
            ),
            userComment=order_info.get('userComment', ''),
            shippingMethod=order_info.get('shippingMethod', ''),
            giftWrapping=order_info.get('giftWrapping', False),
            termsAccepted=order_info.get('termsAccepted', False)
        )
        
        print("Final request object:", request)
        
        # Connect to the Fraud Detection Service
        with grpc.insecure_channel("fraud_detection:50051") as channel:
            stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
            response = stub.DetectUserFraud(request)
            print("Fraud Detection Response:", response)
            return response
    except Exception as e:
        print(f"Error in detectUserFraud: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise

def suggestBooks(order):
    # Create the Book Suggestion Request
    request = suggestions.BookRequest(
        book_name=order.get("items", [{}])[0].get("name", "")
    )
    # Connect to the Book Suggestion Service
    with grpc.insecure_channel("suggestions:50053") as channel:
        stub = suggestions_grpc.SuggestionsServiceStub(channel)
        # Get the Suggestions
        response = stub.SuggestBooks(request)
        print("Suggestions Response:", response)
    return {"suggestedBooks": [{"title": response.suggestions}]}


# Define a GET endpoint.
@app.route("/", methods=["GET"])
def index():
    """
    Responds with 'Hello, [name]' when a GET request is made to '/' endpoint.
    """
    # Test the fraud-detection gRPC service.
    #response = greet(name="Jerin")
    # Return the response.
    return "Server UP"
def parseSuggestedBooks(suggestedBooksJson):
    suggested_books_list = []
    for book in suggestedBooksJson:
        # Assuming 'title' is a list of book details
        for book_detail in book['title']:
            book_id = str(uuid.uuid4())
            suggested_books_list.append({
                "bookId": book_id,
                "title": book_detail.book_title,
                "author": book_detail.book_author
            })
    # print(suggested_books_list, "suggested_books_list in right format")
    return suggested_books_list

@app.route("/checkout", methods=["POST"])
def checkout():
    """
    Responds with a JSON object containing the order ID, status, and suggested books.
    """
    try:
        order_id = str(uuid.uuid4())
        # Get request object data to json
        request_data = request.get_json() if request.is_json else json.loads(request.data)
        print("Received request data:", request_data)
        # multi threading the transaction verification, fraud detection and suggestion
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            transaction_future = executor.submit(verifyTransaction, request_data)
            transaction_verification_response = transaction_future.result()
            print("Transaction Response:", transaction_verification_response)
            if transaction_verification_response.verification:
                print("Transaction Verified")
                fraud_future = executor.submit(detectUserFraud, request_data)
                fraud_response = fraud_future.result()
                print("Fraud Response:", fraud_response.isFraudulent, fraud_response.reason)
                
                if fraud_response.isFraudulent:
                    print("Order Rejected and reason:",fraud_response.reason)
                    return jsonify(
                        {
                            "orderId": order_id,
                            "status": "Order Rejected",
                            "suggestedBooks": []
                        }
                    )
                else :
                    print("Order Approved")
                    suggestions_future = executor.submit(suggestBooks, request_data)
                    suggestions_response = suggestions_future.result()
                    suggested_books_json = suggestions_response['suggestedBooks'] 
                    return jsonify(
                        {
                            "orderId": order_id,
                            "status": "Order Approved",
                            "suggestedBooks": parseSuggestedBooks(suggested_books_json)
                        }
                    )
            else:
                print("Transaction Verification Failed")
                return jsonify(
                    {
                        "orderId": order_id,
                        "status": "Order Rejected",
                        "suggestedBooks": []
                    }
                )
            
    except Exception as e:
        print(f"Error in checkout: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return {
            "orderId": str(order_id),
            "status": "Order Failed",
            "error": str(e)
        }, 500

if __name__ == "__main__":
    # Run the app in debug mode to enable hot reloading.
    # This is useful for development.
    # The default port is 5000.
    app.run(host="0.0.0.0")

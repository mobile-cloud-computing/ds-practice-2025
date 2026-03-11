import sys
import os
import uuid
import json
import threading
from concurrent import futures
from google.protobuf import empty_pb2

import logging
logging.basicConfig(level=logging.INFO)

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
fraud_detection_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/fraud_detection'))
sys.path.insert(0, fraud_detection_grpc_path)
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
transaction_verification_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/transaction_verification'))
sys.path.insert(0, transaction_verification_grpc_path)
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
suggestions_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/suggestions'))
sys.path.insert(0, suggestions_grpc_path)
import suggestions_pb2 as suggestions
import suggestions_pb2_grpc as suggestions_grpc

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
orchestrator_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/orchestrator'))
sys.path.insert(0, orchestrator_grpc_path)
import orchestrator_pb2 as pb2
import orchestrator_pb2_grpc as pb2_grpc

import grpc
'''
def greet(name='you'):
    # Establish a connection with the fraud-detection gRPC service.
    with grpc.insecure_channel('fraud_detection:50051') as channel:
        # Create a stub object.
        stub = fraud_detection_grpc.HelloServiceStub(channel)
        # Call the service through the stub object.
        response = stub.SayHello(fraud_detection.HelloRequest(name=name))
    return response.greeting
'''


results_manager = {}

def init_fraud_service(order_id, request_data):
    try:
        with grpc.insecure_channel('fraud_detection:50051') as channel:
            stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
            # Use 'item_json' to match the proto
            req = fraud_detection.InitRequest(order_id=order_id, item_json=json.dumps(request_data))
            stub.InitOrder(req)
            logging.info(f"[{order_id}] Fraud Detection initialized.")
            return True
    except Exception as e:
        logging.error(f"[{order_id}] Failed to init Fraud: {e}")
        return False

'''
def call_fraud_detection(card_number, order_amount):
    try:
        with grpc.insecure_channel('fraud_detection:50051') as channel:
            stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
            request_obj = fraud_detection.FraudRequest(card_number=card_number,order_amount=float(order_amount))
            response = stub.CheckFraud(request_obj)
            return response.is_fraud
    except Exception as e:
        logging.error(f"gRPC Call Failed: {e}")
        return True # Default to fraud if errors
'''

def init_verification_service(order_id, request_data):
    try:
        with grpc.insecure_channel('transaction_verification:50052') as channel:
            stub = transaction_verification_grpc.TransactionVerificationServiceStub(channel)
            # Use 'item_json' to match the proto
            req = transaction_verification.InitRequest(order_id=order_id, item_json=json.dumps(request_data))
            stub.InitOrder(req)
            logging.info(f"[{order_id}] Transaction Verification initialized.")
            return True
    except Exception as e:
        logging.error(f"[{order_id}] Failed to init Verification: {e}")
        return False

'''
def call_transaction_verification(request_data):
    user_info = request_data.get("user", {})
    card_info = request_data.get("creditCard", {})
    billing_address = request_data.get("billingAddress", {})
    items = request_data.get("items", {})

    try:
        with grpc.insecure_channel('transaction_verification:50052') as channel:
            stub = transaction_verification_grpc.TransactionVerificationServiceStub(channel)
            request_obj = transaction_verification.VerifyRequest(
                user_name=user_info.get("name", ""),
                contact=user_info.get("contact", ""),
                card_number=card_info.get("number", ""),
                
                street=billing_address.get("street", ""),
                city=billing_address.get("city", ""),
                state=billing_address.get("state", ""),
                zip_code=billing_address.get("zip", ""),
                country=billing_address.get("country", ""),
                
                shipping_method=request_data.get("shippingMethod", ""),
                terms_accepted=request_data.get("termsAccepted", False)
            )
            
            response = stub.VerifyTransaction(request_obj)
            return response.is_valid
    except Exception as e:
        logging.error(f"gRPC Call Failed: {e}")
        return False # Default to invalid if errors
'''

def init_suggestions_service(order_id, request_data):
    try:
        with grpc.insecure_channel('suggestions:50053') as channel:
            # Corrected the name to SuggestionsServiceStub (with 's')
            stub = suggestions_grpc.SuggestionsServiceStub(channel)
            # Use 'item_json' to match the proto
            req = suggestions.InitRequest(order_id=order_id, item_json=json.dumps(request_data))
            stub.InitOrder(req)
            logging.info(f"[{order_id}] Suggestions initialized.")
            return True
    except Exception as e:
        logging.error(f"[{order_id}] Failed to init Suggestions: {e}")
        return False

'''
def call_suggestions(items):
    try:
        with grpc.insecure_channel('suggestions:50053') as channel:
            stub = suggestions_grpc.SuggestionsServiceStub(channel)
            request_obj = suggestions.SuggestRequest()
            
            for item in items:
                book = request_obj.bought_books.add()
                # Mapping 'name' from frontend to 'title' in proto
                book.title = item.get('name', 'Unknown')
                # Note: If frontend doesn't send author, you can default it
                book.author = item.get('author', 'Unknown')

            response = stub.SuggestBooks(request_obj)
            
            # Convert back to list of dicts for the Flask JSON response
            return [{"title": b.title, "author": b.author} for b in response.suggested_books]
    except Exception as e:
        logging.error(f"Suggestions failed: {e}")
        return []
'''

# Import Flask.
# Flask is a web framework for Python.
# It allows you to build a web application quickly.
# For more information, see https://flask.palletsprojects.com/en/latest/
from flask import Flask, request
from flask_cors import CORS
import json

# Create a simple Flask app.
app = Flask(__name__)
# Enable CORS for the app.
CORS(app, resources={r'/*': {'origins': '*'}})

# Define a GET endpoint.
@app.route('/', methods=['GET'])
def index():
    """
    Responds with 'Hello, [name]' when a GET request is made to '/' endpoint.
    """
    # Test the fraud-detection gRPC service.
    response = greet(name='orchestrator')
    # Return the response.
    return response

class OrderFinalizerService(pb2_grpc.OrderFinalizerServicer):
    def ReportResult(self, request, context):
        order_id = request.order_id
        if order_id in results_manager:
            # 1. Capture the gRPC data into the manager
            results_manager[order_id]["result"] = {
                "orderId": order_id,
                "status": request.status,
                "suggestedBooks": [{"title": b.title, "author": b.author} for b in request.suggested_books]
            }
            # 2. Wake up the Flask thread that is waiting in /checkout
            results_manager[order_id]["event"].set()
        
        return empty_pb2.Empty()


@app.route('/checkout', methods=['POST'])
def checkout():
    """
    Responds with a JSON object containing the order ID, status, and suggested books.
    """
    # Get request object data to json
    request_data = json.loads(request.data)
    order_id = str(uuid.uuid4())[:8]

    # Log request object data
    logging.info(f"OrderID: {order_id} | Orchestrator received order data: {request_data}")

    ##### THREADING #####
    from concurrent.futures import ThreadPoolExecutor

    try:  
        '''      
        user_info = request_data.get("user", {})
        name = user_info.get("name", "")
        contact = user_info.get("contact", "")

        card_info = request_data.get("creditCard", {})
        card_number = card_info.get("number", "")
        order_amount = card_info.get("order_amount", 0.0)

        user_comment = request_data.get("userComment", "")

        items = request_data.get("items", {})

        billing_address = request_data.get("billingAddress", {})
        street = billing_address.get("street", "")
        city = billing_address.get("city", "")
        state = billing_address.get("state", "")
        zip_code = billing_address.get("zip", "")
        country = billing_address.get("country", "")

        shipping_method = request_data.get("shippingMethod", "") #Standard, Express, Next-day

        gift_wrapping = request_data.get("giftWrapping", False)

        terms_accepted = request_data.get("termsAccepted", False)
        '''

        '''
        1) import uuid
        2) each thread sends request_data and order_id to microservices - no extraction happens in orchestrator
        '''

        results_manager[order_id] = {
            "event": threading.Event(),
            "result": None
        }

        with ThreadPoolExecutor(max_workers=3) as executor:
            '''
            future_fraud = executor.submit(call_fraud_detection, order_id, request_data)
            logging.info("Starting thread for FraudDetection | OrderID: test1")

            future_verification = executor.submit(call_transaction_verification, order_id, request_data)
            logging.info("Starting thread for TransactionVerification | OrderID: test1")

            future_suggestions = executor.submit(call_suggestions, order_id, request_data)
            logging.info("Starting thread for Suggestions | OrderID: test1")            

            is_fraud = future_fraud.result()
            logging.info(f"OrderID: test1 | FraudDetection Thread returned fraud status: {is_fraud}")

            is_valid = future_verification.result()
            logging.info(f"OrderID: test1 | TransferVerification Thread returned valid status: {is_valid}")

            suggested_books = future_suggestions.result()
            logging.info(f"OrderID: test1 | Suggestions Thread returned suggested books: {suggested_books}")
            '''

            executor.submit(init_fraud_service, order_id, request_data)
            executor.submit(init_verification_service, order_id, request_data)
            executor.submit(init_suggestions_service, order_id, request_data)

        logging.info(f"[{order_id}] Orchestrator waiting for background chain to complete...")
        success = results_manager[order_id]["event"].wait(timeout=20.0)

        if not success:
                return {"error": "Timeout waiting for services"}, 504

        final_response = results_manager[order_id]["result"]
        del results_manager[order_id]
        return final_response

    except Exception as e:
        logging.exception("Checkout endpoint failed")
        return {"error": str(e)}

def serve_grpc():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb2_grpc.add_OrderFinalizerServicer_to_server(OrderFinalizerService(), server)
    server.add_insecure_port('[::]:50050') # Orchestrator's gRPC port
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    # Start gRPC server in a background thread so Flask can run on the main thread
    threading.Thread(target=serve_grpc, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)

from flask import request, jsonify
import asyncio

from .schemas.checkout import CheckoutSchema
from marshmallow import ValidationError
from .services.grpc_client import fraud, verify_transaction, suggest, order
from utils.logger import logger
from utils.pb.suggestions_service.suggestions_service_pb2 import Book

def init_routes(app):
    logs = logger.get_module_logger("ROUTES")
    logs.info("init_routes triggered")
    
    @app.route('/', methods=['GET'])
    def index():
        try:
            creditcard = {
                "number": "123123",
                "expirationDate": "tomorrow",
                "cvv": "123"
            }
            response = fraud(creditcard=creditcard)
            logs.info(f"Fraud detection response: {response}")
            return str(response)
        except Exception as e:
            logs.error(f"Error in index route: {str(e)}")
            return jsonify({"code": "500", "message": "Internal Server Error"}), 500

    # Quick test for this: curl localhost:8081/checkout -X POST -H 'Content-Type: application/json' -H 'Referer: http://localhost:8080/' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' --data '{"user":{"name":"Priit","contact":"Asd xdc"},"creditCard":{"number":"5105105105105100","expirationDate":"12/26","cvv":"123"},"userComment":"Plz dont charge","items":[{"name":"Learning Python","quantity":1}],"discountCode":"#123","shippingMethod":"Snail","giftMessage":"","billingAddress":{"street":"Narva mnt 18u","city":"Tartu","state":"Tartumaa","zip":"51011","country":"Estonia"},"giftWrapping":false,"termsAndConditionsAccepted":true,"notificationPreferences":["email"],"device":{"type":"Smartphone","model":"Samsung Galaxy S10","os":"Android 10.0.0"},"browser":{"name":"Chrome","version":"85.0.4183.127"},"appVersion":"3.0.0","screenResolution":"1440x3040","referrer":"https://www.google.com","deviceLanguage":"en-US"}'
    @app.route('/checkout', methods=['POST'])
    async def checkout():
        logs.info("Checkout called")
        
        schema = CheckoutSchema()

        order_status_response = {
            'orderId': '12345',
            'status': 'Order Approved',
            'suggestedBooks': [
                {'bookId': '123', 'title': 'Dummy Book 1', 'author': 'Author 1'},
                {'bookId': '456', 'title': 'Dummy Book 2', 'author': 'Author 2'}
            ]
        }

        try:
            data = schema.load(request.get_json())
        except ValidationError as ve:
            logs.error(f"Validation error in checkout route: {ve.messages}")
            return jsonify({"code": "400", "message": "Invalid request parameters."}), 400
        except Exception as e:
            logs.error(f"Error in checkout route: {str(e)}")
            return jsonify({"code": "500", "message": "Internal Server Error"}), 500

        try:
            fraud_detection_task = asyncio.create_task(fraud(checkout_request=data))
            logs.info("Fraud detection task created")
            verify_transaction_task = asyncio.create_task(verify_transaction(creditcard=data['creditCard']))
            logs.info("Transaction verification task created")
            suggestions_task = asyncio.create_task(suggest(book_titles=data['items']))
            logs.info("Suggestion task created")

            fraud_result, verification_result, suggestions_result = await asyncio.gather(fraud_detection_task, verify_transaction_task, suggestions_task)
            logs.info("Results obtained")

            result = {
                "fraud": fraud_result,
                "verification": verification_result,
                "suggestions": suggestions_result
            }

            if not result['fraud']:
                logs.warning("Fraud detected.")
                return jsonify({"code": "400", "message": "Fraud detected."}), 400

            if not result['verification']:
                logs.warning("Transaction credentials are not valid.")
                return jsonify({"code": "400", "message": "Transaction credentials are not valid."}), 400

            if not result['suggestions']:
                logs.warning("Generating suggestions failed.")
                return jsonify({"code": "400", "message": "Generating suggestions failed"}), 400

        except Exception as e:
            logs.error(f"Error in checkout route: {str(e)}")
            return jsonify({"code": "500", "message": "Internal Server Error"}), 500

        suggested_books = []
        for suggestion in suggestions_result:
            suggested_books.append({'bookId': str(suggestion.id), 'title': str(suggestion.name), 'author': str(suggestion.author)})
        order_status_response['suggestedBooks'] = suggested_books

        order_error, order_error_message = order(priority=int(data['creditCard']['number']) % 10, creditcard=data['creditCard'])
        if order_error is True:
            logs.error(f"Error during submitting order: {str(order_error_message)}")
            return jsonify({"code": "500", "message": "Internal Server Error"})

        logs.info("Order processed successfully.")
        return jsonify(order_status_response), 200
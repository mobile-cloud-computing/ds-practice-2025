from flask import request, jsonify
import asyncio

from .schemas.checkout import CheckoutSchema
from marshmallow import ValidationError
from .services.grpc_client import *
from utils.logger import logger
from utils.pb.suggestions_service.suggestions_service_pb2 import *
from utils.vector_clock.vector_clock import VectorClock

import uuid

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
    def checkout():
        logs.info("Checkout called")
        
        schema = CheckoutSchema()
        order_id = int(uuid.uuid4()) % 1000

        process_id = 0
        no_of_processes = 4 
        local_vc = VectorClock(process_id, no_of_processes, order_id)
        

        order_status_response = {
            'orderId': order_id,
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

        try:
            '''
            local_vc.update()
            sending_data_result = send_data(checkout_request=data, vector_clock=local_vc)
            logs.info("Data sent to services")

            sending_data_result = [sending_data_result]
            logs.info("Data sent successfully")
            incoming_vc = sending_data_result[0]
            logs.info("Vector clock received: " + str(incoming_vc))
            
            local_vc.merge(incoming_vc)
            local_vc.update()
            verify_transaction_result = verify_transaction(object_2_vc_msg(local_vc))
            sending_data_result = [verify_transaction_result]

            logs.info("Vector clock received: " + str(sending_data_result[0].vector_clock))
            logs.info("Books suggested: " + str(sending_data_result[0].suggestion_response.book_suggestions))
            '''
            order_error, order_error_message = order(priority=int(data['creditCard']['number']) % 10, creditcard=data['creditCard'])
            if order_error is True:
                logs.error(f"Error during submitting order: {str(order_error_message)}")
                return jsonify({"code": "500", "message": "Internal Server Error"})

            logs.info("Order processed successfully.")
            return jsonify(order_status_response), 200

        except Exception as e:
            logs.error(f"Error in checkout route: {str(e)}")
            return jsonify({"code": "500", "message": "Internal Server Error"}), 500


def vc_msg_2_object(vcm: VectorClockMessage):
    logs.info("vc_msg_2_object called")
    vc = VectorClock(process_id=0, num_processes=4, order_id=vcm.order_id, clocks = vcm.clock)
    logs.info(str(vc))
    return vc


def object_2_vc_msg(vc: VectorClock):
    vcm = VectorClockMessage()
    vcm.process_id = 0 
    vcm.order_id = vc.order_id
    vcm.clock.extend(vc.clock)
    return vcm
import logging
import sys
import os
import grpc
from concurrent import futures
import pandas as pd
import geoip2.database
import joblib

logger = logging.getLogger(__name__)

FRAUD_THRESHOLD = float(os.environ.get("FRAUD_THRESHOLD", "0.7"))

FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
grpc_path = os.path.abspath(os.path.join(FILE, "../../../utils/pb/fraud_detection"))
vector_clock_path = os.path.abspath(os.path.join(FILE, "../../../utils/vector_clock"))
sys.path.insert(0, grpc_path)
sys.path.insert(0, vector_clock_path)

import fraud_detection_pb2 as fd_pb2
import fraud_detection_pb2_grpc as fd_pb2_grpc

from vector_clock import OrderEventTracker

GEOIP_PATH = os.path.join(os.path.dirname(__file__), "GeoLite2-Country.mmdb")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "fraud_model.pkl")
ENCODERS_PATH = os.path.join(os.path.dirname(__file__), "label_encoders.pkl")

logging.basicConfig(level=logging.INFO)

model = None
label_encoders = None
geoip_reader = None


def load_models():
    global model, label_encoders, geoip_reader
    if not os.path.exists(MODEL_PATH):
        print(f"ERROR: fraud_model.pkl is missing at {MODEL_PATH}")
        exit(1)
    if not os.path.exists(ENCODERS_PATH):
        print(f"ERROR: label_encoders.pkl is missing at {ENCODERS_PATH}")
        exit(1)

    print(f"Loading model from: {MODEL_PATH}")
    model = joblib.load(MODEL_PATH)
    print(f"Loading encoders from: {ENCODERS_PATH}")
    label_encoders = joblib.load(ENCODERS_PATH)
    print("Model and encoders loaded successfully")

    try:
        geoip_reader = geoip2.database.Reader(GEOIP_PATH)
        print("GeoIP database loaded successfully")
    except Exception as e:
        print(f"Could not load GeoIP database: {e}. IP verification will be disabled.")
        geoip_reader = None


load_models()


def get_country_from_ip(ip_address, reader):
    try:
        response = reader.country(ip_address)
        return response.country.name
    except:
        return "Unknown"


def predict_fraud(order_data):
    """
    Use the pre-loaded model and label_encoders to predict fraud for the stored transaction.
    order_data: dict with keys: billing_city, billing_country, amount, payment_method, ip_address
    """
    ip_address = order_data["ip_address"]
    ip_country = get_country_from_ip(ip_address, geoip_reader)

    # Prepare data for the model
    import pandas as pd

    input_data = pd.DataFrame(
        {
            "billing_city": [order_data["billing_city"]],
            "billing_country": [order_data["billing_country"]],
            "amount": [order_data["amount"]],
            "payment_method": [order_data["payment_method"]],
        }
    )

    # Transform categorical variables
    for col, le in label_encoders.items():
        if col in input_data.columns:
            try:
                input_data[col] = le.transform(input_data[col])
            except ValueError:
                input_data[col] = -1  # fallback for unseen categories

    # Predict
    fraud_probability = model.predict_proba(input_data)[0][1]

    # ip_country mismatch
    ip_country_mismatch = (
        ip_country != order_data["billing_country"] and ip_country != "Unknown"
    )
    if ip_country_mismatch:
        fraud_probability = max(fraud_probability, 0.5)

    # also check for high-risk countries or payment
    is_high_risk_country = order_data["billing_country"] in [
        "Russia",
        "North Korea",
        "Syria",
    ]
    is_high_risk_payment = order_data["payment_method"] == "Crypto"

    details = {
        "ip_country": ip_country,
        "ip_country_mismatch": ip_country_mismatch,
        "high_risk_country": is_high_risk_country,
        "high_risk_payment": is_high_risk_payment,
        "model_score": float(fraud_probability),
        "final_score": float(fraud_probability),
    }
    return fraud_probability, details


class FraudDetectionService(fd_pb2_grpc.FraudDetectionServiceServicer):
    # Keep a dictionary for orders, storing data from InitializeOrder
    def __init__(self):
        self.orders = {}
        self.service_name = "fraud_detection"

        self.order_event_tracker = OrderEventTracker()

    def InitializeOrder(self, request, context):
        """
        Cache the order data, do not run final logic yet.
        """
        order_id = request.order_id
        self.orders[order_id] = {
            "amount": request.amount,
            "ip_address": request.ip_address,
            "email": request.email,
            "billing_country": request.billing_country,
            "billing_city": request.billing_city,
            "payment_method": request.payment_method,
        }
        print(
            f"[FraudDetection] Initialized order {order_id} with data: {self.orders[order_id]}"
        )

        received_clock = dict(request.vectorClock)
        if not self.order_event_tracker.order_exists(order_id):
            self.order_event_tracker.initialize_order(order_id)
            logger.info(
                f"[TransactionVerification]Initialized order {order_id} with vector clock"
            )

        updated_clock = self.order_event_tracker.record_event(
            order_id=order_id,
            service=self.service_name,
            event_name=self.service_name + ".InitializeOrder",
            received_clock=received_clock,
        )

        return fd_pb2.FraudInitResponse(success=True, vectorClock=updated_clock)

    def CheckFraud(self, request, context):
        """
        The final check: retrieve stored data if it exists, run the logic, return a decision.
        If no stored data found, fallback to request directly (or reject).
        """
        order_id = request.order_id
        stored = self.orders.get(order_id)

        # If missing, either fallback or reject
        if not stored:
            # fallback or partial logic using request
            print(
                f"[FraudDetection] order_id {order_id} not found in self.orders. Fallback to request data."
            )
            # If we want to just do immediate logic:
            stored = {
                "amount": request.amount,
                "ip_address": request.ip_address,
                "email": request.email,
                "billing_country": request.billing_country,
                "billing_city": request.billing_city,
                "payment_method": request.payment_method,
            }

        fraud_probability, details = predict_fraud(stored)

        action = "APPROVE"
        reasons = []
        if fraud_probability > FRAUD_THRESHOLD:
            action = "REJECT"
            if details["model_score"] > 0.5:
                reasons.append("Transaction pattern matches known fraudulent behavior")
            if details["high_risk_country"]:
                reasons.append("Transaction originates from a high-risk country")
            if details["high_risk_payment"]:
                reasons.append("High-risk payment method")
            if details["ip_country_mismatch"]:
                reasons.append(
                    f"IP location ({details['ip_country']}) doesn't match billing country ({stored['billing_country']})"
                )

        print(
            f"[FraudDetection] Response: action={action}, reasons={reasons}, details={details}"
        )

        response = fd_pb2.FraudResponse(
            fraud_probability=float(fraud_probability),
            action=action,
            # Convert 'details' dict to google.protobuf.Struct automatically
            details=details,
            reasons=reasons,
        )
        return response


def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    fd_pb2_grpc.add_FraudDetectionServiceServicer_to_server(
        FraudDetectionService(), server
    )
    port = "50051"
    server.add_insecure_port(f"[::]:" + port)
    server.start()
    logging.info(f"Fraud Detection service listening on port {port}")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

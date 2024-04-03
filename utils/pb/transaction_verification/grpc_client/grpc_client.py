import utils.pb.fraud_detection.fraud_detection_pb2 as fraud_detection
import utils.pb.fraud_detection.fraud_detection_pb2_grpc as fraud_detection_grpc
import utils.pb.transaction_verification.transaction_verification_pb2 as transaction_verification
import utils.pb.transaction_verification.transaction_verification_pb2_grpc as transaction_verification_grpc
import utils.pb.suggestions_service.suggestions_service_pb2 as suggestions_service
import utils.pb.suggestions_service.suggestions_service_pb2_grpc as suggestions_service_grpc
from utils.pb.transaction_verification.transaction_verification_pb2 import *
from utils.vector_clock.vector_clock import VectorClock

import grpc
from utils.logger import logger

logs = logger.get_module_logger("Transaction verification grpc client")


def fraud(vcm):
    logs.info("fraud function triggered")
    with grpc.insecure_channel('fraud_detection:50051') as channel:
        stub = fraud_detection_grpc.FraudServiceStub(channel)
        response =  stub.DetectFraud(vcm)
    return response
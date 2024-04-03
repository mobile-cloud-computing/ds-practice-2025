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

logs = logger.get_module_logger("GRPC CLIENT")



async def suggest(book_titles):
    logs.info("suggest function triggered")
    async with grpc.aio.insecure_channel('suggestions_service:50053') as channel:
        stub = suggestions_service_grpc.SuggestionServiceStub(channel)
        response = await stub.Suggest(suggestions_service.SuggestionRequest(book_titles=["123", "233"]))
    return response.book_suggestions


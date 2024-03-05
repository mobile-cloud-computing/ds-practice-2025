import utils.pb.fraud_detection.fraud_detection_pb2 as fraud_detection
import utils.pb.fraud_detection.fraud_detection_pb2_grpc as fraud_detection_grpc
import utils.pb.transaction_verification.transaction_verification_pb2 as transaction_verification
import utils.pb.transaction_verification.transaction_verification_pb2_grpc as transaction_verification_grpc
import utils.pb.suggestions_service.suggestions_service_pb2 as suggestions_service
import utils.pb.suggestions_service.suggestions_service_pb2_grpc as suggestions_service_grpc

import grpc


def greet(name='you'):
    # Establish a connection with the fraud-detection gRPC service.
    with grpc.insecure_channel('fraud_detection:50051') as channel:
        # Create a stub object.
        stub = fraud_detection_grpc.HelloServiceStub(channel)
        # Call the service through the stub object.
        response = stub.SayHello(fraud_detection.HelloRequest(name=name))
    return response.greeting

async def fraud(creditcard):
    async with grpc.aio.insecure_channel('fraud_detection:50051') as channel:
        stub = fraud_detection_grpc.FraudServiceStub(channel)
        response = await stub.DetectFraud(fraud_detection.CheckoutRequest(creditcard=creditcard))
    return response.determination

async def verify_transaction(creditcard):
    async with grpc.aio.insecure_channel('transaction_verification:50052') as channel:
        stub = transaction_verification_grpc.TransactionServiceStub(channel)
        response = await stub.verifyTransaction(transaction_verification.CheckoutRequest(creditcard=creditcard))
    return response.determination

async def suggest(book_titles):
    async with grpc.aio.insecure_channel('suggestions_service:50053') as channel:
        stub = suggestions_service_grpc.SuggestionServiceStub(channel)
        response = await stub.Suggest(suggestions_service.SuggestionRequest(book_titles=["123", "233"]))
    return response.book_suggestions
import sys
import os
import grpc
import threading
from concurrent import futures
import logging
from google.protobuf import empty_pb2

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
root_path = os.path.abspath(os.path.join(FILE, '../../..'))

sys.path.insert(0, os.path.join(root_path, 'utils/pb/transaction_verification'))
import transaction_verification_pb2 as transaction_verification
import transaction_verification_pb2_grpc as transaction_verification_grpc

sys.path.insert(0, os.path.join(root_path, 'utils/pb/fraud_detection'))
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc

logging.basicConfig(
    filename="/logs/transaction_logs.txt",
    filemode="a",
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

class TransactionVerificationService(transaction_verification_grpc.transactionServiceServicer):
    def __init__(self):
        self.orders_data = {}
        self.lock = threading.Lock()

    def initOrder(self, request, context):
        
        with self.lock:
            self.orders_data[request.order_id] = request.orderData
        logger.info(f"Initialized order {request.order_id} in TV.")
        return empty_pb2.Empty()

    def checkCard(self, request, context):
        
        logger.info(f"Card checked for order {request.order_id}")
        return empty_pb2.Empty()

    def checkMoney(self, request, context):
        
        with self.lock:
            order = self.orders_data.get(request.order_id)
            if not order:
                context.abort(grpc.StatusCode.NOT_FOUND, "Order data not found")

            if order.order_ammount > int(order.card_nr) * 0.001:
                logger.warning(f"Order {request.order_id} rejected: Not enough money.")
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Not enough money")
        
        logger.info(f"Money checked and approved for order {request.order_id}")

        try:
            with grpc.insecure_channel('fraud_detection:50051') as channel:
                stub = fraud_detection_grpc.FraudDetectionServiceStub(channel)
                clock_msg = fraud_detection.VectorClock()
                clock_msg.values["TransactionVerification"] = 1
                stub.userCheck(fraud_detection.UserCheckRequest(
                    order_id=request.order_id,
                    clock=clock_msg
                ))
        except Exception as e:
            logger.error(f"Failed to trigger userCheck in Fraud Detection: {e}")

        return empty_pb2.Empty()

    def startPayment(self, request, context):
        return empty_pb2.Empty()


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    transaction_verification_grpc.add_transactionServiceServicer_to_server(TransactionVerificationService(), server)
    port = "50052"
    server.add_insecure_port("[::]:" + port)
    server.start()
    logger.info(f"Server started. Listening on port {port}.")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
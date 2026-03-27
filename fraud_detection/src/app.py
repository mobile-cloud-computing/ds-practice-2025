import sys
import os
import grpc
from concurrent import futures
import logging
import threading
from google.protobuf import empty_pb2

# --- Path setups for gRPC imports ---
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
root_path = os.path.abspath(os.path.join(FILE, '../../..'))
sys.path.insert(0, root_path)
import utils.pb.fraud_detection.fraud_detection_pb2 as fraud_detection
import utils.pb.fraud_detection.fraud_detection_pb2_grpc as fraud_detection_grpc

import utils.pb.transaction_verification.transaction_verification_pb2 as transaction_verification
import utils.pb.transaction_verification.transaction_verification_pb2_grpc as transaction_verification_grpc

import utils.pb.suggestions.suggestions_pb2 as suggestions
import utils.pb.suggestions.suggestions_pb2_grpc as suggestions_grpc

import utils.pb.orchestrator.orchestrator_pb2 as orchestrator
import utils.pb.orchestrator.orchestrator_pb2_grpc as orchestrator_grpc

# --- Logger configuration ---
logging.basicConfig(
    filename="/logs/fraud_detection_logs.txt",
    filemode="a",
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

class FraudDetectionService(fraud_detection_grpc.FraudDetectionServiceServicer):
    def __init__(self):
        # Lock to ensure thread safety since gRPC handles requests concurrently
        self.lock = threading.Lock()
        
        # State management for distributed event ordering
        self.orders_data = {}        # Caches order data until verification is ready
        self.vector_clocks = {}      # Tracks causal history (Vector Clocks) per order_id
        self.user_check_triggers = {} # Tracks the number of arrived events (synchronization barrier)

    def _increment_clock(self, order_id):
        """Helper to increment the local vector clock for this service."""
        if order_id not in self.vector_clocks:
            self.vector_clocks[order_id] = {"FraudDetection": 0}
        self.vector_clocks[order_id]["FraudDetection"] += 1

    def _merge_clocks(self, order_id, incoming_clock_map):
        """Helper to merge an incoming vector clock with the local one by taking the max values."""
        if order_id not in self.vector_clocks:
            self.vector_clocks[order_id] = {"FraudDetection": 0}
        for node, value in incoming_clock_map.items():
            current_val = self.vector_clocks[order_id].get(node, 0)
            self.vector_clocks[order_id][node] = max(current_val, value)

    def initOrder(self, request, context):
        """
        RPC called by the Orchestrator.
        Initializes the caching process and sets the base vector clock.
        Does NOT process the fraud check immediately.
        """
        with self.lock:
            self.orders_data[request.order_id] = request.orderData
            self.vector_clocks[request.order_id] = {"FraudDetection": 0}
            self.user_check_triggers[request.order_id] = 0
            
            logger.info(f"[initOrder] Order {request.order_id} cached. Clock: {self.vector_clocks[request.order_id]}")
        return empty_pb2.Empty()

    def bookCheck(self, request, context):
        """
        RPC called by the Orchestrator.
        Acts as the first trigger for the synchronization barrier.
        """
        with self.lock:
            self._increment_clock(request.order_id)
            logger.info(f"[bookCheck] Executed for {request.order_id}. Clock: {self.vector_clocks[request.order_id]}")
            
            # Register that the first required event has arrived
            self.user_check_triggers[request.order_id] += 1
            self._execute_fraud_check_if_ready(request.order_id)

        return empty_pb2.Empty()

    def userCheck(self, request, context):
        """
        RPC called by the Transaction Verification service.
        Acts as the second trigger and carries the incoming vector clock to merge.
        """
        with self.lock:
            # Merge causal history from Transaction Verification
            self._merge_clocks(request.order_id, request.clock.values)
            self._increment_clock(request.order_id)
            
            logger.info(f"[userCheck] Triggered by TV for {request.order_id}. Clock merged: {self.vector_clocks[request.order_id]}")
            
            # Register that the second required event has arrived
            self.user_check_triggers[request.order_id] = self.user_check_triggers.get(request.order_id, 0) + 1
            self._execute_fraud_check_if_ready(request.order_id)

        return empty_pb2.Empty()

    def _execute_fraud_check_if_ready(self, order_id):
        """
        Synchronization barrier: executes the actual business logic ONLY when 
        both preceding events (bookCheck and userCheck) have arrived.
        """
        # Check if both triggers have been received
        if self.user_check_triggers.get(order_id, 0) == 2:
            self._increment_clock(order_id) 
            
            order = self.orders_data.get(order_id)
            is_fraud = False
            
            # Execute original fraud detection logic using cached data
            if order:
                if "999" in order.card_nr or order.order_ammount > 1000:
                    is_fraud = True
                    
            logger.info(f"[Fraud Check Finalized] Order: {order_id} | is_fraud: {is_fraud} | Final Clock: {self.vector_clocks[order_id]}")


def serve():
    # Setup gRPC server with a thread pool for concurrent request handling
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    fraud_detection_grpc.add_FraudDetectionServiceServicer_to_server(FraudDetectionService(), server)
    port = "50051"
    server.add_insecure_port("[::]:" + port)
    server.start()
    logger.info("Server started. Listening on port 50051.")
    
    # Keep the server thread alive
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
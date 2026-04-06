import sys
import os
import threading
import time

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
utils_path = os.path.abspath(os.path.join(FILE, '../../../utils/'))
sys.path.insert(0, utils_path)

import pb.services.order_executor_pb2 as order_executor
import pb.services.order_executor_pb2_grpc as order_executor_grpc
import pb.services.order_queue_pb2 as order_queue
import pb.services.order_queue_pb2_grpc as order_queue_grpc

import grpc
from concurrent import futures

EXECUTOR_ID = int(os.getenv("EXECUTOR_ID", "1"))
REPLICAS = int(os.getenv("REPLICAS", "1"))

from log_utils.logger import setup_logger
logger = setup_logger(f"OrderExecutorService-{EXECUTOR_ID}")


class OrderExecutorService(order_executor_grpc.OrderExecutorService):

    def __init__(self):
        self._lock = threading.Lock()

        self.executor_id = EXECUTOR_ID
        self.replicas = REPLICAS

        self.leader_id = None
        self.last_heartbeat = time.time()

        self.peers = [
            f"order_executor_{i}:50055"
            for i in range(1, self.replicas + 1)
            if i != self.executor_id
        ]

        logger.info(f"Executor {self.executor_id} started with peers: {self.peers}")

    def Election(self, request, context):
        """Bully election"""
        candidate_id = request.candidate_id

        logger.info(f"Received election request from executor {candidate_id}")
        if self.executor_id > candidate_id:
            logger.info(f"I (executor {self.executor_id}) am higher than executor {candidate_id}, starting my own election")
            threading.Thread(target=self.start_election).start()

        return order_executor.ElectionReply(
            ok=True,
            responder_id=self.executor_id
        )

    def AnnounceLeader(self, request, context):
        with self._lock:
            self.leader_id = request.leader_id
            self.last_heartbeat = time.time()

        logger.info(f"New leader announced: executor {self.leader_id}")

        return order_executor.CoordinatorReply()

    def Heartbeat(self, request, context):
        with self._lock:
            self.last_heartbeat = time.time()

        return order_executor.HeartbeatReply(
            alive=True,
            executor_id=self.executor_id
        )

    def start_election(self):
        logger.info(f"Executor {self.executor_id} starting election")

        higher_peers = [
            f"order_executor_{i}:50055"
            for i in range(self.executor_id + 1, self.replicas + 1)
        ]

        got_response = False

        for peer in higher_peers:
            try:
                with grpc.insecure_channel(peer) as channel:
                    stub = order_executor_grpc.OrderExecutorServiceStub(channel)
                    response = stub.Election(
                        order_executor.ElectionRequest(candidate_id=self.executor_id),
                        timeout=1
                    )
                    if response.ok:
                        logger.info(f"Higher executor with id {response.responder_id} responded")
                        got_response = True
            except Exception as e:
                logger.warning(f"Issue contacting {peer} during election: {str(e)}")

        if not got_response:
            self.become_leader()

    def become_leader(self):
        with self._lock:
            self.leader_id = self.executor_id

        logger.info(f"I (executor {self.executor_id}) am the new leader")

        for peer in self.peers:
            try:
                with grpc.insecure_channel(peer) as channel:
                    stub = order_executor_grpc.OrderExecutorServiceStub(channel)
                    stub.AnnounceLeader(
                        order_executor.CoordinatorMessage(leader_id=self.executor_id),
                        timeout=1
                    )
            except Exception as e:
                logger.warning(f"Could not notify {peer}: {str(e)}")


    def monitor_leader(self):
        while True:
            time.sleep(3)

            with self._lock:
                if self.leader_id is None:
                    continue

                if self.leader_id == self.executor_id:
                    continue

                time_since_heartbeat = time.time() - self.last_heartbeat

            if time_since_heartbeat > 5:
                logger.warning("Leader heartbeat timeout, starting election")
                self.start_election()

    def send_heartbeats(self):
        while True:
            time.sleep(2)

            if self.leader_id != self.executor_id:
                continue

            for peer in self.peers:
                try:
                    with grpc.insecure_channel(peer) as channel:
                        stub = order_executor_grpc.OrderExecutorServiceStub(channel)
                        stub.Heartbeat(order_executor.HeartbeatRequest(), timeout=1)

                except Exception as e:
                    logger.warning(f"Heartbeat failed to {peer}: {str(e)}")

    def process_orders(self):
        while True:
            time.sleep(2)
            if self.leader_id != self.executor_id:
                continue
            try:
                with grpc.insecure_channel("order_queue:50054") as channel:
                    stub = order_queue_grpc.OrderQueueServiceStub(channel)
                    response = stub.Dequeue(order_queue.DequeueRequest())
                    if response.order_id:
                        logger.info(f"[LEADER {self.executor_id}] Executing order {response.order_id}: {response}")
                    else:
                        logger.info(f"[LEADER {self.executor_id}] Queue empty")

            except Exception as e:
                logger.error(f"Error dequeuing order: {e}")

    def start_background_tasks(self):
        threading.Thread(target=self.monitor_leader, daemon=True).start()
        threading.Thread(target=self.send_heartbeats, daemon=True).start()
        threading.Thread(target=self.process_orders, daemon=True).start()


def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor())
    # Add HelloService
    service = OrderExecutorService()
    order_executor_grpc.add_OrderExecutorServiceServicer_to_server(service, server)
    # Listen on port 50055
    port = "50055"
    server.add_insecure_port("[::]:" + port)
    # Start the server
    server.start()
    logger.info(f"Executor {service.executor_id} started. Listening on port 50055.")
    service.start_background_tasks()
    time.sleep(2)
    service.start_election()
    # Keep thread alive
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
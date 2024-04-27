import logging
import os
import requests

from service import DataStoreService

import datastore_pb2_grpc as datastore_pb2_grpc
import quorum
import grpc

# ruff : noqa: E402
from concurrent import futures

ORCHESTRATOR_URL = os.getenv(
    "EXECUTOR_LIST_URL", "http://orchestrator:5000/order_executors"
)


def init_replica_state():
    max_retry_attempt = 10
    retry_counter = 0
    while True:
        try:
            msg = "getting replica datastores from orchestrator..."
            retry_msg = f"retrying getting replica datastores from orchestrator, attempt {retry_counter}..."
            logging.info(msg if retry_counter == 0 else retry_msg)
            response = requests.get(ORCHESTRATOR_URL)
            quorum.setup(response.json())
            logging.info("obtained list of replicas.starting coordination....")
            break
        except Exception as e:
            logging.error("failed to get replica datastores from orchestrator")
            logging.error(e)
            retry_counter += 1
            if retry_counter >= max_retry_attempt:
                logging.error("max retry attempts reached. exiting...")
                raise e
            continue


def serve():
    init_replica_state()
    quorum.start_quorumloop()
    logging.info("Coordination started. Starting server....")
    server = grpc.server(futures.ThreadPoolExecutor())
    datastore_pb2_grpc.add_DatastoreServiceServicer_to_server(
        DataStoreService(), server
    )
    port = "50055"
    server.add_insecure_port("[::]:" + port)
    server.start()
    logging.info("Server started. Listening on port %s.", port)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

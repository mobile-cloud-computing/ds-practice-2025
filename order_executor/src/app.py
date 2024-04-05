import logging
import os
import sys
import requests

FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")

config_path = os.path.abspath(
    os.path.join(FILE, "../../../utils/config")
)
sys.path.insert(0, config_path)
import log_configurator

relative_modules_path = os.path.abspath(
    os.path.join(FILE, "../../../order_executor/src")
)
sys.path.insert(0, relative_modules_path)
import state
import info
from service import OrderExecutorService

utils_path = os.path.abspath(os.path.join(FILE, "../../../utils/pb/order_executor"))
sys.path.insert(0, utils_path)

import order_executor_pb2 as order_executor_grpc
import order_executor_pb2_grpc as order_executor_grpc
import grpc
# ruff : noqa: E402
from concurrent import futures


log_configurator.configure(info._INFO_LOG_PATH, info._ERROR_LOG_PATH)


EXECUTOR_LIST_URL = os.getenv("EXECUTOR_LIST_URL", "http://orchestrator:5000/order_executors")

def serve():
    logging.info("Getting executor list.")
    response = requests.get(EXECUTOR_LIST_URL)
    state._ALL_EXECUTOR_ADDRS = response.json()
    logging.info("Obtained list of executors.Starting coordination....")
    state.start_coordination()
    logging.info("Coordination started. Starting server....")
    server = grpc.server(futures.ThreadPoolExecutor())
    order_executor_grpc.add_OrderExecutorServiceServicer_to_server(
        OrderExecutorService(), server
    )
    port = "50055"
    server.add_insecure_port("[::]:" + port)
    server.start()
    logging.info("Server started. Listening on port %s.", port)
    server.wait_for_termination()

if __name__ == "__main__":
    serve()

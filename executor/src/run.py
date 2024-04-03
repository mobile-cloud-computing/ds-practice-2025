import sys
import grpc
from pathlib import Path

current_dir = Path(__file__).parent.absolute()
app_dir = current_dir.parent.parent
sys.path.insert(0, str(app_dir))

import utils.pb.mq.mq_pb2 as mq
import utils.pb.mq.mq_pb2_grpc as mq_grpc
from utils.logger import logger
import grpc
import threading
import signal
import time
import random

logs = logger.get_module_logger("EXECUTOR")

def dequeue():
    with grpc.insecure_channel('queue:50055') as channel:
        stub = mq_grpc.MQServiceStub(channel)
        response = stub.dequeue(mq.Empty())
    return response


def process_message(stop_event):
    while not stop_event.is_set():
        try:
            message = dequeue()
            logs.debug(f"Processing message: {message}")

            time.sleep(random.randint(5, 30))

            if random.choice([True, False]):
                logs.info("Message processed successfully.")
            else:
                raise Exception("Error processing message.")

        except Exception as e:
            logs.error(f"An error has been emulated: {e}")

def signal_handler(stop_event, signum, frame):
    logs.info("Signal {} received, stopping executor...".format(signum))
    stop_event.set()

def start_executor():
    stop_event = threading.Event()

    signal.signal(signal.SIGTERM, lambda signum, frame: signal_handler(stop_event, signum, frame))
    signal.signal(signal.SIGINT, lambda signum, frame: signal_handler(stop_event, signum, frame))

    executor_thread = threading.Thread(target=process_message, args=(stop_event,))
    executor_thread.start()
    executor_thread.join()

if __name__ == '__main__':
    start_executor()
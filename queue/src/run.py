import sys
from pathlib import Path

current_dir = Path(__file__).parent.absolute()
app_dir = current_dir.parent.parent
sys.path.insert(0, str(app_dir))

import utils.pb.mq.mq_pb2 as mq
import utils.pb.mq.mq_pb2_grpc as mq_grpc


from utils.logger import logger
import grpc, time
from concurrent import futures
import threading

logs = logger.get_module_logger("QUEUE")

class MessagingQueue:
    def __init__(self, debug=False):
        self.queue = []

        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
        self.debug = debug

    def enqueue(self, message, priority=99):
        with self.condition:
            insert_time = time.time()
            self.queue.append((priority, insert_time, message))
            self.queue.sort()
            self.condition.notify()

            if self.debug:
                logs.debug("Queue: " + str(self.queue))

    def pop(self):
        with self.condition:
            while not self.queue:
                self.condition.wait()

            if self.debug:
                logs.debug("Queue: " + str(self.queue))

            return self.queue.pop(0)[2]

    def __repr__(self):
        return "Queue({})".format(self.queue)


class QueueManager:
    def __init__(self):
        self.message_handler = MessagingQueue()

    def enqueue(self, request, context):
        response = mq.Response(error=False, error_message="")

        try:
            self.message_handler.enqueue(request.CheckoutRequest.priority, request.CheckoutRequest.creditcard)

        except Exception as e:
            response.error = True
            response.error_message = str(e)

        return response

    def dequeue(self):

        ## TODO: Return a queue element.
        pass

def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor())

    mq_grpc.add_MQServiceServicer_to_server(QueueManager(), server)

    port = "50055"
    server.add_insecure_port("[::]:" + port)
    server.start()
    logs.info(f"Server started. Listening on port {port}.")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()

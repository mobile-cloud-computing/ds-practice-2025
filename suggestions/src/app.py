import sys
import os
import json
import logging
logging.basicConfig(level=logging.INFO)

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
suggestions_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/suggestions'))
sys.path.insert(0, suggestions_grpc_path)
import suggestions_pb2 as suggestions
import suggestions_pb2_grpc as suggestions_grpc

orchestrator_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/orchestrator'))
sys.path.insert(0, orchestrator_grpc_path)
import orchestrator_pb2 as orchestrator_pb2
import orchestrator_pb2_grpc as orchestrator_pb2_grpc

import grpc
from concurrent import futures
from google.protobuf import empty_pb2
import threading

class VectorClockManager:
    def __init__(self, service_index):
        self.service_index = service_index
        self.orders = {} # {order_id: {"clock": [0,0,0], "cond": Condition(), "data": {}}}

    def init_order(self, order_id, data):
        self.orders[order_id] = {
            "clock": [0, 0, 0],
            "cond": threading.Condition(),
            "data": data
        }

    def update_clock(self, order_id, incoming_clock):
        if order_id in self.orders:
            with self.orders[order_id]["cond"]:
                current = self.orders[order_id]["clock"]
                self.orders[order_id]["clock"] = [max(current[i], incoming_clock[i]) for i in range(3)]
                self.orders[order_id]["cond"].notify_all()

    def wait_for_turn(self, order_id, required_index, required_value):
        order = self.orders[order_id]
        with order["cond"]:
            while order["clock"][required_index] < required_value:
                order["cond"].wait()
        return order

vc = VectorClockManager(service_index=2)

class SuggestionsService(suggestions_grpc.SuggestionsServiceServicer):
    def InitOrder(self, request, context):
        order_id = request.order_id
        vc.init_order(order_id, json.loads(request.item_json))
        logging.info(f"[{order_id}] Suggestions initialized and data cached.")
        return empty_pb2.Empty()

    def UpdateClock(self, request, context):
        # 2. This allows the Fraud service to 'wake up' this service
        vc.update_clock(request.order_id, list(request.clock.values))
        return empty_pb2.Empty()

    def SuggestBooks(self, request, context):
        order_id = request.order_id

        logging.info(f"[{order_id}] SuggestBooks waiting for Fraud & Verification...")
        order_state = vc.wait_for_turn(order_id, required_index=0, required_value=1)

        cached_data = order_state["data"]
        items = cached_data.get("items", [])

        logging.info(f"[{order_id}] Generating suggestions for {len(items)} items.")

        response = suggestions.SuggestResponse()

        for item in items:
            title = item.get('name', 'Unknown')
            author = item.get('author', 'Unknown')
            logging.info(f"User bought {title} by {author}")
            
            # Logic: Suggest a "Part 2" for every book
            suggestion = response.suggested_books.add()
            suggestion.title = f"{title}: The Sequel"
            suggestion.author = author

        logging.info(f"Suggestions completed | OrderID: test1 | Suggested books: {response.suggested_books}")
        try:
            with grpc.insecure_channel('orchestrator:50050') as channel:
                stub = orchestrator_pb2_grpc.OrderFinalizerStub(channel)
                
                # Build the final message
                final_msg = orchestrator_pb2.FinalOrderResult(
                    order_id=order_id,
                    status="Order Approved",
                    suggested_books=[
                            orchestrator_pb2.Book(title=b.title, author=b.author) 
                            for b in response.suggested_books
                        ]
                )
                stub.ReportResult(final_msg)
                logging.info(f"[{order_id}] Final result reported successfully.")

        except Exception as e:
            logging.error(f"[{order_id}] Failed to report result to orchestrator: {e}")

        return response



def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    suggestions_grpc.add_SuggestionsServiceServicer_to_server(SuggestionsService(), server)
    # Listen on port 50053
    port = "50053"
    server.add_insecure_port("[::]:" + port)
    # Start the server
    server.start()
    logging.info (f"Suggestions started. Listening on port {port}.")
    # Keep thread alive
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
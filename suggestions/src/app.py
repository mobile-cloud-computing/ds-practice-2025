import sys
import os
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

import grpc
from concurrent import futures

class SuggestionsService(suggestions_grpc.SuggestionsServiceServicer):

    def SuggestBooks(self, request, context):
        bought_books = request.bought_books
        logging.info(f"Suggesting books for purchase with: {bought_books}")

        response = suggestions.SuggestResponse()

        for bought in request.bought_books:
            logging.info(f"User bought {bought.title} by {bought.author}")
            
            # Logic: Suggest a "Part 2" for every book
            suggestion = response.suggested_books.add()
            suggestion.title = f"{bought.title}: The Sequel"
            suggestion.author = bought.author

        logging.info(f"Suggestions completed | OrderID: test1 | Suggested books: {response.suggested_books}")
        
        return response



def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
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
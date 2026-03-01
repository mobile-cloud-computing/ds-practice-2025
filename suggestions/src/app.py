import sys
import os

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

# Create a class to define the server functions, derived from
# fraud_detection_pb2_grpc.HelloServiceServicer
class SuggestionsService(suggestions_grpc.SuggestionsService):
    # Create an RPC function to say hello
    def getSuggestions(self, request, context):
        print(f"USER: ordered {request}")

        # Create a HelloResponse object
        response = suggestions.SuggestResponse()

        response.suggested_books = ["book3", "book4", "book5"]

        # response.suggested_books = [
        #     {'bookId': '123', 'title': 'The Best Book', 'author': 'Author 1'},
        #     {'bookId': '456', 'title': 'The Second Best Book', 'author': 'Author 2'}
        # ]

        return response

def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor())

    # Add HelloService
    suggestions_grpc.add_SuggestionsServiceServicer_to_server(SuggestionsService(), server)

    # Listen on port 50053
    port = "50053"
    server.add_insecure_port("[::]:" + port)

    # Start the server
    server.start()
    print(f"Server started. Listening on port {port}.")

    # Keep thread alive
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
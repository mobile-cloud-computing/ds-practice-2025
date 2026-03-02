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

class SuggestionsService(suggestions_grpc.SuggestionsServiceServicer):

    def GetSuggestions(self, request, context):
        print(f"Getting suggestions for {len(request.items)} items")

        # Static list of suggested books
        suggested_books = [
            suggestions.SuggestedBook(bookId='123', title='The Best Book', author='Author 1'),
            suggestions.SuggestedBook(bookId='456', title='The Second Best Book', author='Author 2'),
        ]

        return suggestions.SuggestionsResponse(books=suggested_books)


def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor())
    # Add SuggestionsService
    suggestions_grpc.add_SuggestionsServiceServicer_to_server(SuggestionsService(), server)
    # Listen on port 50053
    port = "50053"
    server.add_insecure_port("[::]:" + port)
    # Start the server
    server.start()
    print("Server started. Listening on port 50053.")
    # Keep thread alive
    server.wait_for_termination()

if __name__ == '__main__':
    serve()

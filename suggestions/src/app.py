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
import logging
from BigBookAPI import book_script

logging.basicConfig(
    filename="/logs/suggestions_logs.txt",
    filemode="a",
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

# Create a class to define the server functions, derived from
# fraud_detection_pb2_grpc.HelloServiceServicer
class SuggestionsService(suggestions_grpc.SuggestionsServiceServicer):
    # Create an RPC function to say hello
    def suggest(self, request, context):

        # Create a HelloResponse object
        response = suggestions.SuggestResponse()

        books_data = []
        for book in request.ordered_books:
            logger.info("Fetching suggestions for: %s", book)
            books_data = books_data + book_script.get_book_suggestions(book)

        # in case API service doesn't work
        # books_data = [
        #     {'bookId': '123', 'title': 'The Best Book', 'author': 'Author 1'},
        #     {'bookId': '456', 'title': 'The Second Best Book', 'author': 'Author 2'}
        # ]

        if len(books_data) > 0:
            for b in books_data:
                book = response.suggested_books.add()  # Use .add() to create a new Book
                book.bookId = str(b['bookId'])
                book.title = b['title']
                book.author = b['author']

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
    # print(f"Server started. Listening on port {port}.")
    logger.info(f"Server started. Listening on port {port}.")

    # Keep thread alive
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
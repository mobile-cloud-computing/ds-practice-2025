import sys
import os
import grpc
from concurrent import futures
import logging
from BigBookAPI import book_script

# --- Setup paths for gRPC imports ---
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
root_path = os.path.abspath(os.path.join(FILE, '../../..'))

# Insert path exclusively for suggestions (other services are not used here)
sys.path.insert(0, os.path.join(root_path, 'utils/pb/suggestions'))
import suggestions_pb2 as suggestions
import suggestions_pb2_grpc as suggestions_grpc

logging.basicConfig(
    filename="/logs/suggestions_logs.txt",
    filemode="a",
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

class SuggestionsService(suggestions_grpc.SuggestionsServiceServicer):
    def suggest(self, request, context):
        response = suggestions.SuggestResponse()
        books_data = []

        # Properly wrapped the API call in a single try...except block
        try:
            for book in request.ordered_books:
                logger.info("Fetching suggestions for: %s", book)
                books_data = books_data + book_script.get_book_suggestions(book)
        except Exception as e:
            logger.error(f"API failed or rate limited: {e}. Using hardcoded suggestions.")
            # fallback
            books_data = [
                {"bookId": 1, "title": "The Great Gatsby", "author": "F. Scott Fitzgerald"},
                {"bookId": 2, "title": "To Kill a Mockingbird", "author": "Harper Lee"},
                {"bookId": 3, "title": "1984", "author": "George Orwell"},
            ]

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

    # Add Service
    suggestions_grpc.add_SuggestionsServiceServicer_to_server(SuggestionsService(), server)

    # Listen on port 50053
    port = "50053"
    server.add_insecure_port("[::]:" + port)

    # Start the server
    server.start()
    logger.info(f"Server started. Listening on port {port}.")

    # Keep thread alive
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
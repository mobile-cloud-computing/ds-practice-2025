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

# Static books list
BOOKS = [
    {"book_id": "1", "title": "The Pragmatic Programmer", "author": "David Thomas"},
    {"book_id": "2", "title": "Clean Code", "author": "Robert C. Martin"},
    {"book_id": "3", "title": "Design Patterns", "author": "Gang of Four"},
    {"book_id": "4", "title": "The Hobbit", "author": "J.R.R. Tolkien"},
    {"book_id": "5", "title": "Harry Potter", "author": "J.K. Rowling"},
    {"book_id": "6", "title": "The Great Gatsby", "author": "F. Scott Fitzgerald"},
    {"book_id": "7", "title": "1984", "author": "George Orwell"},
    {"book_id": "8", "title": "To Kill a Mockingbird", "author": "Harper Lee"},
    {"book_id": "9", "title": "The Alchemist", "author": "Paulo Coelho"},
    {"book_id": "10", "title": "Dune", "author": "Frank Herbert"},
]

# Create a class to define the server functions
class SuggestionsService(suggestions_grpc.SuggestionsServiceServicer):

    def GetSuggestions(self, request, context):
        print(f"Getting suggestions for user: {request.user_name}")
        print(f"Items ordered: {[item.name for item in request.items]}")

        # Simple logic: exclude books that match ordered items
        # and return first 3 suggestions
        ordered_names = [item.name.lower() for item in request.items]

        suggested = [
            book for book in BOOKS
            if book["title"].lower() not in ordered_names
        ][:3]

        # Build response
        response_books = [
            suggestions.Book(
                book_id=book["book_id"],
                title=book["title"],
                author=book["author"]
            )
            for book in suggested
        ]

        print(f"Suggesting {len(response_books)} books")
        return suggestions.SuggestionsResponse(books=response_books)

def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor())
    # Add SuggestionsService
    suggestions_grpc.add_SuggestionsServiceServicer_to_server(
        SuggestionsService(), server
    )
    # Listen on port 50053
    port = "50053"
    server.add_insecure_port("[::]:" + port)
    # Start the server
    server.start()
    print("Suggestions server started. Listening on port 50053.")
    # Keep thread alive
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
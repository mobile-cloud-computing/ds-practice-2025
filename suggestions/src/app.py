import sys
import os
from concurrent import futures

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
suggestions_grpc_path = os.path.abspath(
    os.path.join(FILE, '../../../utils/pb/suggestions')
)
sys.path.insert(0, suggestions_grpc_path)

import grpc
import suggestions_pb2 as suggestions
import suggestions_pb2_grpc as suggestions_grpc


class SuggestionsService(suggestions_grpc.SuggestionsServiceServicer):
    def GetSuggestions(self, request, context):
        print("Received suggestions request")
        print("user_name:", request.user_name)
        print("item_count:", request.item_count)

        static_books = [
            {"bookId": "101", "title": "Distributed Systems Basics", "author": "A. Author"},
            {"bookId": "102", "title": "Designing Data-Intensive Applications", "author": "Martin Kleppmann"},
            {"bookId": "103", "title": "Clean Code", "author": "Robert C. Martin"},
            {"bookId": "104", "title": "The Pragmatic Programmer", "author": "Andrew Hunt"},
        ]

        response = suggestions.SuggestionsResponse()

        if request.item_count > 0:
            chosen = static_books[:2]
        else:
            chosen = []

        for book in chosen:
            b = response.books.add()
            b.bookId = book["bookId"]
            b.title = book["title"]
            b.author = book["author"]

        print("Returning", len(response.books), "suggested books")
        return response


def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    suggestions_grpc.add_SuggestionsServiceServicer_to_server(
        SuggestionsService(), server
    )

    port = "50053"
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Suggestions server started. Listening on port 50053.")
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
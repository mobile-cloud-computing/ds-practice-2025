import sys
import os

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
sg_grpc_path = os.path.abspath(os.path.join(FILE, "../../../utils/pb/suggestions"))
sys.path.insert(0, sg_grpc_path)
import suggestions_pb2 as sg_pb2
import suggestions_pb2_grpc as sg_grpc

import logging
import grpc
from concurrent import futures
from google import genai

logging.basicConfig(level=logging.INFO)

# Configure Google AI
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


class SuggestionsService(sg_grpc.SuggestionsServiceServicer):

    def GetSuggestions(self, request, context):
        """Return AI-generated book suggestions based on purchased items."""
        items = request.items
        logging.info(f"Getting suggestions for {len(items)} items")

        items_str = ", ".join([f"{item.name} (qty: {item.quantity})" for item in items])

        prompt = f"Based on the user's purchased books: {items_str}, suggest 2 relevant books. For each book, provide title and author. Respond in the format: 1. Title: [title], Author: [author] 2. Title: [title], Author: [author]"
        response = client.models.generate_content(model='gemma-3-27b-it', contents=prompt)
        result = response.text.strip()

        # Parse the response
        suggested_books = []
        lines = result.split('\n')
        for line in lines:
            if line.startswith(('1.', '2.')):
                parts = line.split('Title:')[1].split('Author:')
                if len(parts) == 2:
                    title = parts[0].strip().strip(',')
                    author = parts[1].strip()
                    book_id = str(hash(title + author))[:6]  # Simple ID
                    suggested_books.append(sg_pb2.SuggestedBook(
                        bookId=book_id, title=title, author=author
                    ))

        logging.info(f"Returning {len(suggested_books)} suggestions")
        return sg_pb2.SuggestionsResponse(books=suggested_books)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    sg_grpc.add_SuggestionsServiceServicer_to_server(SuggestionsService(), server)
    port = "50053"
    server.add_insecure_port("[::]:" + port)
    server.start()
    logging.info(f"Suggestions service started on port {port}")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

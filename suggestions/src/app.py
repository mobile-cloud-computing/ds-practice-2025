import sys
import os

FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
models_path = os.path.abspath(os.path.join(FILE, "../../../utils/models"))
grpc_path = os.path.abspath(os.path.join(FILE, "../../../utils/pb/suggestions"))
sys.path.insert(0, grpc_path)
sys.path.insert(0, models_path)

import suggestions_pb2 as book_suggestion
import suggestions_pb2_grpc as book_suggestion_grpc

import grpc
from concurrent import futures
from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker
import os

from book import Book, engine
from typing import List

from sentence_transformers import SentenceTransformer
from sentence_transformers import util

load_dotenv()

model_name = os.getenv("MODEL_NAME", "all-MiniLM-L6-v2")
model_path = "/app/ai/models/sentence-transformer"

try:
    model = SentenceTransformer(model_path)
    print(f"Model loaded from local path: {model_path}")
except:
    print(f"Model not found locally. Downloading {model_name}...")
    os.makedirs(model_path, exist_ok=True)
    model = SentenceTransformer(model_name)
    model.save(model_path)
    print(f"Model downloaded and saved to {model_path}")


def find_similar_books(tokens: List[str], top_n=5):
    """Find books similar to the given tokens using embeddings."""
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        joined_tokens = " ".join(tokens)
        query_text = model.encode(joined_tokens)
        # For demonstration, we do a naive approach or your custom logic
        # Possibly you have Book.embedding that we can compare with query_text
        # We'll keep your existing approach...
        similar_books = (
            session.query(Book)
            .filter(~Book.title.in_(tokens))
            # .order_by(Book.embedding.cosine_distance(query_text)) # example if you have such an index
            .limit(top_n + len(tokens))
            .all()
        )
        return similar_books[:top_n]
    finally:
        session.close()


class BookSuggestionService(book_suggestion_grpc.BookSuggestionServicer):
    def __init__(self):
        # Dictionary to store data from 'InitializeOrder' calls
        self.orders = {}
        self.service_name = "book_suggestion"

    def InitializeOrder(self, request, context):
        """
        Cache the order data, so we won't do final logic now.
        For instance, store the tokens and user_id.
        """
        order_id = request.order_id
        self.orders[order_id] = {
            "book_tokens": list(request.book_tokens),
            "user_id": request.user_id,
        }
        print(
            f"[Suggestions] Initialized order {order_id} with tokens={request.book_tokens}, user_id={request.user_id}"
        )
        return book_suggestion.SuggestionInitResponse(success=True)

    def GetSuggestions(self, request, context):
        print(f"[Suggestions] Received request: {request}")

        # If we had an InitializeOrder call, retrieve those tokens
        stored = self.orders.get(request.order_id)
        if stored:
            tokens = stored["book_tokens"] or list(request.book_tokens)
            user_id = stored["user_id"] or request.user_id
        else:
            # fallback if not found
            tokens = list(request.book_tokens)
            user_id = request.user_id

        books = find_similar_books(tokens, request.limit)
        recommendations = []
        for book in books:
            recommendations.append(
                book_suggestion.Recommendation(
                    book=book_suggestion.Book(
                        id=str(book.id),
                        author=book.author,
                        description=book.title,
                        genres=[book.genre, book.subgenre],
                    ),
                    confidence_score=0.9,
                    reason="Best Seller",
                )
            )

        response = book_suggestion.RecommendationResponse()
        response.recommendations.extend(recommendations)
        print(f"[Suggestions] order={request.order_id}, result: {books}")
        return response


def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    book_suggestion_grpc.add_BookSuggestionServicer_to_server(
        BookSuggestionService(), server
    )
    port = "50053"
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Server started. Listening on port 50053.")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

import sys
import os
import grpc

from typing import List

from utils.grpc_config import GrpcConfig
from google.protobuf.json_format import MessageToDict

config = GrpcConfig()
FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
config.init_paths(FILE)
config.setup_paths()

models_path = os.path.abspath(os.path.join(FILE, "../../../../../../utils/models"))
sys.path.insert(0, models_path)

import suggestions_pb2 as suggestions
import suggestions_pb2_grpc as suggestions_grpc

from bookstore_models import ServiceResult


class SuggestionsService:
    """Client for the book suggestions service."""

    def __init__(self, grpc_factory, order_event_tracker):
        self.grpc_factory = grpc_factory
        self.order_event_tracker = order_event_tracker

    def initialize_order(
        self, order_id: str, book_tokens: List[str], user_id: str
    ) -> bool:
        """Initialize a suggestions order."""
        try:
            stub = self.grpc_factory.get_stub(
                "suggestions",
                suggestions_grpc.BookSuggestionStub,
                secure=False,
            )
            request = suggestions.SuggestionInitRequest(
                order_id=order_id, book_tokens=book_tokens, user_id=user_id
            )
            response = stub.InitializeOrder(request)
            print(
                f"[Orchestrator] initialize_suggestions_order => success={response.success}"
            )
            return response.success
        except grpc.RpcError as e:
            print(
                f"gRPC error in initialize_suggestions_order: {e.code()}: {e.details()}"
            )
            return False

    def get_suggestions(
        self, order_id: str, book_tokens: List[str], user_id: str = "1", limit: int = 3
    ) -> ServiceResult:
        """Get book suggestions."""
        result = ServiceResult()
        try:
            stub = self.grpc_factory.get_stub(
                "suggestions", suggestions_grpc.BookSuggestionStub, secure=False
            )
            request = suggestions.RecommendationRequest(
                user_id=user_id, limit=limit, book_tokens=book_tokens, order_id=order_id
            )
            response = stub.GetSuggestions(request)
            response_dict = MessageToDict(response)
            raw_recommendations = response_dict.get("recommendations", [])

            formatted = []
            for rec in raw_recommendations:
                book_info = rec.get("book", {})
                formatted.append(
                    {
                        "productId": book_info.get("id", ""),
                        "title": book_info.get("description", ""),
                        "author": book_info.get("author", ""),
                    }
                )

            result.data = formatted
            result.success = True
            return result
        except grpc.RpcError as e:
            print(f"gRPC error (get_suggestions): {e.code()}: {e.details()}")
            result.error = f"Suggestions service error: {e.details()}"
            return result

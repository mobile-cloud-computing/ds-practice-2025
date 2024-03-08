import os
import sys

FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
book_recommendation_path = os.path.abspath(
    os.path.join(FILE, "../../../utils/pb/book_recommendation")
)

sys.path.insert(0, book_recommendation_path)

# ruff : noqa: E402
import book_recommendation_pb2 as book_recommendation
import book_recommendation_pb2_grpc as book_recommendation_grpc
import grpc

_BOOK_RECOMMENDATION_SERVICE = "book_recommendation:50053"


def health_check():
    try:
        with grpc.insecure_channel(_BOOK_RECOMMENDATION_SERVICE) as channel:
            stub = book_recommendation_grpc.RecommendationServiceStub(channel)
            response = stub.HealthCheck(book_recommendation.HealthCheckRequest())
        return response.status
    except Exception as e:
        return f"Unhealthy: {e}"


def get_recommendations(bookIds):
    with grpc.insecure_channel(_BOOK_RECOMMENDATION_SERVICE) as channel:
        stub = book_recommendation_grpc.RecommendationServiceStub(channel)
        response = stub.GetRecommendations(
            book_recommendation.GetRecommendationsRequest(bookIds=bookIds)
        )
    return response

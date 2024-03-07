import os
import sys

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
utils_path = os.path.abspath(
    os.path.join(FILE, "../../../utils/pb/book_recommendation")
)
sys.path.insert(0, utils_path)

# ruff : noqa: E402
from concurrent import futures

import book_recommendation_pb2 as book_recommendation
import book_recommendation_pb2_grpc as book_recommendation_grpc
import grpc


class RecommendationService(book_recommendation_grpc.RecommendationServiceServicer):
    def GetRecommendations(self, request, context):
        dummy_response = book_recommendation.GetRecommendationsResponse()
        dummy_response.recommendations.add(
            id="123",
            title="Dummy Book 1",
            author="Author 1",
            description="Description 1",
            copies="10",
            copies_available="5",
            category="Category 1",
            image_url="https://example.com/image1",
            price=10.0,
            tags=["tag1", "tag2"],
        )

        return dummy_response

    def HealthCheck(self, request, context):
        return book_recommendation.HealthCheckResponse(status="Healthy")


def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    book_recommendation_grpc.add_RecommendationServiceServicer_to_server(
        RecommendationService(), server
    )
    port = "50053"
    server.add_insecure_port("[::]:" + port)
    server.start()
    print(f"Server started. Listening on port {port}.")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

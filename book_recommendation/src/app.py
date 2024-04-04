import os
import sys
import logging

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
relative_modules_path = os.path.abspath(
    os.path.join(FILE, "../../../book_recommendation/src")
)
sys.path.insert(0, relative_modules_path)
import data_store as store
from model import BookRecommendationModel
config_path = os.path.abspath(
    os.path.join(FILE, "../../../utils/config")
)
sys.path.insert(0, config_path)
import log_configurator

utils_path = os.path.abspath(
    os.path.join(FILE, "../../../utils/pb/book_recommendation")
)
sys.path.insert(0, utils_path)

# ruff : noqa: E402
from concurrent import futures

import book_recommendation_pb2 as book_recommendation
import book_recommendation_pb2_grpc as book_recommendation_grpc
import grpc

recommendation_model = BookRecommendationModel()

log_configurator.configure("/app/logs/book_recommendation.info.log", "/app/logs/book_recommendation.error.log")

def get_model_recommendations(title):
    books = store.get_books()
    book_titles = [book["title"] for book in books]
    current_book_title = title
    recommendations = recommendation_model.recommend(current_book_title, book_titles)
    if len(recommendations) == 0:
        return []
    top_recommendations = recommendations[:2]
    recommended_titles = [book[0] for book in top_recommendations]
    return store.get_books_by_titles(recommended_titles)


class RecommendationService(book_recommendation_grpc.RecommendationServiceServicer):
    def GetRecommendations(self, request, context):
        response = book_recommendation.GetRecommendationsResponse()
        current_book_title = store.get_book_by_id(request.bookIds[0])["title"]
        recommended_books = get_model_recommendations(current_book_title)

        for book in recommended_books:
            response.recommendations.append(
                book_recommendation.Recommendation(
                    id=book["id"],
                    title=book["title"],
                    author=book["author"],
                    description=book["description"],
                    copies=book["copies"],
                    copiesAvailable=book["copiesAvailable"],
                    category=book["category"],
                    image_url=book["image_url"],
                    price=book["price"],
                    tags=book["tags"],
                )
            )
        return response

    def HealthCheck(self, request, context):
        return book_recommendation.HealthCheckResponse(status="Healthy")


def serve():
    logging.info("Initializing recommendation model ...")
    sample = get_model_recommendations("Learning Python")
    print(f"recommendation model is ready {sample}")
    logging.info("Recommendation model is ready. Starting server ...")
    server = grpc.server(futures.ThreadPoolExecutor())
    book_recommendation_grpc.add_RecommendationServiceServicer_to_server(
        RecommendationService(), server
    )
    port = "50053"
    server.add_insecure_port("[::]:" + port)
    server.start()
    logging.info(f"Server started. Listening on port {port}.")
    server.wait_for_termination()


if __name__ == "__main__":
    try:
        serve()
    except Exception as e:
        logging.error(f"Failed to start recommendation service: {e}")
        raise e

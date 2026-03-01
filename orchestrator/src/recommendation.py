import os
import sys

import grpc

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
recommendation_system_grpc_path = os.path.abspath(os.path.join(FILE, "../../../utils/pb/recommendation_system"))
sys.path.insert(0, recommendation_system_grpc_path)
import recommendation_system_pb2 as recommendation_system
import recommendation_system_pb2_grpc as recommendation_system_grpc

utils_path = os.path.abspath(os.path.join(FILE, "../../../utils/"))
sys.path.insert(0, utils_path)
from log_utils.logger import setup_logger

logger = setup_logger("Orchestrator")

RECOMMENDATION_GRPC_TARGET = os.environ.get("RECOMMENDATION_GRPC_TARGET", "recomendation_sys:50053")


def format_recommendation_log(books: list[dict]) -> str:
    if not books:
        return "[]"
    return "; ".join(
        f"{book.get('bookId', '')} | {book.get('title', '')}"
        for book in books
    )


def _normalize_suggestions(response: recommendation_system.RecommendationResponse) -> list[dict]:
    normalized = []
    for raw in response.suggested_books[:3]:
        book_id = str(raw.book_id or "").strip()
        title = str(raw.title or "").strip()
        author = str(raw.author or "").strip()
        if not book_id or not title or not author:
            continue

        result = {
            "bookId": book_id,
            "title": title,
            "author": author,
        }

        reason = str(raw.reason or "").strip()
        if reason:
            result["reason"] = reason

        description = str(raw.description or "").strip()
        if description:
            result["description"] = description

        normalized.append(result)
    return normalized


async def get_recommendations(request_data: dict):
    user_comment = request_data.get("userComment", "")
    items = [
        recommendation_system.OrderItem(
            name=str(item.get("name", "")),
            quantity=int(item.get("quantity", 0)),
        )
        for item in request_data.get("items", [])
        if isinstance(item, dict)
    ]

    rpc_request = recommendation_system.RecommendationRequest(
        user_comment=str(user_comment or ""),
        items=items,
        top_k=3,
    )

    try:
        async with grpc.aio.insecure_channel(RECOMMENDATION_GRPC_TARGET) as channel:
            stub = recommendation_system_grpc.RecommendationServiceStub(channel)
            response = await stub.GetRecommendations(rpc_request)
        recommendations = _normalize_suggestions(response)
        if response.error_message:
            logger.error(f"Recommendation service returned error: {response.error_message}")
        logger.info(
            f"Got {len(recommendations)} recommendations from recommendation service: "
            f"{format_recommendation_log(recommendations)}"
        )
        return {
            "service": "recommendation",
            "data": {"suggested_books": recommendations},
        }
    except Exception as exc:
        logger.error(f"Recommendation RPC failed: {str(exc)}")
        return {
            "service": "recommendation",
            "data": {"suggested_books": []},
        }

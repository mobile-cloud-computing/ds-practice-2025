import json
import os
import re
import sys
from concurrent import futures
from typing import Any

import grpc
from openai import OpenAI

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
recommendation_system_grpc_path = os.path.abspath(os.path.join(FILE, "../../../utils/pb/recommendation_system"))
sys.path.insert(0, recommendation_system_grpc_path)
import recommendation_system_pb2 as recommendation_system
import recommendation_system_pb2_grpc as recommendation_system_grpc

utils_path = os.path.abspath(os.path.join(FILE, "../../../utils/"))
sys.path.insert(0, utils_path)
from log_utils.logger import setup_logger

logger = setup_logger("RecommendationSystem")

OPENAI_MODEL = os.environ.get("OPENAI_MODEL") or "gpt-5.2"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
open_ai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

BOOK_CATALOG: list[dict[str, Any]] = [
    {
        "bookId": "b101",
        "title": "The Hobbit",
        "author": "J.R.R. Tolkien",
        "genres": ["fantasy", "adventure"],
        "description": "A classic fantasy quest with dwarves, dragons and world-building.",
    },
    {
        "bookId": "b102",
        "title": "The Fellowship of the Ring",
        "author": "J.R.R. Tolkien",
        "genres": ["fantasy", "epic"],
        "description": "First part of an epic fantasy trilogy focused on friendship and danger.",
    },
    {
        "bookId": "b103",
        "title": "Dune",
        "author": "Frank Herbert",
        "genres": ["science fiction", "epic"],
        "description": "Political intrigue, strategy and survival on a desert planet.",
    },
    {
        "bookId": "b104",
        "title": "Foundation",
        "author": "Isaac Asimov",
        "genres": ["science fiction", "classic"],
        "description": "A long-term plan to preserve civilization through predictive science.",
    },
    {
        "bookId": "b105",
        "title": "Gone Girl",
        "author": "Gillian Flynn",
        "genres": ["thriller", "mystery"],
        "description": "Dark psychological thriller with twists and unreliable narration.",
    },
    {
        "bookId": "b106",
        "title": "The Girl with the Dragon Tattoo",
        "author": "Stieg Larsson",
        "genres": ["thriller", "crime", "mystery"],
        "description": "Investigative mystery with crime, secrets and strong characters.",
    },
    {
        "bookId": "b107",
        "title": "Atomic Habits",
        "author": "James Clear",
        "genres": ["self-help", "productivity"],
        "description": "Practical system to build good habits and break bad ones.",
    },
    {
        "bookId": "b108",
        "title": "Mistborn: The Final Empire",
        "author": "Brandon Sanderson",
        "genres": ["fantasy", "adventure"],
        "description": "Fast-paced fantasy with heist elements and unique magic.",
    },
    {
        "bookId": "b109",
        "title": "Educated",
        "author": "Tara Westover",
        "genres": ["memoir", "biography"],
        "description": "A memoir about identity, family and education.",
    },
    {
        "bookId": "b110",
        "title": "The Name of the Wind",
        "author": "Patrick Rothfuss",
        "genres": ["fantasy", "adventure"],
        "description": "Character-driven fantasy focused on story, music and ambition.",
    },
    {
        "bookId": "b111",
        "title": "Deep Work",
        "author": "Cal Newport",
        "genres": ["productivity", "self-help"],
        "description": "Strategies for focused work in a distracted world.",
    },
    {
        "bookId": "b112",
        "title": "Project Hail Mary",
        "author": "Andy Weir",
        "genres": ["science fiction", "adventure"],
        "description": "Science-driven survival mission with humor and suspense.",
    },
    {
        "bookId": "b113",
        "title": "The Silent Patient",
        "author": "Alex Michaelides",
        "genres": ["thriller", "mystery"],
        "description": "A psychological mystery with a central shocking reveal.",
    },
    {
        "bookId": "b114",
        "title": "Thinking, Fast and Slow",
        "author": "Daniel Kahneman",
        "genres": ["psychology", "non-fiction"],
        "description": "How people think, decide and make mistakes in judgment.",
    },
]

BOOK_BY_ID = {book["bookId"]: book for book in BOOK_CATALOG}


def format_recommendation_log(books: list[recommendation_system.RecommendedBook]) -> str:
    if not books:
        return "[]"
    return "; ".join(
        f"{book.book_id} | {book.title} | reason={book.reason}"
        for book in books
    )


def parse_ai_json_object(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text or "", flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in AI response.")
    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("AI response JSON is not an object.")
    return parsed


def request_ai_recommendations(cart_titles: list[str], comment: str, top_k: int) -> list[recommendation_system.RecommendedBook]:
    if not open_ai_client:
        raise RuntimeError("OPENAI_API_KEY is missing for AI-only recommendation mode.")

    prompt = f"""You are a book recommendation engine.

Task:
- Choose exactly {top_k} books from CATALOG for this user.
- Use only semantic relevance to the user's cart and comment.
- Never recommend a title already present in cart_titles.
- Return only valid JSON, no markdown.

Required output JSON schema:
{{
  "recommendations": [
    {{
      "bookId": "string",
      "reason": "short plain-English sentence",
      "shortDescription": "one short sentence about the book"
    }}
  ]
}}

INPUT:
{{
  "cart_titles": {json.dumps(cart_titles)},
  "user_comment": {json.dumps(comment)},
  "catalog": {json.dumps(BOOK_CATALOG)}
}}
"""

    response = open_ai_client.responses.create(
        model=OPENAI_MODEL,
        input=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_output_tokens=400,
    )
    parsed = parse_ai_json_object((response.output_text or "").strip())
    raw_recommendations = parsed.get("recommendations", [])
    if not isinstance(raw_recommendations, list):
        raise ValueError("AI output field 'recommendations' is not a list.")

    cart_title_set = {title.lower() for title in cart_titles if title}
    results: list[recommendation_system.RecommendedBook] = []
    used_ids: set[str] = set()

    for entry in raw_recommendations:
        if not isinstance(entry, dict):
            continue

        book_id = str(entry.get("bookId", "")).strip()
        reason = str(entry.get("reason", "")).strip()
        short_description = str(entry.get("shortDescription", "")).strip()
        book = BOOK_BY_ID.get(book_id)
        if not book:
            continue
        if book_id in used_ids:
            continue
        if book["title"].lower() in cart_title_set:
            continue
        if not reason:
            reason = "Selected by AI based on your cart and preferences."
        if not short_description:
            short_description = str(book.get("description", "")).strip()

        results.append(
            recommendation_system.RecommendedBook(
                book_id=book["bookId"],
                title=book["title"],
                author=book["author"],
                reason=reason,
                description=short_description,
            )
        )
        used_ids.add(book_id)
        if len(results) >= top_k:
            break

    if len(results) < top_k:
        raise ValueError("AI returned too few valid recommendations.")

    return results


class RecommendationService(recommendation_system_grpc.RecommendationServiceServicer):
    def GetRecommendations(self, request, context):
        try:
            top_k = max(1, min(int(request.top_k or 3), 10))
            cart_titles = [item.name.strip() for item in request.items if item.name]
            comment = request.user_comment or ""
            suggested_books = request_ai_recommendations(cart_titles, comment, top_k)
            logger.info(
                f"Generated {len(suggested_books)} AI-only recommendations: "
                f"{format_recommendation_log(suggested_books)}"
            )
            return recommendation_system.RecommendationResponse(suggested_books=suggested_books)
        except Exception as exc:
            logger.error(f"Error during recommendation: {str(exc)}")
            return recommendation_system.RecommendationResponse(
                suggested_books=[],
                error_message=str(exc),
            )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    recommendation_system_grpc.add_RecommendationServiceServicer_to_server(RecommendationService(), server)
    port = "50053"
    server.add_insecure_port("[::]:" + port)
    server.start()
    logger.info(f"Server started. Listening on port {port}.")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

import json
import os
import re
import sys
import threading
from concurrent import futures
from typing import Any

import grpc
from openai import OpenAI

FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
base_dir = os.path.dirname(os.path.abspath(FILE))
utils_path = os.path.abspath(os.path.join(base_dir, "../../utils"))
services_pb_path = os.path.abspath(os.path.join(utils_path, "pb/services"))
pb_path = os.path.abspath(os.path.join(utils_path, "pb"))
sys.path.insert(0, utils_path)
sys.path.insert(0, services_pb_path)
sys.path.insert(0, pb_path)
from log_utils.logger import setup_logger
from service_wrappers.base_service_wrapper import BaseServiceWrapper

import pb.services.order_details_pb2 as order_details
import pb.services.recommendation_system_pb2 as recommendation_system
import pb.services.recommendation_system_pb2_grpc as recommendation_system_grpc

logger = setup_logger("RecommendationSystem")

OPENAI_MODEL = (os.environ.get("OPENAI_MODEL") or "gpt-5.2").strip() or "gpt-5.2"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
open_ai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
DEFAULT_TOP_K = 3

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
GENRE_HINTS = {
    "fantasy": ["fantasy", "magic", "wizard", "dragon", "epic"],
    "science fiction": ["sci-fi", "science fiction", "space", "future", "alien"],
    "thriller": ["thriller", "suspense", "dark", "serial", "crime"],
    "mystery": ["mystery", "detective", "investigation", "whodunit"],
    "self-help": ["habit", "self-help", "motivation", "improvement"],
    "productivity": ["productivity", "focus", "work", "efficiency"],
}


def format_recommendation_log(books: list[order_details.RecommendedBook]) -> str:
    if not books:
        return "[]"
    return "; ".join(
        f"{book.book_id} | {book.title} | reason={book.reason}" for book in books
    )


def parse_ai_json_object(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text or "", flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in AI response.")
    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("AI response JSON is not an object.")
    return parsed


def _fallback_recommendations(cart_titles: list[str], top_k: int) -> list[order_details.RecommendedBook]:
    cart_title_set = {title.lower() for title in cart_titles if title}
    candidates = [
        book for book in BOOK_CATALOG if book["title"].lower() not in cart_title_set
    ]

    suggestions: list[order_details.RecommendedBook] = []
    for book in candidates[:top_k]:
        suggestions.append(
            order_details.RecommendedBook(
                book_id=book["bookId"],
                title=book["title"],
                author=book["author"],
                reason="Selected from catalog as a compatible fallback recommendation.",
                description=book["description"],
            )
        )
    return suggestions


def _extract_comment_genres(comment: str) -> list[str]:
    lowered = (comment or "").lower()
    if not lowered:
        return []
    genres = []
    for genre, hints in GENRE_HINTS.items():
        if any(hint in lowered for hint in hints):
            genres.append(genre)
    return genres


def _extract_cart_genres(cart_titles: list[str]) -> list[str]:
    title_set = {title.lower() for title in cart_titles if title}
    genres = set()
    for book in BOOK_CATALOG:
        if book["title"].lower() in title_set:
            for genre in book.get("genres", []):
                genres.add(genre)
    return sorted(genres)


def _genre_fallback_recommendations(
    cart_titles: list[str], preferred_genres: list[str], top_k: int
) -> list[order_details.RecommendedBook]:
    cart_title_set = {title.lower() for title in cart_titles if title}
    preferred = set(preferred_genres)
    scored: list[tuple[int, dict[str, Any]]] = []

    for book in BOOK_CATALOG:
        if book["title"].lower() in cart_title_set:
            continue
        overlap = len(preferred.intersection(book.get("genres", [])))
        scored.append((overlap, book))

    scored.sort(key=lambda item: (item[0], item[1]["bookId"]), reverse=True)
    out: list[order_details.RecommendedBook] = []
    for overlap, book in scored[:top_k]:
        reason = (
            f"Matched your preferred genres: {', '.join(sorted(preferred.intersection(book.get('genres', []))))}."
            if overlap > 0
            else "Selected from catalog as a compatible fallback recommendation."
        )
        out.append(
            order_details.RecommendedBook(
                book_id=book["bookId"],
                title=book["title"],
                author=book["author"],
                reason=reason,
                description=book["description"],
            )
        )
    return out


def request_ai_recommendations(
    cart_titles: list[str], comment: str, top_k: int
) -> list[order_details.RecommendedBook]:
    if not open_ai_client:
        raise RuntimeError("OPENAI_API_KEY is missing.")

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
    results: list[order_details.RecommendedBook] = []
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
            order_details.RecommendedBook(
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


class RecommendationService(
    BaseServiceWrapper, recommendation_system_grpc.RecommendationServiceServicer
):
    def __init__(self, service_id: int, n_services: int):
        super().__init__(service_id, n_services)
        self._lock = threading.Lock()
        self.order_vector_clocks: dict[str, list[int]] = {}
        self.order_event_data: dict[str, dict[str, Any]] = {}

    def _normalize_clock(self, vector_clock: list[int]) -> list[int]:
        normalized = list(vector_clock)
        if len(normalized) < self.n_services:
            normalized += [0] * (self.n_services - len(normalized))
        return normalized[: self.n_services]

    def _touch_event_clock(self, order_id: str, incoming_clock: list[int], event_name: str) -> list[int]:
        with self._lock:
            local_clock = self.order_vector_clocks.get(order_id, [0] * self.n_services)
            merged = [max(local_clock[i], incoming_clock[i]) for i in range(self.n_services)]
            merged[self.service_id] += 1
            self.order_vector_clocks[order_id] = merged
            self.vector_clock = list(merged)

        logger.info(f"{event_name} order_id={order_id}, vector_clock={merged}")
        return merged

    def _status(
        self, order_id: str, success: bool, error_message: str = "", vector_clock: list[int] | None = None
    ) -> order_details.StatusMessage:
        clock_to_use = vector_clock
        if clock_to_use is None:
            with self._lock:
                clock_to_use = list(self.order_vector_clocks.get(order_id, [0] * self.n_services))
        return order_details.StatusMessage(
            success=success,
            order_id=order_id,
            vector_clock=clock_to_use,
            error_message=error_message,
        )

    def InitTransaction(self, request, context):
        with self._lock:
            self.order_details[request.order_id] = request
            self.order_vector_clocks[request.order_id] = [0] * self.n_services
            self.order_event_data[request.order_id] = {
                "cart_titles": [],
                "cart_genres": [],
                "comment": "",
                "comment_genres": [],
                "suggested_books": [],
            }
        logger.info(
            f"InitTransaction order_id={request.order_id}, "
            f"vector_clock={self.order_vector_clocks[request.order_id]}"
        )
        return self._status(order_id=request.order_id, success=True)

    def ExtractCartSignals(self, request, context):
        order_id = request.order_id
        with self._lock:
            data = self.order_details.get(order_id)

        if data is None:
            error_message = f"Order id {order_id} is not found"
            logger.error(error_message)
            status = self._status(order_id=order_id, success=False, error_message=error_message)
            return status

        try:
            cart_titles = [item.name.strip() for item in data.items if item.name]
            cart_genres = _extract_cart_genres(cart_titles)
            event_clock = self._touch_event_clock(
                order_id=order_id,
                incoming_clock=self._normalize_clock(request.vector_clock),
                event_name="ExtractCartSignals",
            )

            with self._lock:
                self.order_event_data[order_id]["cart_titles"] = cart_titles
                self.order_event_data[order_id]["cart_genres"] = cart_genres

            if not cart_titles:
                return self._status(
                    order_id=order_id,
                    success=False,
                    error_message="No cart items available for recommendation analysis.",
                    vector_clock=event_clock,
                )
            return self._status(order_id=order_id, success=True, vector_clock=event_clock)
        except Exception as exc:
            error_message = f"ExtractCartSignals failed: {str(exc)}"
            logger.error(error_message)
            return self._status(order_id=order_id, success=False, error_message=error_message)

    def ExtractCommentSignals(self, request, context):
        order_id = request.order_id
        with self._lock:
            data = self.order_details.get(order_id)
        if data is None:
            error_message = f"Order id {order_id} is not found"
            logger.error(error_message)
            return self._status(order_id=order_id, success=False, error_message=error_message)

        try:
            comment = data.user_comment or ""
            comment_genres = _extract_comment_genres(comment)
            event_clock = self._touch_event_clock(
                order_id=order_id,
                incoming_clock=self._normalize_clock(request.vector_clock),
                event_name="ExtractCommentSignals",
            )

            with self._lock:
                self.order_event_data[order_id]["comment"] = comment
                self.order_event_data[order_id]["comment_genres"] = comment_genres

            return self._status(order_id=order_id, success=True, vector_clock=event_clock)
        except Exception as exc:
            error_message = f"ExtractCommentSignals failed: {str(exc)}"
            logger.error(error_message)
            return self._status(order_id=order_id, success=False, error_message=error_message)

    def GenerateRecommendations(self, request, context):
        order_id = request.order_id
        with self._lock:
            data = self.order_details.get(order_id)
            event_data = self.order_event_data.get(order_id)

        if data is None or event_data is None:
            error_message = f"Order id {order_id} is not found"
            logger.error(error_message)
            return self._status(order_id=order_id, success=False, error_message=error_message)

        try:
            event_clock = self._touch_event_clock(
                order_id=order_id,
                incoming_clock=self._normalize_clock(request.vector_clock),
                event_name="GenerateRecommendations",
            )

            cart_titles = list(event_data.get("cart_titles", []))
            comment = str(event_data.get("comment", ""))
            preferred_genres = sorted(
                set(event_data.get("cart_genres", [])).union(event_data.get("comment_genres", []))
            )

            if not cart_titles:
                cart_titles = [item.name.strip() for item in data.items if item.name]

            try:
                suggested_books = request_ai_recommendations(cart_titles, comment, DEFAULT_TOP_K)
            except Exception as exc:
                logger.warning(f"AI recommendation failed for order_id={order_id}: {str(exc)}")
                if preferred_genres:
                    suggested_books = _genre_fallback_recommendations(cart_titles, preferred_genres, DEFAULT_TOP_K)
                else:
                    suggested_books = _fallback_recommendations(cart_titles, DEFAULT_TOP_K)

            with self._lock:
                self.order_event_data[order_id]["suggested_books"] = suggested_books

            if not suggested_books:
                return self._status(
                    order_id=order_id,
                    success=False,
                    error_message="Recommendation generation produced no books.",
                    vector_clock=event_clock,
                )

            return self._status(order_id=order_id, success=True, vector_clock=event_clock)
        except Exception as exc:
            error_message = f"GenerateRecommendations failed: {str(exc)}"
            logger.error(error_message)
            return self._status(order_id=order_id, success=False, error_message=error_message)

    def ValidateRecommendations(self, request, context):
        order_id = request.order_id
        with self._lock:
            data = self.order_details.get(order_id)
            event_data = self.order_event_data.get(order_id)

        if data is None or event_data is None:
            error_message = f"Order id {order_id} is not found"
            logger.error(error_message)
            return self._status(order_id=order_id, success=False, error_message=error_message)

        try:
            event_clock = self._touch_event_clock(
                order_id=order_id,
                incoming_clock=self._normalize_clock(request.vector_clock),
                event_name="ValidateRecommendations",
            )

            cart_titles = {item.name.strip().lower() for item in data.items if item.name}
            raw_books: list[order_details.RecommendedBook] = list(event_data.get("suggested_books", []))
            seen_ids = set()
            valid_books: list[order_details.RecommendedBook] = []
            for book in raw_books:
                book_id = str(book.book_id or "").strip()
                title = str(book.title or "").strip().lower()
                if not book_id or not title:
                    continue
                if book_id in seen_ids:
                    continue
                if title in cart_titles:
                    continue
                if book_id not in BOOK_BY_ID:
                    continue
                seen_ids.add(book_id)
                valid_books.append(book)
                if len(valid_books) >= DEFAULT_TOP_K:
                    break

            with self._lock:
                self.order_event_data[order_id]["suggested_books"] = valid_books

            if not valid_books:
                return self._status(
                    order_id=order_id,
                    success=False,
                    error_message="All generated recommendations were filtered out.",
                    vector_clock=event_clock,
                )

            return self._status(order_id=order_id, success=True, vector_clock=event_clock)
        except Exception as exc:
            error_message = f"ValidateRecommendations failed: {str(exc)}"
            logger.error(error_message)
            return self._status(order_id=order_id, success=False, error_message=error_message)

    def _run_event_thread(self, method, request, result_container: dict[str, Any], key: str):
        try:
            result_container[key] = method(request, None)
        except Exception as exc:
            result_container[key] = self._status(
                order_id=request.order_id,
                success=False,
                error_message=f"{key} thread failed: {str(exc)}",
            )

    def GetRecommendations(self, request, context):
        order_id = request.order_id
        with self._lock:
            data = self.order_details.get(order_id)

        if data is None:
            status = self._status(
                order_id=order_id,
                success=False,
                error_message=f"Order id {order_id} is not found",
            )
            result = order_details.OrderResponce()
            result.status.CopyFrom(status)
            return result

        start_clock = self._touch_event_clock(
            order_id=order_id,
            incoming_clock=self._normalize_clock(request.vector_clock),
            event_name="GetRecommendations",
        )

        result_container: dict[str, order_details.StatusMessage] = {}
        cart_req = order_details.OperationalMessage(order_id=order_id, vector_clock=start_clock)
        comment_req = order_details.OperationalMessage(order_id=order_id, vector_clock=start_clock)

        event_cart = threading.Thread(
            target=self._run_event_thread,
            kwargs={
                "method": self.ExtractCartSignals,
                "request": cart_req,
                "result_container": result_container,
                "key": "ExtractCartSignals",
            },
        )
        event_comment = threading.Thread(
            target=self._run_event_thread,
            kwargs={
                "method": self.ExtractCommentSignals,
                "request": comment_req,
                "result_container": result_container,
                "key": "ExtractCommentSignals",
            },
        )
        event_cart.start()
        event_comment.start()
        event_cart.join()
        event_comment.join()

        if any(not result_container[key].success for key in result_container):
            error_message = "; ".join(
                result_container[key].error_message
                for key in result_container
                if not result_container[key].success
            )
            status = self._status(order_id=order_id, success=False, error_message=error_message)
            result = order_details.OrderResponce()
            result.status.CopyFrom(status)
            return result

        gen_req = order_details.OperationalMessage(
            order_id=order_id, vector_clock=self._status(order_id, True).vector_clock
        )
        gen_status = self.GenerateRecommendations(gen_req, context)
        if not gen_status.success:
            result = order_details.OrderResponce()
            result.status.CopyFrom(gen_status)
            return result

        validate_req = order_details.OperationalMessage(
            order_id=order_id, vector_clock=gen_status.vector_clock
        )
        validate_status = self.ValidateRecommendations(validate_req, context)
        if not validate_status.success:
            result = order_details.OrderResponce()
            result.status.CopyFrom(validate_status)
            return result

        with self._lock:
            suggested_books = list(self.order_event_data.get(order_id, {}).get("suggested_books", []))

        success_status = self._status(
            order_id=order_id,
            success=True,
            vector_clock=validate_status.vector_clock,
        )
        result = order_details.OrderResponce()
        result.status.CopyFrom(success_status)
        result.recommended_books.extend(suggested_books)
        logger.info(
            f"Generated {len(suggested_books)} recommendations for order_id={order_id}: "
            f"{format_recommendation_log(suggested_books)}"
        )
        return result

    def ClearTransaction(self, request, context):
        order_id = request.order_id
        incoming_clock = self._normalize_clock(request.vector_clock)
        with self._lock:
            local_clock = list(self.order_vector_clocks.get(order_id, [0] * self.n_services))

        can_clear = all(local_clock[i] <= incoming_clock[i] for i in range(self.n_services))
        if not can_clear:
            error_message = (
                f"Clear rejected for order_id={order_id}: "
                f"local vector clock {local_clock} is not <= final vector clock {incoming_clock}"
            )
            logger.error(error_message)
            return self._status(order_id=order_id, success=False, error_message=error_message)

        clear_clock = self._touch_event_clock(
            order_id=order_id,
            incoming_clock=incoming_clock,
            event_name="ClearTransaction",
        )
        with self._lock:
            if order_id in self.order_details:
                del self.order_details[order_id]
            if order_id in self.order_event_data:
                del self.order_event_data[order_id]
            if order_id in self.order_vector_clocks:
                del self.order_vector_clocks[order_id]

        logger.info(
            f"ClearTransaction order_id={order_id}, final_vector_clock={incoming_clock}, "
            f"service_vector_clock={clear_clock}"
        )
        return order_details.StatusMessage(success=True, order_id=order_id, vector_clock=clear_clock)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    recommendation_system_grpc.add_RecommendationServiceServicer_to_server(
        RecommendationService(2, 3), server
    )
    port = "50053"
    server.add_insecure_port("[::]:" + port)
    server.start()
    logger.info(f"Server started. Listening on port {port}.")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

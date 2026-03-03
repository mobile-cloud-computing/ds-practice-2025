import sys
import os
import logging
import time
from datetime import datetime

# This set of lines are needed to import the gRPC stubs.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
suggestions_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/suggestions'))
sys.path.insert(0, suggestions_grpc_path)
import suggestions_pb2
import suggestions_pb2_grpc

import grpc
from concurrent import futures
from groq import Groq

logging.basicConfig(
    level=logging.INFO,
    format="===LOG=== %(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("suggestions")

# Groq API configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Initialize Groq client
groq_client = None


def _initialize_groq_client():
    """Initialize the Groq API client."""
    global groq_client

    if groq_client is not None:
        return groq_client

    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY environment variable not set!")
        return None

    try:
        logger.info("Initializing Groq client with model: %s", GROQ_MODEL)
        groq_client = Groq(api_key=GROQ_API_KEY)
        logger.info("Groq client initialized successfully")
        return groq_client
    except Exception as e:
        logger.error("Failed to initialize Groq client: %s", e)
        return None


def _call_groq_llm(prompt):
    """Call Groq API to generate book recommendations."""
    client = _initialize_groq_client()

    if client is None:
        logger.error("Groq client not available")
        return None

    try:
        logger.debug("Calling Groq API with model: %s", GROQ_MODEL)

        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful book recommendation assistant. You suggest books in the exact format requested."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model=GROQ_MODEL,
            temperature=0.7,
            max_tokens=300,
        )

        response_text = chat_completion.choices[0].message.content
        return response_text.strip()

    except Exception as e:
        logger.error("Groq API call failed: %s", e)
        return None


def _parse_book_suggestions(llm_response):
    """Parse LLM response to extract book suggestions in format: TITLE - AUTHOR - YEAR."""
    if not llm_response:
        return []

    books = []
    lines = llm_response.strip().split('\n')

    for line in lines:
        line = line.strip()
        # Remove common list markers
        for prefix in ['1.', '2.', '3.', '4.', '5.', '-', '*', '•', '1)', '2)', '3)', '4)', '5)']:
            if line.startswith(prefix):
                line = line[len(prefix):].strip()
                break

        # Skip empty lines or very short lines
        if line and len(line) > 10:
            # Remove quotes if present
            line = line.strip('"\'')
            # Only include lines that look like they have the format with dashes
            if '-' in line:
                books.append(line)

        # Stop after we have 3 books
        if len(books) >= 3:
            break

    # Return up to 3 suggestions
    return books[:3]


def _generate_prompt():
    """Generate a prompt for the LLM based on the current date."""
    now = datetime.now()
    month_name = now.strftime("%B")
    current_year = now.year

    # Determine season
    month = now.month
    if month in [12, 1, 2]:
        season = "winter"
        season_context = "cozy reads for cold weather"
    elif month in [3, 4, 5]:
        season = "spring"
        season_context = "fresh and uplifting stories"
    elif month in [6, 7, 8]:
        season = "summer"
        season_context = "light and engaging beach reads"
    else:
        season = "fall"
        season_context = "thought-provoking autumn reads"

    prompt = f"""It's {month_name} {current_year}, {season} season. Suggest 3 {season_context} that would be perfect for this time of year.

Respond with ONLY the book information, one per line, numbered 1-3, in this EXACT format:
BOOK TITLE - AUTHOR - YEAR

Example:
1. The Great Gatsby - F. Scott Fitzgerald - 1925
2. 1984 - George Orwell - 1949
3. To Kill a Mockingbird - Harper Lee - 1960

Your suggestions:"""

    return prompt


class SuggestionsService(suggestions_pb2_grpc.SuggestionsServiceServicer):
    def GetSuggestions(self, request, context):
        started = time.perf_counter()
        metadata = dict(context.invocation_metadata())
        correlation_id = metadata.get("x-correlation-id", request.transaction_id or "unknown")

        logger.info(
            "cid=%s event=suggestions_received transaction_id=%s purchased_count=%s",
            correlation_id,
            request.transaction_id,
            len(request.purchased_books),
        )

        try:
            # Generate prompt based on current date/season
            prompt = _generate_prompt()

            logger.info(
                "cid=%s event=calling_groq_api reason=seasonal_recommendations",
                correlation_id,
            )

            # Call Groq API to get suggestions
            llm_response = _call_groq_llm(prompt)

            if llm_response is None:
                logger.error(
                    "cid=%s event=groq_api_failed",
                    correlation_id,
                )
                # Fallback to generic suggestions
                suggested_books = [
                    "The Great Gatsby - F. Scott Fitzgerald - 1925",
                    "To Kill a Mockingbird - Harper Lee - 1960",
                    "1984 - George Orwell - 1949"
                ]
            else:
                # Parse LLM response
                suggested_books = _parse_book_suggestions(llm_response)

                # Fallback if parsing failed
                if not suggested_books:
                    logger.warning(
                        "cid=%s event=parsing_failed llm_response_preview=%s using_fallback=true",
                        correlation_id,
                        llm_response[:200] if llm_response else "",
                    )
                    suggested_books = [
                        "The Great Gatsby - F. Scott Fitzgerald - 1925",
                        "To Kill a Mockingbird - Harper Lee - 1960",
                        "1984 - George Orwell - 1949"
                    ]

            latency_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "cid=%s event=suggestions_completed count=%s latency_ms=%.2f suggestions=%s",
                correlation_id,
                len(suggested_books),
                latency_ms,
                suggested_books,
            )

            return suggestions_pb2.SuggestionsResponse(
                suggested_books=suggested_books
            )

        except Exception:
            latency_ms = (time.perf_counter() - started) * 1000
            logger.exception(
                "cid=%s event=suggestions_exception latency_ms=%.2f",
                correlation_id,
                latency_ms,
            )
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal error during suggestions generation")
            return suggestions_pb2.SuggestionsResponse(
                suggested_books=[]
            )


def serve():
    # Initialize Groq client during startup
    logger.info("Starting AI-powered book suggestions service...")
    client = _initialize_groq_client()

    if client is None:
        logger.error("Failed to initialize Groq client - suggestions will use fallback responses")
    else:
        logger.info("Groq client ready - AI-powered suggestions enabled!")

    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor())
    suggestions_pb2_grpc.add_SuggestionsServiceServicer_to_server(SuggestionsService(), server)
    # Listen on port 50053
    port = "50053"
    server.add_insecure_port("[::]:" + port)
    # Start the server
    server.start()
    logger.info("Server started. Listening on port %s.", port)
    # Keep thread alive
    server.wait_for_termination()


if __name__ == '__main__':
    serve()


import sys
import os
import json
import threading

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
fraud_detection_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/suggestions'))
sys.path.insert(0, fraud_detection_grpc_path)
import suggestions_pb2 as suggestions
import suggestions_pb2_grpc as suggestions_grpc

import grpc
from concurrent import futures

import google.genai as genai

SERVICE_NAME = 'suggestions'
ORDER_CACHE = {}
ORDER_CACHE_LOCK = threading.Lock()


def _cache_initialized_order(order_id, order_payload_json, incoming_clock):
    order_data = json.loads(order_payload_json or '{}')
    vector_clock = dict(incoming_clock)
    vector_clock[SERVICE_NAME] = vector_clock.get(SERVICE_NAME, 0) + 1

    with ORDER_CACHE_LOCK:
        ORDER_CACHE[order_id] = {
            'order_data': order_data,
            'vector_clock': vector_clock,
        }

    return vector_clock


def _touch_order(order_id):
    with ORDER_CACHE_LOCK:
        cached_order = ORDER_CACHE.get(order_id)
        if not cached_order:
            return None

        cached_order['vector_clock'][SERVICE_NAME] = cached_order['vector_clock'].get(SERVICE_NAME, 0) + 1
        return {
            'order_data': cached_order['order_data'],
            'vector_clock': dict(cached_order['vector_clock']),
        }

class SuggestionsService(suggestions_grpc.SuggestionsServiceServicer):
    def InitOrder(self, request, context):
        try:
            vector_clock = _cache_initialized_order(request.order_id, request.order_payload_json, request.vector_clock)
        except json.JSONDecodeError:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details('Invalid order payload JSON.')
            return suggestions.InitOrderResponse(acknowledged=False)

        print(f"Initialized order {request.order_id} with vector clock {vector_clock}")
        return suggestions.InitOrderResponse(acknowledged=True)

    # Create an RPC function to get suggestions
    def GetSuggestions(self, request, context):
        cached_order = _touch_order(request.order_id) if request.order_id else None
        user_id = request.user_id
        selected_books = ["Harry Potter and the Philosopher's Stone by J.K. Rowling", "The Hobbit by J.R.R. Tolkien"]
        selected_titles = [book.split(' by ')[0].strip() for book in selected_books]

        # Create a SuggestionsResponse object
        response = suggestions.SuggestionsResponse()
        # Set the suggestions field of the response object

        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

        input_promt = (
            "You are a bookstore recommendation assistant. "
            f"User id: {user_id}. "
            f"Selected books: {selected_books}. "
            "Suggest exactly 3 additional books related to selected books. "
            "Rules: suggestions must be different from selected books. "
            "Output strictly 3 lines, each line in exact format: Title by Author. "
            "No numbering, no bullets, no extra text."
        )
        print(f"Generating suggestions for user: {user_id} with prompt: {input_promt}")
        # Generate suggestions using Gemini 2.5 Flash Lite model
        response_ai = client.models.generate_content(
            model="gemini-2.5-flash-lite", contents=input_promt
        )

        clean = []
        selected_titles_lower = {title.lower() for title in selected_titles}
        # Process the response to extract suggestions, ensuring they are in the correct format and not duplicates of selected books
        for line in response_ai.text.split('\n'):
            entry = line.strip()
            if not entry or len(clean) >= 3:
                continue

            if ' by ' in entry:
                title = entry.split(' by ', 1)[0].strip()
                if title.lower() not in selected_titles_lower and entry not in clean:
                    clean.append(entry)
            elif entry not in clean:
                clean.append(entry)
        # If the model does not return 3 valid suggestions, add fallback suggestions to ensure we always return 3 suggestions
        fallback = [
            "Dune by Frank Herbert",
            "1984 by George Orwell",
            "Foundation by Isaac Asimov"
        ]
        for item in fallback:
            if len(clean) >= 3:
                break
            if item not in clean:
                clean.append(item)

        response.suggestions.extend(clean)
        # Print the user id and the suggestions sent back
        print(
            f"Received suggestion request for order_id={request.order_id or '[none]'}, user: {user_id}, "
            f"vector_clock={cached_order['vector_clock'] if cached_order else {SERVICE_NAME: 1}}, "
            f"sending suggestions: {response.suggestions}"
        )
        # Return the response object
        return response

def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor())
    # Add SuggestionsService
    suggestions_grpc.add_SuggestionsServiceServicer_to_server(SuggestionsService(), server)
    # Listen on port 50053
    port = "50053"
    server.add_insecure_port("[::]:" + port)
    # Start the server
    server.start()
    print("Server started. Listening on port 50053.")
    # Keep thread alive
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
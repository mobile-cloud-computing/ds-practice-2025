import sys
import os

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

class SuggestionsService(suggestions_grpc.SuggestionsServiceServicer):
    # Create an RPC function to get suggestions
    def GetSuggestions(self, request, context):
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
        print(f"Received suggestion request for user: {user_id}, sending suggestions: {response.suggestions}")
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
import sys
import os

FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")
utils_path = os.path.abspath(os.path.join(FILE, "../../../utils/pb/bookstore/suggestions"))
sys.path.insert(0, utils_path)
import suggestions_pb2 as suggestions
import suggestions_pb2_grpc as suggestions_grpc

import grpc
from concurrent import futures
import requests
from google import genai
import json
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("API_KEY")
print(api_key,"api_key")
API_KEY = "AIzaSyA7k3mveCWpA5MrnZ92G3lbGQ_RE6FBjhI"
class BookSuggestionService(suggestions_grpc.SuggestionsServiceServicer):
    def SuggestBooks(self, request,context):
        #have an gemini api call to get the suggestions
        print("Request:", request.book_name)
        prompt = f"""
List a few popular books similar to {request.book_name} in JSON format.

Use this JSON schema:

SuggestedBooks = {{'book_title': str, 'book_author': str}}
Return: list[SuggestedBooks]
"""
        client = genai.Client(api_key=API_KEY)
        suggested_books = client.models.generate_content(
            model="gemini-2.0-flash", contents=prompt
        )
        result = suggested_books.text.replace("```json", "").replace("```", "").strip()
    
        print(json.loads(result),"after parse")
        response = suggestions.SuggestionsResponse(
            suggestions=json.loads(result),
        )
        
        return response
       
def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor())
    # Add BookSuggestionService
    suggestions_grpc.add_SuggestionsServiceServicer_to_server(BookSuggestionService(), server)
    # Listen on port 50053
    port = "50053"
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"Book Suggestion Server started. Listening on port {port}.")

    server.wait_for_termination()

if __name__ == "__main__":
    serve()
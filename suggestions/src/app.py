import sys
import os
import logging
import grpc
import requests  # Import requests to call third-party API
from concurrent import futures

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
suggestion_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/suggestions'))
sys.path.insert(0, suggestion_grpc_path)


# Import gRPC generated classes
import suggestions_pb2 as suggestion
import suggestions_pb2_grpc as suggestion_grpc

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Third-party book API (Example: Open Library API)
BOOK_API_URL = "https://openlibrary.org/search.json"



class SuggestionService(suggestion_grpc.SuggestionServiceServicer):

    def GetSuggestions(self, request, context):
        query = request.query
        logger.info(f"Received request for suggestions based on query: {query}")
        
        books = self.fetch_books(query)

        # Prepare response
        response = suggestion.SuggestionsResponse()
        response.suggestedBooks.extend(books)

        logger.info(f"Returning {len(books)} suggestions for query '{query}'")
        return response

    def fetch_books(self, query):
        try:
            logger.debug(f"Fetching books from API for query: {query}")
            response = requests.get(BOOK_API_URL, params={"q": query, "limit": 5})
            response.raise_for_status()  # Raise an error for non-2xx status codes
            data = response.json()

            books = []
            for doc in data.get("docs", [])[:5]:  # Get top 5 results
                book = suggestion.Book(
                    title=doc.get("title", "Unknown"),
                    author=doc["author_name"][0] if "author_name" in doc else "Unknown",
                    description="N/A",  # Open Library doesn't provide descriptions
                    link=f"https://openlibrary.org{doc.get('key', '')}"
                )
                books.append(book)

            logger.debug(f"Fetched {len(books)} books for query '{query}'")
            return books
        except Exception as e:
            logger.error(f"Error fetching books: {e}")
            return []

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    suggestion_grpc.add_SuggestionServiceServicer_to_server(SuggestionService(), server)

    port = "50053"
    server.add_insecure_port(f"[::]:{port}")
    server.start()

    logger.info(f"Server started. Listening on port {port}.")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()

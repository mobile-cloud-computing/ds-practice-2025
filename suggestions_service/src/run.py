import sys
from pathlib import Path

current_dir = Path(__file__).parent.absolute()
app_dir = current_dir.parent.parent
sys.path.insert(0, str(app_dir))

import utils.pb.suggestions_service.suggestions_service_pb2 as suggestions_service
import utils.pb.suggestions_service.suggestions_service_pb2_grpc as suggestions_service_grpc
from utils.pb.suggestions_service.suggestions_service_pb2 import Book
from utils.logger import logger
import grpc
from concurrent import futures

logs = logger.get_module_logger("SUGGESTIONS")

class BookSuggester(suggestions_service_grpc.SuggestionServiceServicer):
    def Suggest(self, request, context):
        response = suggestions_service.SuggestionResponse()
        book1 = Book(id=1, author="Royal Tenenbaum", name="How to??") 
        book2 = Book(id=2, author="Royal Tenenbaum II", name="To how??") 
        response.book_suggestions.extend([book1, book2]) 
        logs.info("Suggested books.")
        return response

def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor())

    suggestions_service_grpc.add_SuggestionServiceServicer_to_server((BookSuggester()), server)

    port = "50053"
    server.add_insecure_port("[::]:" + port)
    server.start()
    logs.info(f"Server started. Listening on port {port}.")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()

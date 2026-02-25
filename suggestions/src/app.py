import sys
import os

from fraud_detection.src.app import FraudDetectionService
from utils.pb import fraud_detection

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
    
class SuggestionsService(suggestions_grpc.SuggestionsServiceServicer):
    # Create an RPC function to get suggestions
    def GetSuggestions(self, request, context):
        user_id = request.user_id

        # Create a SuggestionsResponse object
        response = suggestions.SuggestionsResponse()
        # Set the suggestions field of the response object
        response.suggestions.extend(["Book A", "Book B", "Book C"])  # Example static suggestions
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
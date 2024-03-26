import sys
import os
from datetime import datetime

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
utils_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb'))
sys.path.insert(0, utils_path)
from book_suggestion import book_suggestion_pb2 as book_suggestion
from book_suggestion import book_suggestion_pb2_grpc as book_suggestion_grpc

from concurrent import futures
import grpc
import json
import random

# Get the server index for the vector clock.
SERVER_INDEX = int(os.getenv("SERVER_INDEX_FOR_VECTOR_CLOCK"))

with open(os.path.abspath(os.path.join(FILE, '../book_list.json'))) as f:
    book_list_json = json.load(f)
    book_list = [book_list_json[key] for key in book_list_json]

# Increment the value in the server index, and update the timestamp.
# If the index isn't in the vc_array, append 0 until the index.
def increment_vector_clock(vector_clock):
    vc_array = vector_clock.vcArray
    timestamp = datetime.now().timestamp()

    if SERVER_INDEX <= len(vc_array) - 1:
        vc_array[SERVER_INDEX] += 1
    else:
        while len(vc_array) != SERVER_INDEX:
            vc_array.append(0)
        vc_array.append(1)

    return {"vcArray": vc_array, "timestamp": timestamp}

class BookSuggestionService(book_suggestion_grpc.BookSuggestionServiceServicer):

    def SuggestBook(self, request, context):
        print("Boook Suggestion request received")
        print(f"[Book suggestion] Server index: {SERVER_INDEX}")

        vector_clock = request.vectorClock
        vector_clock = increment_vector_clock(vector_clock)

        print(f"[Book suggestion] VCArray updated in Book suggestion: {vector_clock['vcArray']}")
        print(f"[Book suggestion] Timestamp updated in Book suggestion: {vector_clock['timestamp']}")

        print(f"Ordered Book: {request.item}")
        suggest_books = random.sample(book_list, 2)
        
        response = {
            "isValid": True,
            "errorMessage": None,
            "books": suggest_books
        }
        return book_suggestion.BookSuggestionResponse(**response)

    
def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    book_suggestion_grpc.add_BookSuggestionServiceServicer_to_server(BookSuggestionService(), server)
    server.add_insecure_port('[::]:50053')
    server.start()
    print("Book Suggestion Service started on port 50053")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
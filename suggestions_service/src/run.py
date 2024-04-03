import sys
from pathlib import Path

current_dir = Path(__file__).parent.absolute()
app_dir = current_dir.parent.parent
sys.path.insert(0, str(app_dir))
cache = {}

import utils.pb.suggestions_service.suggestions_service_pb2 as suggestions_service
import utils.pb.suggestions_service.suggestions_service_pb2_grpc as suggestions_service_grpc
from utils.pb.suggestions_service.suggestions_service_pb2 import *
from utils.logger import logger
import grpc
from concurrent import futures

from utils.vector_clock.vector_clock import VectorClock

logs = logger.get_module_logger("SUGGESTIONS")

class BookSuggester(suggestions_service_grpc.SuggestionServiceServicer):
    def Suggest(self, vcm:VectorClockMessage, context):
        logs.info("Received suggestion request")
        order_id = vcm.order_id
        vc_received = vc_msg_2_object(vcm)
        try:
            local_vc = vc_msg_2_object(cache[order_id].vector_clock)
            local_vc.update()
        except:
            logs.error("Error occurred while processing suggestion request")
            det = Determination()
            det.vector_clock.CopyFrom(object_2_vc_msg(vc_received))
            det.suggestion_response.CopyFrom(SuggestionResponse())
            return det 


        local_vc.merge(vc_received)
        request = cache[order_id]

        
        response = suggest_books(request)
        local_vc.update()
        
        response.vector_clock.CopyFrom(object_2_vc_msg(local_vc))

    
        logs.info("Suggested books.")
        return response

    def sendData(self, request:CheckoutRequest, context):
        logs.info("Received data to suggest books")
        order_id = request.vector_clock.order_id
        cache[order_id] = request
        local_vc = vc_msg_2_object(request.vector_clock)
        local_vc.update()

        det = Determination()
        local_vc.update()
        det.vector_clock.CopyFrom(object_2_vc_msg(local_vc))
        det.suggestion_response.CopyFrom(SuggestionResponse())
        
        return det 

def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor())

    suggestions_service_grpc.add_SuggestionServiceServicer_to_server((BookSuggester()), server)

    port = "50053"
    server.add_insecure_port("[::]:" + port)
    server.start()
    logs.info(f"Server started. Listening on port {port}.")
    server.wait_for_termination()

def vc_msg_2_object(vcm: VectorClockMessage):
    logs.info("Converting VectorClockMessage to VectorClock")
    vc = VectorClock(process_id=3, num_processes=4, order_id=vcm.order_id, clocks = vcm.clock)
    logs.info(f"Converted VectorClockMessage to VectorClock: {vc}")
    return vc

def object_2_vc_msg(vc: VectorClock):
    logs.info("Converting VectorClock to VectorClockMessage")
    vcm = VectorClockMessage()
    vcm.process_id = 3 
    vcm.order_id = vc.order_id
    vcm.clock.extend(vc.clock)
    return vcm

def suggest_books(vcm: VectorClockMessage):
    logs.info("Suggesting books")
    response = suggestions_service.Determination()
    book1 = Book(id=1, author="Royal Tenenbaum", name="How to??") 
    book2 = Book(id=2, author="Royal Tenenbaum II", name="To how??") 

    
    response.suggestion_response.book_suggestions.extend([book1, book2]) 

    return response 

if __name__ == '__main__':
    serve()

# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

from utils.pb.book_suggestion import book_suggestion_pb2 as utils_dot_pb_dot_book__suggestion_dot_book__suggestion__pb2


class BookSuggestionServiceStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.SuggestBook = channel.unary_unary(
                '/book_suggestion.BookSuggestionService/SuggestBook',
                request_serializer=utils_dot_pb_dot_book__suggestion_dot_book__suggestion__pb2.BookSuggestionRequest.SerializeToString,
                response_deserializer=utils_dot_pb_dot_book__suggestion_dot_book__suggestion__pb2.BookSuggestionResponse.FromString,
                )


class BookSuggestionServiceServicer(object):
    """Missing associated documentation comment in .proto file."""

    def SuggestBook(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_BookSuggestionServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'SuggestBook': grpc.unary_unary_rpc_method_handler(
                    servicer.SuggestBook,
                    request_deserializer=utils_dot_pb_dot_book__suggestion_dot_book__suggestion__pb2.BookSuggestionRequest.FromString,
                    response_serializer=utils_dot_pb_dot_book__suggestion_dot_book__suggestion__pb2.BookSuggestionResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'book_suggestion.BookSuggestionService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class BookSuggestionService(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def SuggestBook(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/book_suggestion.BookSuggestionService/SuggestBook',
            utils_dot_pb_dot_book__suggestion_dot_book__suggestion__pb2.BookSuggestionRequest.SerializeToString,
            utils_dot_pb_dot_book__suggestion_dot_book__suggestion__pb2.BookSuggestionResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

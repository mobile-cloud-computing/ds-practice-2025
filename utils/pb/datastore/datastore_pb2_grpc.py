# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

import datastore_pb2 as datastore__pb2


class DatastoreServiceStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.HealthCheck = channel.unary_unary(
                '/datastore.DatastoreService/HealthCheck',
                request_serializer=datastore__pb2.HealthCheckRequest.SerializeToString,
                response_deserializer=datastore__pb2.HealthCheckResponse.FromString,
                )
        self.Get = channel.unary_unary(
                '/datastore.DatastoreService/Get',
                request_serializer=datastore__pb2.GetRequest.SerializeToString,
                response_deserializer=datastore__pb2.GetResponse.FromString,
                )
        self.GetBulk = channel.unary_unary(
                '/datastore.DatastoreService/GetBulk',
                request_serializer=datastore__pb2.GetBulkRequest.SerializeToString,
                response_deserializer=datastore__pb2.GetBulkResponse.FromString,
                )
        self.Put = channel.unary_unary(
                '/datastore.DatastoreService/Put',
                request_serializer=datastore__pb2.PutRequest.SerializeToString,
                response_deserializer=datastore__pb2.PutResponse.FromString,
                )
        self.PutBulk = channel.unary_unary(
                '/datastore.DatastoreService/PutBulk',
                request_serializer=datastore__pb2.PutBulkRequest.SerializeToString,
                response_deserializer=datastore__pb2.PutBulkResponse.FromString,
                )
        self.Delete = channel.unary_unary(
                '/datastore.DatastoreService/Delete',
                request_serializer=datastore__pb2.DeleteRequest.SerializeToString,
                response_deserializer=datastore__pb2.DeleteResponse.FromString,
                )
        self.DeleteBulk = channel.unary_unary(
                '/datastore.DatastoreService/DeleteBulk',
                request_serializer=datastore__pb2.DeleteBulkRequest.SerializeToString,
                response_deserializer=datastore__pb2.DeleteBulkResponse.FromString,
                )


class DatastoreServiceServicer(object):
    """Missing associated documentation comment in .proto file."""

    def HealthCheck(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def Get(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def GetBulk(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def Put(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def PutBulk(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def Delete(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def DeleteBulk(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_DatastoreServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'HealthCheck': grpc.unary_unary_rpc_method_handler(
                    servicer.HealthCheck,
                    request_deserializer=datastore__pb2.HealthCheckRequest.FromString,
                    response_serializer=datastore__pb2.HealthCheckResponse.SerializeToString,
            ),
            'Get': grpc.unary_unary_rpc_method_handler(
                    servicer.Get,
                    request_deserializer=datastore__pb2.GetRequest.FromString,
                    response_serializer=datastore__pb2.GetResponse.SerializeToString,
            ),
            'GetBulk': grpc.unary_unary_rpc_method_handler(
                    servicer.GetBulk,
                    request_deserializer=datastore__pb2.GetBulkRequest.FromString,
                    response_serializer=datastore__pb2.GetBulkResponse.SerializeToString,
            ),
            'Put': grpc.unary_unary_rpc_method_handler(
                    servicer.Put,
                    request_deserializer=datastore__pb2.PutRequest.FromString,
                    response_serializer=datastore__pb2.PutResponse.SerializeToString,
            ),
            'PutBulk': grpc.unary_unary_rpc_method_handler(
                    servicer.PutBulk,
                    request_deserializer=datastore__pb2.PutBulkRequest.FromString,
                    response_serializer=datastore__pb2.PutBulkResponse.SerializeToString,
            ),
            'Delete': grpc.unary_unary_rpc_method_handler(
                    servicer.Delete,
                    request_deserializer=datastore__pb2.DeleteRequest.FromString,
                    response_serializer=datastore__pb2.DeleteResponse.SerializeToString,
            ),
            'DeleteBulk': grpc.unary_unary_rpc_method_handler(
                    servicer.DeleteBulk,
                    request_deserializer=datastore__pb2.DeleteBulkRequest.FromString,
                    response_serializer=datastore__pb2.DeleteBulkResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'datastore.DatastoreService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class DatastoreService(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def HealthCheck(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/datastore.DatastoreService/HealthCheck',
            datastore__pb2.HealthCheckRequest.SerializeToString,
            datastore__pb2.HealthCheckResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def Get(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/datastore.DatastoreService/Get',
            datastore__pb2.GetRequest.SerializeToString,
            datastore__pb2.GetResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def GetBulk(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/datastore.DatastoreService/GetBulk',
            datastore__pb2.GetBulkRequest.SerializeToString,
            datastore__pb2.GetBulkResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def Put(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/datastore.DatastoreService/Put',
            datastore__pb2.PutRequest.SerializeToString,
            datastore__pb2.PutResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def PutBulk(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/datastore.DatastoreService/PutBulk',
            datastore__pb2.PutBulkRequest.SerializeToString,
            datastore__pb2.PutBulkResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def Delete(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/datastore.DatastoreService/Delete',
            datastore__pb2.DeleteRequest.SerializeToString,
            datastore__pb2.DeleteResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def DeleteBulk(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/datastore.DatastoreService/DeleteBulk',
            datastore__pb2.DeleteBulkRequest.SerializeToString,
            datastore__pb2.DeleteBulkResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

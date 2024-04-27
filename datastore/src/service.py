import datastore_pb2 as datastore
import datastore_pb2_grpc as datastore_grpc
import grpc


class DataStoreService(datastore_grpc.DatastoreServiceServicer):
    def HealthCheck(self, request, context):
        return datastore.HealthCheckResponse(status="Healthy")

    def Get(self, request, context):
        return datastore.GetResponse()

    def GetBulk(self, request, context):
        response = datastore.GetBulkResponse()
        return response

    def Put(self, request, context):
        return datastore.PutResponse()

    def PutBulk(self, request, context):
        response = datastore.PutBulkResponse()
        return response

    def Delete(self, request, context):
        return datastore.DeleteResponse()

    def DeleteBulk(self, request, context):
        response = datastore.DeleteBulkResponse()
        return response

import uuid

_SERVICE_NAME = f"datastore_{str(uuid.uuid4().node)}"
_INFO_LOG_PATH = f"/app/logs/datastore/{_SERVICE_NAME}.info.log"
_ERROR_LOG_PATH = f"/app/logs/datastore/{_SERVICE_NAME}.error.log"
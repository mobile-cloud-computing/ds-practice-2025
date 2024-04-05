import uuid

_WORKER_NAME = str(uuid.uuid4().node)
_INFO_LOG_PATH = f"/app/logs/order_executor_{_WORKER_NAME}.info.log"
_ERROR_LOG_PATH = f"/app/logs/order_executor_{_WORKER_NAME}.error.log"
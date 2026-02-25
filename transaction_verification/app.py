import sys
import os

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
tv_path = os.path.abspath(os.path.join(FILE, '../utils/pb/transaction_verification'))
sys.path.insert(0, tv_path)

import transaction_verification_pb2 as tv_pb2
import transaction_verification_pb2_grpc as tv_grpc
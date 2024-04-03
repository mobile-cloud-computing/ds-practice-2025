#!/bin/bash

python3 -m grpc_tools.protoc -I. --python_out=. --pyi_out=. --grpc_python_out=. ./pb/transaction_verification/transaction_verification.proto
python3 -m grpc_tools.protoc -I. --python_out=. --pyi_out=. --grpc_python_out=. ./pb/suggestions_service/suggestions_service.proto
python3 -m grpc_tools.protoc -I. --python_out=. --pyi_out=. --grpc_python_out=. ./pb/fraud_detection/fraud_detection.proto
# import utils.pb.transaction_verification.transaction_verification_pb2 as pb_dot_transaction__verification_dot_transaction__verification__pb2
# import utils.pb.suggestions_service.suggestions_service_pb2 as pb_dot_suggestions__service_dot_suggestions__service__pb2
# import utils.pb.fraud_detection.fraud_detection_pb2 as pb_dot_fraud__detection_dot_fraud__detection__pb2

#!/bin/sh

cd utils/pb/fraud_detection
python -m grpc_tools.protoc -I. --python_out=. --pyi_out=. --grpc_python_out=. ./fraud_detection.proto
cd ../transaction_verification
python -m grpc_tools.protoc -I. --python_out=. --pyi_out=. --grpc_python_out=. ./transaction_verification.proto
cd ../suggestions
python -m grpc_tools.protoc -I. --python_out=. --pyi_out=. --grpc_python_out=. ./suggestions.proto
cd ../orchestrator
python -m grpc_tools.protoc -I. --python_out=. --pyi_out=. --grpc_python_out=. ./orchestrator.proto
cd ../../..
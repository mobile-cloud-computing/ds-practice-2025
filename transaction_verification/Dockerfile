# Use an official Python runtime as the base image
FROM python:3.11

# Set the working directory in the container
# Both the utils and src folders will be mounted as volumes, please see docker-compose.yaml
WORKDIR /app

# Copy the requirements file to the working directory
COPY ./transaction_verification/requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set the command to run the application
CMD python -m grpc_tools.protoc -I utils/pb/transaction_verification --python_out=utils/pb/transaction_verification --pyi_out=utils/pb/transaction_verification --grpc_python_out=utils/pb/transaction_verification utils/pb/transaction_verification/transaction_verification.proto && python utils/other/hotreload.py "transaction_verification/src/app.py"
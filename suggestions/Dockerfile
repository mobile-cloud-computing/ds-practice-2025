# Use an official Python runtime as the base image
FROM python:3.11

# Set the working directory in the container
# Both the utils and src folders will be mounted as volumes, please see docker-compose.yaml
WORKDIR /app

# Copy the requirements file to the working directory
COPY ./suggestions/requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set the command to run the application
CMD python -m grpc_tools.protoc -I utils/pb/suggestions --python_out=utils/pb/suggestions --pyi_out=utils/pb/suggestions --grpc_python_out=utils/pb/suggestions utils/pb/suggestions/suggestions.proto && python utils/other/hotreload.py "suggestions/src/app.py"

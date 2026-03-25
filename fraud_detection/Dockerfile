# Use an official Python runtime as the base image
FROM python:3.11

# Set the working directory in the container
# Both the utils and src folders will be mounted as volumes, please see docker-compose.yaml
WORKDIR /app

# Copy the requirements file to the working directory
COPY ./fraud_detection/requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Ensure Python can import from /app (project root)
ENV PYTHONPATH=/app

# Set the command to run the application
CMD python utils/other/hotreload.py "fraud_detection/src/app.py"
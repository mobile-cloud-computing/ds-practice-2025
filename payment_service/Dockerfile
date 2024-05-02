# Use an official Python runtime as the base image
FROM python:3.11

# Set the working directory in the container
# Both the utils and src folders will be mounted as volumes, please see docker-compose.yaml
WORKDIR /app

# Copy the requirements file to the working directory
COPY ./payment_service/requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
ADD ./payment_service/src payment_service/src
# Set the command to run the application
CMD python3 "payment_service/src/app.py"

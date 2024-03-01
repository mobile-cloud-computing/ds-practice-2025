# Use an official Python runtime as the base image
FROM --platform=$BUILDPLATFORM python:3.11

# Set the working directory in the container
# Both the utils and src folders will be mounted as volumes, please see docker-compose.yaml
WORKDIR /app

# Copy the requirements file to the working directory
COPY ./orchestrator/requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
# Install reloadium for hot reloading
# This allows us to make changes to the code without having to rebuild the container
RUN pip install reloadium

# Set the command to run the container
CMD reloadium run "orchestrator/src/app.py"

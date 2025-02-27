FROM python:3.11

WORKDIR /app

# Copy the requirements file
COPY ./transaction_verification/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Start the transaction verification service
CMD python utils/other/hotreload.py "transaction_verification/src/app.py"

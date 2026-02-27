FROM python:3.11-slim

WORKDIR /app

COPY ./transaction_verification/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

CMD python utils/other/hotreload.py "transaction_verification/src/app.py"

# order_executor/Dockerfile
FROM python:3.11
WORKDIR /app

COPY ./order_executor/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ./order_executor/src /app/order_executor/src
COPY ./utils /app/utils

CMD ["python", "order_executor/src/debug.py"]

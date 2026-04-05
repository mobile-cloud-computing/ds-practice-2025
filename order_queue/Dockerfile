FROM python:3.11
WORKDIR /app
COPY ./order_queue/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
CMD python utils/other/hotreload.py "order_queue/src/app.py"
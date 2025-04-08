
FROM python:3.11
WORKDIR /app

COPY ./fraud_detection/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY fraud_detection /app/fraud_detection

CMD python utils/other/hotreload.py "fraud_detection/src/app.py"

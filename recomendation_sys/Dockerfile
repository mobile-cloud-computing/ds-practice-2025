FROM python:3.11
WORKDIR /app
COPY ./recomendation_sys/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
CMD python utils/other/hotreload.py "recomendation_sys/src/app.py"

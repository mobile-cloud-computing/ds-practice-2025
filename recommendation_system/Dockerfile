FROM python:3.11
WORKDIR /app
COPY ./recommendation_system/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
CMD python utils/other/hotreload.py "recommendation_system/src/app.py"

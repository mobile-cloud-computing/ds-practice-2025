FROM python:3.11

WORKDIR /app

COPY ./suggestions/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

CMD python utils/other/hotreload.py "suggestions/src/app.py"
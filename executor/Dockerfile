FROM python:3.11-slim

WORKDIR /app

COPY ./executor/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

CMD sh -c "python ${PYTHONFILE}"
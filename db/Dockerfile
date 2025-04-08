FROM docker.io/postgres:16

RUN apt-get update && apt-get install -y \
  git \
  build-essential \
  postgresql-server-dev-$PG_MAJOR \
  && rm -rf /var/lib/apt/lists/*

RUN git clone --branch v0.7.0 https://github.com/pgvector/pgvector.git \
  && cd pgvector \
  && make \
  && make install

COPY ./db/init-extensions.sql /docker-entrypoint-initdb.d/

FROM python:3.14

RUN python3 --version && which python3 && ls -la /usr/local/bin/python3*

WORKDIR /test

RUN pip install -U pip setuptools
RUN pip install poetry

COPY ../pyproject.toml ../poetry.lock ./

RUN python3 -m poetry install
RUN apt-get update \
    && apt-get install postgresql -y \
    && apt-get install postgresql-contrib -y \
    && apt-get install postgresql-client -y

COPY .. .
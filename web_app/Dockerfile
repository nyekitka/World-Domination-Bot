FROM python:3.14

WORKDIR /web_app

RUN pip install -U pip setuptools
RUN pip install poetry

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

RUN apt-get update \
    && apt-get install postgresql -y \
    && apt-get install postgresql-contrib -y \
    && apt-get install postgresql-client -y

COPY database ./database
COPY game ./game
COPY web_app/ ./
COPY presets ./presets

COPY web_app/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

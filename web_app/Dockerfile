FROM python:3.14

WORKDIR /web_app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false

RUN pip install -U pip setuptools
RUN pip install poetry

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

RUN apt-get update \
    && apt-get install postgresql -y \
    && apt-get install postgresql-contrib -y \
    && apt-get install postgresql-client -y

COPY . .

RUN chmod +x web_app/entrypoint.sh

ENTRYPOINT ["/bin/sh", "web_app/entrypoint.sh"]

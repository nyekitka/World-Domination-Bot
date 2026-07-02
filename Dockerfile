FROM python:3.13

WORKDIR /app

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

CMD ["python3", "main.py"]
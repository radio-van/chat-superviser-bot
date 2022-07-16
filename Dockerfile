FROM python:3.10

ENV PYTHONUNBUFFERED=1

RUN pip install --ignore-installed --timeout 120 poetry

COPY poetry.lock pyproject.toml /bot/

WORKDIR /bot/

RUN poetry config virtualenvs.create false

RUN poetry install --no-dev --no-interaction

COPY ./src/ /bot/

ENTRYPOINT poetry run python main.py

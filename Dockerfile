FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.4.0 /uv /bin/uv

WORKDIR /app

ADD uv.lock /app/uv.lock
ADD pyproject.toml /app/pyproject.toml

ENV UV_COMPILE_BYTECODE=1
RUN uv sync --frozen --no-install-project

ADD . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

CMD ["uv", "run", "python", "lessons_reporter_bot/main.py"]
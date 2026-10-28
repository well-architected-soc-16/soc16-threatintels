# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

# Target runtime: bersih, tanpa dependensi dev (untuk GHCR / produksi).
FROM base AS runtime
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
COPY scripts ./scripts
USER app
EXPOSE 8000
CMD ["sh", "scripts/entrypoint.sh"]

# Target dev: runtime + dependensi dev + tests (dipakai docker-compose).
FROM base AS dev
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements-dev.txt
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
COPY scripts ./scripts
COPY tests ./tests
USER app
EXPOSE 8000
CMD ["sh", "scripts/entrypoint.sh"]

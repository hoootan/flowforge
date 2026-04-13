# syntax=docker/dockerfile:1

# ================================
# Build Stage
# ================================
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Virtual environment for clean isolation
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade "pip>=25.3" "wheel>=0.46.2" setuptools

COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir ".[auth]"

# ================================
# Runtime Stage
# ================================
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.source="https://github.com/flowforge/flowforge"
LABEL org.opencontainers.image.description="FlowForge Server"

# Runtime libraries and security updates
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    libjpeg62-turbo \
    zlib1g \
    libpng16-16 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN groupadd --gid 1000 flowforge && \
    useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash flowforge

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=flowforge:flowforge src/ src/
COPY --chown=flowforge:flowforge migrations/ /app/migrations/

# Create media directory for generated images (writable by flowforge user)
RUN mkdir -p /app/media/generated && chown -R flowforge:flowforge /app/media

ENV PATH="/opt/venv/bin:$PATH"
ENV FLOWFORGE_MIGRATIONS_DIR=/app/migrations
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

USER flowforge

EXPOSE 8000

# Healthchecks are intentionally defined per-service in docker-compose.yml,
# not baked into the image. This image is reused for `server`, `runner`, and
# `executor` services — only `server` exposes the HTTP /api/v1/health endpoint,
# while workers run as background processes with no listener. Defining an
# HTTP healthcheck here causes worker containers to be marked unhealthy
# whenever a downstream compose file forgets to override it.

CMD ["uvicorn", "flowforge_server.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

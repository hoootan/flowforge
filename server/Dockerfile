FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck and image libraries for Pillow (QR code generation)
RUN apt-get update && apt-get install -y \
    curl \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ src/
COPY migrations/ /app/migrations/

# Install dependencies (including auth extras for JWT and bcrypt)
RUN pip install --no-cache-dir ".[auth]"

# Set migrations directory for Docker
ENV FLOWFORGE_MIGRATIONS_DIR=/app/migrations

# Expose port
EXPOSE 8000

# Run server
CMD ["uvicorn", "flowforge_server.main:app", "--host", "0.0.0.0", "--port", "8000"]

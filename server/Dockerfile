FROM python:3.11-slim

# Create non-root user for security
RUN groupadd --gid 1000 flowforge && \
    useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash flowforge

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

# Change ownership of app directory to non-root user
RUN chown -R flowforge:flowforge /app

# Set migrations directory for Docker
ENV FLOWFORGE_MIGRATIONS_DIR=/app/migrations

# Switch to non-root user
USER flowforge

# Expose port
EXPOSE 8000

# Run server
CMD ["uvicorn", "flowforge_server.main:app", "--host", "0.0.0.0", "--port", "8000"]

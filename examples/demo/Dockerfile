FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy SDK and install first (for layer caching)
COPY packages/flowforge-sdk /sdk
RUN pip install --no-cache-dir /sdk[ai,fastapi]

# Copy demo application
COPY examples/demo /app

# Set Python path
ENV PYTHONPATH=/app:/app/src
ENV PYTHONUNBUFFERED=1

# Default port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the worker
CMD ["python", "src/app.py"]

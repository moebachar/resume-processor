# Dockerfile for Resume Processing Microservice
# JSON-only API (no PDF generation)
# Optimized for high concurrency and multiple simultaneous users

FROM python:3.13-slim

WORKDIR /app

# Copy requirements first (for Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (Cloud Run uses PORT env var, default 8080)
EXPOSE 8080

# Environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV WORKERS=4

# Health check (optional, but good for load balancing)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health', timeout=5)"

# Run with uvicorn
# CRITICAL FOR CONCURRENCY:
# - Multiple workers for parallel request handling
# - High timeout for long-running OpenAI calls
# - Proper host binding for Cloud Run
CMD exec uvicorn api:app \
    --host 0.0.0.0 \
    --port ${PORT} \
    --workers ${WORKERS} \
    --timeout-keep-alive 300 \
    --limit-concurrency 1000 \
    --backlog 2048

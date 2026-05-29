# Dockerfile for Fusion Engine Service
FROM python:3.11-slim AS builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==1.7.0

# Configure Poetry
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Copy project files
WORKDIR /app
COPY pyproject.toml poetry.lock ./

# Install dependencies (without optional GPU support)
RUN poetry install --only main --no-root

# Copy source code
COPY . .

# Install the project
RUN poetry install --no-dev

# Runtime stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Create non-root user
RUN groupadd -r ids && useradd -r -g ids ids

# Create directories
RUN mkdir -p /app /var/log && \
    chown -R ids:ids /app /var/log

# Switch to non-root user
USER ids

# Set working directory
WORKDIR /app

# Copy source code
COPY --chown=ids:ids . .

# Expose API port
EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Run the service
CMD ["uvicorn", "fusion_engine.main:main", "--host", "0.0.0.0", "--port", "8003"]
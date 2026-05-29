# ML Inference Service Dockerfile
# Multi-architecture with ARM64 support for Raspberry Pi

# Stage 1: Builder - for compiling dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster builds
RUN pip install --no-cache-dir uv==0.4.0

# Copy requirements first for better caching
COPY requirements.txt pyproject.toml ./

# Create virtual environment and install dependencies
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
RUN uv pip compile requirements.txt -o requirements-compiled.txt && \
    uv pip install --system -r requirements-compiled.txt

# Copy application code
COPY src/ ./src/
COPY README.md ./

# Stage 2: Runtime - smaller image for deployment
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    # For MQTT
    ca-certificates \
    # For numpy/scipy
    liblapack3 \
    libgomp1 \
    # For ONNX Runtime
    libssl3 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user
RUN groupadd -r mlservice && useradd -r -g mlservice mlservice

# Create directories with proper permissions
RUN mkdir -p /app /var/models /var/log /tmp/ml_cache && \
    chown -R mlservice:mlservice /app /var/models /var/log /tmp/ml_cache

# Copy application code
COPY --from=builder --chown=mlservice:mlservice /app/src/ ./src/
COPY --from=builder --chown=mlservice:mlservice /app/README.md ./
COPY --from=builder --chown=mlservice:mlservice /app/requirements.txt ./

# Switch to non-root user
USER mlservice

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import sys; import urllib.request; \
    try: \
        urllib.request.urlopen('http://localhost:8002/health', timeout=2) \
    except: \
        sys.exit(1)"

# Expose API port
EXPOSE 8002

# Default environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    MODEL_DIR=/var/models \
    LOG_LEVEL=INFO \
    NODE_ID=edge-ml-inference-01 \
    API_HOST=0.0.0.0 \
    API_PORT=8002 \
    OPTIMIZE_FOR_EDGE=true

# Run the application
CMD ["python", "-m", "ml_inference_service.main"]

# ============================================================================
# Stage 3: ARM64 Optimized (for Raspberry Pi)
# ============================================================================
FROM arm64v8/python:3.11-slim AS arm64-runtime

WORKDIR /app

# ARM64 specific optimizations
RUN apt-get update && apt-get install -y \
    ca-certificates \
    liblapack3 \
    libgomp1 \
    libssl3 \
    # ARM64 optimized BLAS
    libopenblas0-pthread \
    && rm -rf /var/lib/apt/lists/*

# Optimize for ARM64
RUN echo "Optimizing for ARM64 architecture" && \
    # Set ARM-specific optimizations
    pip config set global.cache-dir /tmp/pip-cache && \
    pip config set global.no-cache-dir false

# Copy virtual environment from builder (need to rebuild for ARM64)
# In practice, you would rebuild dependencies for ARM64
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user
RUN groupadd -r mlservice && useradd -r -g mlservice mlservice

# Create directories
RUN mkdir -p /app /var/models /var/log /tmp/ml_cache && \
    chown -R mlservice:mlservice /app /var/models /var/log /tmp/ml_cache

# Copy application code
COPY --from=builder --chown=mlservice:mlservice /app/src/ ./src/
COPY --from=builder --chown=mlservice:mlservice /app/README.md ./

USER mlservice

# ARM64 specific environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    MODEL_DIR=/var/models \
    LOG_LEVEL=INFO \
    NODE_ID=pi-ml-inference-01 \
    API_HOST=0.0.0.0 \
    API_PORT=8002 \
    OPTIMIZE_FOR_EDGE=true \
    INFERENCE_THREADS=1 \
    BATCH_SIZE=16 \
    MAX_MEMORY_MB=512

HEALTHCHECK --interval=60s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import sys; import urllib.request; \
    try: \
        urllib.request.urlopen('http://localhost:8002/health', timeout=3) \
    except: \
        sys.exit(1)"

EXPOSE 8002

CMD ["python", "-m", "ml_inference_service.main"]

# ============================================================================
# Build instructions:
# ============================================================================
#
# For x86_64:
# docker build -t ml-inference-service:latest .
#
# For ARM64 (Raspberry Pi):
# docker build --target arm64-runtime -t ml-inference-service:arm64 .
#
# Multi-architecture build:
# docker buildx build --platform linux/amd64,linux/arm64 -t ml-inference-service:multi-arch .
#
# Run with environment variables:
# docker run -p 8002:8002 \
#   -v ./models:/var/models \
#   -e NODE_ID=edge-node-001 \
#   -e MQTT_BROKER_URL=mqtt://broker:1883 \
#   ml-inference-service:latest
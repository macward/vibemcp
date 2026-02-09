# Multi-stage build for vibeMCP
# Stage 1: Build wheel with uv
FROM python:3.11-slim AS builder

WORKDIR /app

# Install uv for faster dependency resolution
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml .
COPY src/ src/

# Build wheel
RUN uv pip install --system build && \
    python -m build --wheel --outdir /dist

# Stage 2: Runtime image
FROM python:3.11-slim

WORKDIR /app

# Install uv for faster package installation
RUN pip install --no-cache-dir uv

# Copy wheel from builder
COPY --from=builder /dist/*.whl /tmp/

# Install the wheel
RUN uv pip install --system /tmp/*.whl && \
    rm /tmp/*.whl

# Create non-root user
RUN useradd -r -m -s /bin/bash vibemcp

# Create data directory
RUN mkdir -p /data && chown vibemcp:vibemcp /data

# Switch to non-root user
USER vibemcp

# Environment defaults
ENV VIBE_ROOT=/data \
    VIBE_DB=/data/index.db \
    VIBE_PORT=8288

# Expose port
EXPOSE 8288

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8288/')" || exit 1

# Run server
CMD ["vibe-mcp"]

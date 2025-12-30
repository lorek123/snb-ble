# Multi-stage Dockerfile for storzandbickel-ble

# Build stage
FROM python:3.14.2-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files and README (needed for package metadata)
COPY pyproject.toml README.md ./

# Copy source code (needed for editable install)
COPY src/ ./src/

# Install dependencies using UV
RUN uv pip install --system -e ".[dev]"

# Production stage
FROM python:3.14.2-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ ./src/
COPY README.md LICENSE ./

# Set Python path
ENV PYTHONPATH=/app/src

# Default command
CMD ["python", "-c", "import storzandbickel_ble; print('storzandbickel-ble library loaded')"]


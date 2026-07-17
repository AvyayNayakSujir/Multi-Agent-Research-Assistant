# Use a lightweight python image for building dependencies
FROM python:3.14-slim AS builder

WORKDIR /multi-agent-research-assistant

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/

# Configure uv: virtual environment location and optimizations
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install dependencies using uv sync
# By mounting the cache and binding pyproject.toml/uv.lock, we avoid copying unnecessary files and keep builds fast
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    /uv/bin/uv sync --frozen --no-dev


# Final production stage
FROM python:3.14-slim

WORKDIR /multi-agent-research-assistant

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv
COPY . .

# Set environment path to find dependencies in the virtual environment
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Start server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

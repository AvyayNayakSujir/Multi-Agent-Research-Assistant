# Use a lightweight python image for building dependencies
FROM python:3.14-slim AS builder

WORKDIR /multi-agent-research-assistant

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/

# Create a virtual environment
RUN /uv/bin/uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies using uv
COPY requirements.txt .
RUN /uv/bin/uv pip install --no-cache -r requirements.txt

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

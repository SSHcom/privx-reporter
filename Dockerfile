FROM python:3.14-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Set PATH to include uv's virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Use copy mode to avoid hardlink warnings when venv is on a different filesystem
ENV UV_LINK_MODE=copy
ENV PYTHONDONTWRITEBYTECODE=1
ENV UV_CACHE_DIR=/tmp/uv-cache

# Default command
CMD ["uv", "run", "sync-server"]


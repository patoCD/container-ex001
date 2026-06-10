#
# dockerfile
#

FROM python:3.14-slim

# System dependencies (safe baseline for pandas/pyarrow)
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy dependency metadata first (for caching)
COPY pyproject.toml uv.lock ./

# Install ONLY production dependencies (exclude dev group)
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Default command (adjust to your entrypoint)
# CMD ["uv", "run", "python", "pipeline/pipeline.py"]
ENTRYPOINT ["uv", "run", "python", "pipeline/pipeline.py"]
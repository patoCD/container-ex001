#
# dockerfile
#

# ---- Builder stage ----
FROM python:3.14-slim AS builder

# Install build tools only in the builder stage
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*
    
# Install uv CLI
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy dependency metadata first for caching
COPY pyproject.toml uv.lock ./

# Install ONLY production dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# ---- Final stage (runtime) ----
FROM python:3.14-slim

WORKDIR /app

# Copy only the installed packages and app code from the builder
COPY --from=builder /root/.local /root/.local
COPY --from=builder /app /app

# Make uv CLI available
ENV PATH="/root/.local/bin:$PATH"

# Run your pipeline
ENTRYPOINT ["uv", "run", "python", "pipeline/pipeline.py"]
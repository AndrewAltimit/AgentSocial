# Stage 1: Builder stage
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY config/python/requirements.txt /build/requirements.txt
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY packages/bulletin_board /app/packages/bulletin_board
COPY packages/bulletin_board/pyproject.toml /app/packages/bulletin_board/pyproject.toml

# Install the bulletin board package
RUN pip install --user -e /app/packages/bulletin_board

# Create non-root user and set permissions
RUN useradd -m -u 1000 bulletin && \
    chown -R bulletin:bulletin /app && \
    # Create .git directory for version detection
    mkdir -p /app/.git && \
    chown -R bulletin:bulletin /app/.git

USER bulletin

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH=/home/bulletin/.local/bin:$PATH

EXPOSE 8080

# Default command
CMD ["python", "-m", "packages.bulletin_board.app.app"]

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
# Including matplotlib dependencies for analytics visualizations
RUN apt-get update && apt-get install -y \
    postgresql-client \
    git \
    libpng-dev \
    libfreetype6-dev \
    pkg-config \
    python3-tk \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user first
RUN useradd -m -u 1000 bulletin

# Copy Python dependencies from builder to bulletin user's home
COPY --from=builder /root/.local /home/bulletin/.local

# Fix ownership of dependencies
RUN chown -R bulletin:bulletin /home/bulletin/.local

# Copy application code
COPY packages/bulletin_board /app/packages/bulletin_board

# Set PYTHONPATH instead of installing as editable package
ENV PYTHONPATH=/app:$PYTHONPATH

# Set permissions for app directory
RUN chown -R bulletin:bulletin /app && \
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

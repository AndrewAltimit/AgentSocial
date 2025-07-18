FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements (will be created later)
COPY bulletin_board/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY bulletin_board /app/bulletin_board

# Create non-root user
RUN useradd -m -u 1000 bulletin && chown -R bulletin:bulletin /app
USER bulletin

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8080

# Default command
CMD ["python", "-m", "bulletin_board.app.app"]
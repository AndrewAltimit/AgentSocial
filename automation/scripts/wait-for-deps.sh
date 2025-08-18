#!/bin/bash
# Wait for bulletin board dependencies to be healthy before starting agent services
# This provides a more robust alternative to simple sleep commands

set -e

# Configuration
MAX_RETRIES=${MAX_RETRIES:-30}
RETRY_INTERVAL=${RETRY_INTERVAL:-2}
DATABASE_URL=${DATABASE_URL:-postgresql://bulletin:bulletin@bulletin-db:5432/bulletin_board}
API_URL=${BULLETIN_BOARD_API_URL:-http://bulletin-web:8080}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Function to check PostgreSQL connectivity
check_postgres() {
    # Extract connection details from DATABASE_URL
    # Expected format: postgresql://user:pass@host:port/database
    # Note: This regex assumes the URL includes username, password, host, port, and database name
    # If your DATABASE_URL format differs (e.g., no password, different scheme), this script will need modification
    if [[ $DATABASE_URL =~ postgresql://([^:]+):([^@]+)@([^:]+):([^/]+)/(.+) ]]; then
        DB_USER="${BASH_REMATCH[1]}"
        DB_PASS="${BASH_REMATCH[2]}"
        DB_HOST="${BASH_REMATCH[3]}"
        DB_PORT="${BASH_REMATCH[4]}"
        DB_NAME="${BASH_REMATCH[5]}"

        PGPASSWORD=$DB_PASS pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" > /dev/null 2>&1
        return $?
    else
        error "Invalid DATABASE_URL format"
        return 1
    fi
}

# Function to check API health
check_api() {
    # Use curl to check the API health endpoint
    curl -sf "${API_URL}/api/health" > /dev/null 2>&1
    return $?
}

# Wait for PostgreSQL
log "Waiting for PostgreSQL database..."
retry_count=0
while [ $retry_count -lt "$MAX_RETRIES" ]; do
    if check_postgres; then
        log "PostgreSQL is ready!"
        break
    fi

    retry_count=$((retry_count + 1))
    if [ $retry_count -eq "$MAX_RETRIES" ]; then
        error "PostgreSQL failed to become ready after $MAX_RETRIES retries"
        exit 1
    fi

    warning "PostgreSQL not ready (attempt $retry_count/$MAX_RETRIES), waiting ${RETRY_INTERVAL}s..."
    sleep "$RETRY_INTERVAL"
done

# Wait for API
log "Waiting for Bulletin Board API..."
retry_count=0
while [ $retry_count -lt "$MAX_RETRIES" ]; do
    if check_api; then
        log "Bulletin Board API is ready!"
        break
    fi

    retry_count=$((retry_count + 1))
    if [ $retry_count -eq "$MAX_RETRIES" ]; then
        error "API failed to become ready after $MAX_RETRIES retries"
        exit 1
    fi

    warning "API not ready (attempt $retry_count/$MAX_RETRIES), waiting ${RETRY_INTERVAL}s..."
    sleep "$RETRY_INTERVAL"
done

# All dependencies are ready
log "All dependencies are healthy - starting agent service"

# Execute the provided command
exec "$@"

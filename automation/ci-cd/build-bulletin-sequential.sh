#!/bin/bash
# Sequential build script for bulletin board services
# Avoids docker buildx panic when building multiple images in parallel

set -e

echo "🔨 Building bulletin board services sequentially..."

# Build each service one at a time to avoid buildx race conditions
services=("bulletin-db" "bulletin-web" "bulletin-collector" "bulletin-agent-runner" "bulletin-memory-runner")

for service in "${services[@]}"; do
    echo "Building $service..."
    if docker-compose build --no-cache "$service"; then
        echo "✅ $service built successfully"
    else
        echo "❌ Failed to build $service"
        exit 1
    fi
done

echo "✅ All bulletin board services built successfully"

#!/bin/bash
# Sequential build script for bulletin board services
# Avoids docker buildx panic when building multiple images in parallel

set -e

echo "🔨 Building bulletin board services sequentially..."

# Build each service one at a time to avoid buildx race conditions
services=("bulletin-db" "bulletin-web" "bulletin-collector" "bulletin-agent-runner" "bulletin-memory-runner")

for service in "${services[@]}"; do
    echo "Building $service..."
    # Use --progress plain to avoid docker buildx progress reporting panic
    # See: https://github.com/docker/buildx/issues/1309
    export DOCKER_BUILDKIT=1
    if docker-compose --progress plain build --no-cache "$service"; then
        echo "✅ $service built successfully"
        # Small delay to ensure resources are freed between builds
        sleep 2
    else
        echo "❌ Failed to build $service"
        exit 1
    fi
done

echo "✅ All bulletin board services built successfully"

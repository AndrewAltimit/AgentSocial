#!/bin/bash

# Pre-commit hook script for running Selenium UI tests
# Only runs smoke tests to keep commit times reasonable

set -eu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# PROJECT_ROOT is referenced in docker-compose commands which use paths relative to the compose file
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
export PROJECT_ROOT

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Running UI smoke tests...${NC}"

# Function to check if services are running
check_services() {
    if docker ps | grep -q bulletin-web && docker ps | grep -q bulletin-db; then
        return 0
    else
        return 1
    fi
}

# Function to check if Docker is available
check_docker() {
    if command -v docker &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Note: File filtering is handled by .pre-commit-config.yaml
# This script only runs when relevant files have changed

# Check if we're in CI environment
if [ "${CI:-}" == "true" ] || [ -n "${GITHUB_ACTIONS:-}" ]; then
    echo -e "${YELLOW}Skipping UI tests in CI environment${NC}"
    exit 0
fi

# Check if services are running
if ! check_services; then
    echo -e "${YELLOW}Bulletin board services not running.${NC}"
    echo -e "${YELLOW}Skipping UI tests (run ./test-ui.sh to start services)${NC}"
    exit 0
fi

# Check if Docker is available
if ! check_docker; then
    echo -e "${RED}Docker is required to run tests${NC}"
    echo -e "${YELLOW}Tests run in containers to ensure consistency${NC}"
    exit 1
fi

# Ensure selenium-tests container image is built
if ! docker images | grep -q selenium-tests; then
    echo -e "${YELLOW}Building selenium-tests container...${NC}"
    docker-compose build selenium-tests
fi

# Run only smoke tests (fast subset)
echo -e "${BLUE}Running smoke tests...${NC}"

# Set timeout for tests (30 seconds max) and run in container
# Using --foreground for better signal handling in complex scenarios
timeout --foreground 30 docker-compose run --rm selenium-tests \
    python -m pytest \
    "/tests/ui/test_critical_functionality.py::TestSmokeTests" \
    -v \
    --tb=short \
    -x || TEST_RESULT=$?

if [ "${TEST_RESULT:-0}" -eq 0 ]; then
    echo -e "${GREEN}✓ UI smoke tests passed${NC}"
    exit 0
elif [ "${TEST_RESULT:-0}" -eq 124 ]; then
    echo -e "${RED}✗ UI tests timed out${NC}"
    echo -e "${YELLOW}Tests took too long. Please check manually.${NC}"
    exit 1
else
    echo -e "${RED}✗ UI smoke tests failed${NC}"
    echo -e "${YELLOW}Fix the issues or run with --no-verify to skip${NC}"
    exit 1
fi

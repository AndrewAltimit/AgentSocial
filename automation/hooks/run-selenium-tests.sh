#!/bin/bash

# Pre-commit hook script for running Selenium UI tests
# Only runs smoke tests to keep commit times reasonable

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Running UI smoke tests...${NC}"

# Function to check if services are running
check_services() {
    if docker ps 2>/dev/null | grep -q bulletin-web && docker ps 2>/dev/null | grep -q bulletin-db; then
        return 0
    else
        return 1
    fi
}

# Function to check if ChromeDriver is available
check_chromedriver() {
    if command -v chromedriver &> /dev/null || [ -f "/usr/local/bin/chromedriver" ]; then
        return 0
    else
        return 1
    fi
}

# Skip if no Python files changed (optimization)
if ! git diff --cached --name-only --diff-filter=ACM | grep -q '\.py$\|\.js$\|\.html$'; then
    echo -e "${GREEN}No Python/JS/HTML files changed, skipping UI tests${NC}"
    exit 0
fi

# Check if we're in CI environment
if [ "${CI}" == "true" ] || [ -n "${GITHUB_ACTIONS}" ]; then
    echo -e "${YELLOW}Skipping UI tests in CI environment${NC}"
    exit 0
fi

# Check if services are running
if ! check_services; then
    echo -e "${YELLOW}Bulletin board services not running.${NC}"
    echo -e "${YELLOW}Skipping UI tests (run ./test-ui.sh to start services)${NC}"
    exit 0
fi

# Check if ChromeDriver is available
if ! check_chromedriver; then
    echo -e "${YELLOW}ChromeDriver not found, skipping UI tests${NC}"
    echo -e "${YELLOW}Install with: apt-get install chromium-chromedriver${NC}"
    exit 0
fi

# Check if Selenium is installed
if ! python3 -c "import selenium" 2>/dev/null; then
    echo -e "${YELLOW}Selenium not installed, skipping UI tests${NC}"
    echo -e "${YELLOW}Install with: pip install selenium pytest${NC}"
    exit 0
fi

# Run only smoke tests (fast subset)
echo -e "${BLUE}Running smoke tests...${NC}"

# Set timeout for tests (30 seconds max)
timeout 30 python3 -m pytest \
    "$PROJECT_ROOT/tests/ui/test_critical_functionality.py::TestSmokeTests" \
    -v \
    --tb=short \
    -x \
    2>/dev/null || TEST_RESULT=$?

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

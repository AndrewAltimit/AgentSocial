#!/bin/bash

# UI Testing Script for AgentSocial Bulletin Board
# Runs Selenium tests against the local instance

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}     AgentSocial UI Testing Suite${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

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

# Step 1: Check prerequisites
echo -e "${YELLOW}Step 1: Checking prerequisites...${NC}"

if ! check_docker; then
    echo -e "${RED}Docker not found!${NC}"
    echo "Docker is required to run tests in containers"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

echo -e "${GREEN}✓ Docker found${NC}"

# Build selenium-tests container if needed
if ! docker images | grep -q selenium-tests; then
    echo -e "${YELLOW}Building selenium-tests container...${NC}"
    docker-compose build selenium-tests
fi

echo -e "${GREEN}✓ Selenium test container ready${NC}"

# Step 2: Check if services are running
echo -e "${YELLOW}Step 2: Checking if bulletin board is running...${NC}"

if ! check_services; then
    echo -e "${YELLOW}Services not running. Starting with mock data...${NC}"
    "$PROJECT_ROOT/automation/scripts/test-with-mock-data.sh"

    # Wait for services to be ready
    sleep 5
fi

echo -e "${GREEN}✓ Services are running${NC}"

# Step 3: Dependencies are handled in container
echo -e "${YELLOW}Step 3: Container dependencies...${NC}"
echo -e "${GREEN}✓ All dependencies are managed in the selenium-tests container${NC}"

# Step 4: Run the tests
echo -e "${YELLOW}Step 4: Running UI tests...${NC}"
echo ""

# Create test results directory
RESULTS_DIR="$PROJECT_ROOT/test-results"
mkdir -p "$RESULTS_DIR"

# Run tests with different options based on arguments
if [[ "$1" == "--headless" ]] || [[ -z "$DISPLAY" ]]; then
    echo -e "${BLUE}Running in headless mode...${NC}"
else
    echo -e "${BLUE}Running with browser window...${NC}"
fi

# Set test report filename with timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
REPORT_FILE="$RESULTS_DIR/ui_test_report_${TIMESTAMP}.html"

# Run the Selenium tests in container
echo -e "${BLUE}Executing test suite in container...${NC}"
echo ""

# Mount the report directory and run tests
docker-compose run --rm \
    -v "$RESULTS_DIR:/test-results" \
    selenium-tests \
    python -m pytest \
    "/tests/ui/test_bulletin_board_ui.py" \
    -v \
    --html="/test-results/ui_test_report_${TIMESTAMP}.html" \
    --self-contained-html \
    --tb=short \
    --timeout=60 \
    -x \
    || TEST_EXIT_CODE=$?

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

# Step 5: Display results
if [[ ${TEST_EXIT_CODE:-0} -eq 0 ]]; then
    echo -e "${GREEN}✓ All UI tests passed!${NC}"
    echo ""
    echo -e "Test report saved to: ${REPORT_FILE}"
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo ""
    echo -e "Test report saved to: ${REPORT_FILE}"
    echo ""
    echo -e "${YELLOW}Troubleshooting tips:${NC}"
    echo "  1. Check if the application is accessible at http://localhost:8080"
    echo "  2. Clear browser cache with: Ctrl+Shift+R (or Cmd+Shift+R on Mac)"
    echo "  3. Check logs: ./automation/scripts/bulletin-board.sh logs"
    echo "  4. Restart services: ./automation/scripts/bulletin-board.sh stop && ./automation/scripts/bulletin-board.sh start"
fi

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

# Optional: Open report in browser
if [[ "$2" == "--show-report" ]] && [[ -f "$REPORT_FILE" ]]; then
    echo ""
    echo -e "${YELLOW}Opening test report in browser...${NC}"
    if command -v xdg-open &> /dev/null; then
        xdg-open "$REPORT_FILE"
    elif command -v open &> /dev/null; then
        open "$REPORT_FILE"
    fi
fi

exit "${TEST_EXIT_CODE:-0}"

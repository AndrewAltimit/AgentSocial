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

# Function to check if ChromeDriver is installed
check_chromedriver() {
    if command -v chromedriver &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to install dependencies
install_dependencies() {
    echo -e "${YELLOW}Installing test dependencies...${NC}"
    pip install --user selenium pytest pytest-html pytest-timeout
}

# Step 1: Check prerequisites
echo -e "${YELLOW}Step 1: Checking prerequisites...${NC}"

if ! check_chromedriver; then
    echo -e "${RED}ChromeDriver not found!${NC}"
    echo "Please install ChromeDriver:"
    echo "  Ubuntu/Debian: sudo apt-get install chromium-chromedriver"
    echo "  Mac: brew install chromedriver"
    echo "  Or download from: https://chromedriver.chromium.org/"
    exit 1
fi

# Check if Chrome/Chromium is installed
if ! command -v google-chrome &> /dev/null && ! command -v chromium-browser &> /dev/null; then
    echo -e "${RED}Chrome/Chromium browser not found!${NC}"
    echo "Please install Chrome or Chromium browser"
    exit 1
fi

echo -e "${GREEN}✓ ChromeDriver and browser found${NC}"

# Step 2: Check if services are running
echo -e "${YELLOW}Step 2: Checking if bulletin board is running...${NC}"

if ! check_services; then
    echo -e "${YELLOW}Services not running. Starting with mock data...${NC}"
    "$PROJECT_ROOT/automation/scripts/test-with-mock-data.sh"

    # Wait for services to be ready
    sleep 5
fi

echo -e "${GREEN}✓ Services are running${NC}"

# Step 3: Install Python dependencies
echo -e "${YELLOW}Step 3: Checking Python dependencies...${NC}"

if ! python3 -c "import selenium" 2>/dev/null; then
    install_dependencies
fi

echo -e "${GREEN}✓ Dependencies installed${NC}"

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

# Run the Selenium tests
echo -e "${BLUE}Executing test suite...${NC}"
echo ""

python3 -m pytest \
    "$PROJECT_ROOT/tests/ui/test_bulletin_board_ui.py" \
    -v \
    --html="$REPORT_FILE" \
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

#!/bin/bash

# AgentSocial API-Based Testing Script
# Uses internal API endpoints to seed test data, ensuring proper validation/sanitization

set -eu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BULLETIN_SCRIPT="$PROJECT_ROOT/automation/scripts/bulletin-board.sh"
SEED_SCRIPT="$PROJECT_ROOT/packages/bulletin_board/scripts/seed_via_api.py"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}AgentSocial API-Based Testing Environment${NC}"
echo "============================================"
echo ""

# Function to check if services are running
check_services() {
    if docker ps | grep -q bulletin-db && docker ps | grep -q bulletin-web; then
        return 0
    else
        return 1
    fi
}

# Function to wait for web service to be ready
wait_for_web() {
    echo -n "Waiting for web service to be ready..."
    for _ in {1..30}; do
        if curl -s http://localhost:8080/health >/dev/null 2>&1; then
            echo -e " ${GREEN}ready!${NC}"
            return 0
        fi
        echo -n "."
        sleep 1
    done
    echo -e " ${RED}timeout!${NC}"
    return 1
}

# Step 1: Stop any existing services
echo -e "${YELLOW}Step 1: Cleaning up existing services...${NC}"
"$BULLETIN_SCRIPT" stop >/dev/null 2>&1 || true
sleep 2

# Step 2: Start fresh services
echo -e "${YELLOW}Step 2: Starting AgentSocial services...${NC}"
# Set environment variables to enable seed API
export ENABLE_SEED_API=true
export INTERNAL_API_KEY=development-seed-key
export ALLOW_DATA_CLEAR=true

"$BULLETIN_SCRIPT" start

# Step 3: Wait for services to be ready
echo -e "${YELLOW}Step 3: Ensuring services are ready...${NC}"
if ! wait_for_web; then
    echo -e "${RED}Web service failed to start. Exiting.${NC}"
    exit 1
fi

# Step 4: Initialize agent profiles
echo -e "${YELLOW}Step 4: Initializing agent profiles...${NC}"
"$BULLETIN_SCRIPT" init

# Step 5: Clear any existing test data (optional)
echo -e "${YELLOW}Step 5: Clearing existing test data...${NC}"
python3 "$SEED_SCRIPT" --clear --url http://localhost:8080 --key development-seed-key || {
    echo -e "${YELLOW}Warning: Could not clear data (may not exist)${NC}"
}

# Step 6: Seed comprehensive test data via API
echo -e "${YELLOW}Step 6: Seeding test data via API...${NC}"
python3 "$SEED_SCRIPT" --url http://localhost:8080 --key development-seed-key || {
    echo -e "${RED}Failed to seed data via API${NC}"
    echo "Make sure Python dependencies are installed:"
    echo "  pip install requests"
    exit 1
}

# Step 7: Additional batch data for testing
echo -e "${YELLOW}Step 7: Adding additional test scenarios...${NC}"
ADDITIONAL_SEED_SCRIPT="$PROJECT_ROOT/packages/bulletin_board/scripts/seed_additional_test_data.py"
python3 "$ADDITIONAL_SEED_SCRIPT" --url http://localhost:8080 --key development-seed-key || {
    echo -e "${RED}Failed to seed additional test data${NC}"
    exit 1
}

echo ""
echo -e "${GREEN}✓ API-based testing environment is ready!${NC}"
echo ""
echo -e "${YELLOW}Access the bulletin board at:${NC} http://localhost:8080"
echo ""
echo "Test data includes:"
echo "  • AI agents with diverse personalities"
echo "  • Technical posts and discussions"
echo "  • XSS test cases (should be sanitized)"
echo "  • MySpace-style profile customizations"
echo "  • Comments with reaction images"
echo ""
echo -e "${YELLOW}Benefits of API-based seeding:${NC}"
echo "  ✓ All data goes through validation"
echo "  ✓ HTML/XSS sanitization is applied"
echo "  ✓ Tests the full application stack"
echo "  ✓ Consistent with production data flow"
echo ""
echo -e "${YELLOW}Useful commands:${NC}"
echo "  View logs:    $BULLETIN_SCRIPT logs"
echo "  Stop:         $BULLETIN_SCRIPT stop"
echo "  Health check: $BULLETIN_SCRIPT health"
echo "  Re-seed:      python3 $SEED_SCRIPT"
echo ""

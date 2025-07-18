#!/bin/bash
# Run bulletin board agents

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}AgentSocial - Agent Runner${NC}"

# Check if specific agent ID is provided
AGENT_ID=${1:-""}

# Function to run agent in container
run_agent() {
    local agent_id=$1
    echo -e "${YELLOW}Running agent: ${agent_id}${NC}"
    
    docker-compose run --rm \
        -e DATABASE_URL=postgresql://bulletin:bulletin@bulletin-db:5432/bulletin_board \
        bulletin-web \
        python -m bulletin_board.agents.agent_runner ${agent_id}
}

# Initialize agents if requested
if [ "$1" == "init" ]; then
    echo -e "${YELLOW}Initializing agent profiles in database...${NC}"
    docker-compose run --rm \
        -e DATABASE_URL=postgresql://bulletin:bulletin@bulletin-db:5432/bulletin_board \
        bulletin-web \
        python -m bulletin_board.agents.init_agents
    exit 0
fi

# List agents if requested
if [ "$1" == "list" ]; then
    echo -e "${YELLOW}Available agents:${NC}"
    echo "- tech_enthusiast_claude (Claude Code)"
    echo "- security_analyst_gemini (Gemini CLI)"
    echo "- business_strategist_claude (Claude Code)"
    echo "- ai_researcher_gemini (Gemini CLI)"
    echo "- developer_advocate_claude (Claude Code)"
    exit 0
fi

# Run specific agent or all agents
if [ -n "$AGENT_ID" ]; then
    run_agent "$AGENT_ID"
else
    echo -e "${YELLOW}Running all agents...${NC}"
    docker-compose run --rm \
        -e DATABASE_URL=postgresql://bulletin:bulletin@bulletin-db:5432/bulletin_board \
        bulletin-web \
        python -m bulletin_board.agents.agent_runner
fi

echo -e "${GREEN}Agent run completed!${NC}"
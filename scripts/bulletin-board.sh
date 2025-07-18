#!/bin/bash
# Manage bulletin board services

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

COMMAND=${1:-"help"}

show_help() {
    echo -e "${GREEN}AgentSocial Bulletin Board Manager${NC}"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start     - Start all bulletin board services"
    echo "  stop      - Stop all bulletin board services"
    echo "  restart   - Restart all services"
    echo "  logs      - View logs from all services"
    echo "  web-logs  - View web application logs"
    echo "  db-logs   - View database logs"
    echo "  collector - View feed collector logs"
    echo "  status    - Check service status"
    echo "  init      - Initialize database and agent profiles"
    echo "  collect   - Run feed collectors once"
    echo "  help      - Show this help message"
}

case $COMMAND in
    start)
        echo -e "${YELLOW}Starting bulletin board services...${NC}"
        docker-compose up -d bulletin-db bulletin-web bulletin-collector
        echo -e "${GREEN}Services started!${NC}"
        echo "Web interface: http://localhost:8080"
        ;;
        
    stop)
        echo -e "${YELLOW}Stopping bulletin board services...${NC}"
        docker-compose stop bulletin-db bulletin-web bulletin-collector
        echo -e "${GREEN}Services stopped!${NC}"
        ;;
        
    restart)
        echo -e "${YELLOW}Restarting bulletin board services...${NC}"
        docker-compose restart bulletin-db bulletin-web bulletin-collector
        echo -e "${GREEN}Services restarted!${NC}"
        ;;
        
    logs)
        echo -e "${YELLOW}Showing logs for all bulletin board services...${NC}"
        docker-compose logs -f bulletin-db bulletin-web bulletin-collector
        ;;
        
    web-logs)
        echo -e "${YELLOW}Showing web application logs...${NC}"
        docker-compose logs -f bulletin-web
        ;;
        
    db-logs)
        echo -e "${YELLOW}Showing database logs...${NC}"
        docker-compose logs -f bulletin-db
        ;;
        
    collector)
        echo -e "${YELLOW}Showing feed collector logs...${NC}"
        docker-compose logs -f bulletin-collector
        ;;
        
    status)
        echo -e "${YELLOW}Checking service status...${NC}"
        docker-compose ps bulletin-db bulletin-web bulletin-collector
        ;;
        
    init)
        echo -e "${YELLOW}Initializing database and agent profiles...${NC}"
        
        # Wait for database to be ready
        echo "Waiting for database to be ready..."
        sleep 5
        
        # Initialize agent profiles
        docker-compose run --rm \
            -e DATABASE_URL=postgresql://bulletin:bulletin@bulletin-db:5432/bulletin_board \
            bulletin-web \
            python -m bulletin_board.agents.init_agents
            
        echo -e "${GREEN}Initialization complete!${NC}"
        ;;
        
    collect)
        echo -e "${YELLOW}Running feed collectors once...${NC}"
        docker-compose run --rm \
            -e DATABASE_URL=postgresql://bulletin:bulletin@bulletin-db:5432/bulletin_board \
            bulletin-web \
            python -m bulletin_board.agents.feed_collector
        echo -e "${GREEN}Collection complete!${NC}"
        ;;
        
    help|*)
        show_help
        ;;
esac
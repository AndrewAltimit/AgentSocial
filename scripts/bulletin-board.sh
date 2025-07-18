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
    echo "  health    - Check if services are healthy and ready"
    echo "  init      - Initialize database and agent profiles"
    echo "  collect   - Run feed collectors once"
    echo "  help      - Show this help message"
}

# Health check function
wait_for_postgres() {
    echo -n "Waiting for PostgreSQL to be ready..."
    for i in {1..30}; do
        if docker-compose exec -T bulletin-db pg_isready -U bulletin >/dev/null 2>&1; then
            echo -e " ${GREEN}ready!${NC}"
            return 0
        fi
        echo -n "."
        sleep 1
    done
    echo -e " ${RED}timeout!${NC}"
    return 1
}

wait_for_web() {
    echo -n "Waiting for web service to be ready..."
    for i in {1..30}; do
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

case $COMMAND in
    start)
        echo -e "${YELLOW}Starting bulletin board services...${NC}"
        docker-compose up -d bulletin-db bulletin-web bulletin-collector
        
        # Wait for services to be ready
        if wait_for_postgres && wait_for_web; then
            echo -e "${GREEN}All services are ready!${NC}"
            echo "Web interface: http://localhost:8080"
        else
            echo -e "${RED}Some services failed to start properly${NC}"
            echo "Check logs with: $0 logs"
            exit 1
        fi
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
        if ! wait_for_postgres; then
            echo -e "${RED}Database is not ready. Please ensure services are running.${NC}"
            exit 1
        fi
        
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
        
    health)
        echo -e "${YELLOW}Checking service health...${NC}"
        
        # Check database
        if wait_for_postgres; then
            echo -e "  Database: ${GREEN}healthy${NC}"
        else
            echo -e "  Database: ${RED}unhealthy${NC}"
        fi
        
        # Check web service
        if wait_for_web; then
            echo -e "  Web service: ${GREEN}healthy${NC}"
        else
            echo -e "  Web service: ${RED}unhealthy${NC}"
        fi
        ;;
        
    help|*)
        show_help
        ;;
esac
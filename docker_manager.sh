#!/bin/bash
# Quick Docker Management Script for OpenDiscourse
# Provides easy commands for common Docker tasks

set -e

echo "🐳 OpenDiscourse Docker Management"
echo "================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

case "$1" in
    "status")
        echo "${BLUE}📊 Current Docker Status:${NC}"
        echo ""
        echo "Running containers:"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
        echo ""
        echo "Resource usage:"
        docker system df
        ;;
    
    "essential")
        echo "${GREEN}🎯 Keeping only essential containers...${NC}"
        echo "Essential: mcp-postgres, mcp-redis, charm"
        
        # Stop non-essential containers
        non_essential=$(docker ps --format "{{.Names}}" | grep -v "mcp-postgres\|mcp-redis\|charm")
        
        if [ -n "$non_essential" ]; then
            echo "Stopping non-essential containers..."
            docker stop $non_essential
            echo "Removing non-essential containers..."
            docker rm $non_essential
        fi
        
        echo "${GREEN}✅ Only essential containers running${NC}"
        ;;
    
    "cleanup")
        echo "${YELLOW}🧹 Performing quick cleanup...${NC}"
        
        # Remove stopped containers
        stopped=$(docker ps -a --filter "status=exited" -q)
        if [ -n "$stopped" ]; then
            docker rm $stopped
            echo "Removed stopped containers"
        fi
        
        # Remove unused volumes
        docker volume prune -f
        
        # Remove unused images
        docker image prune -f
        
        echo "${GREEN}✅ Quick cleanup completed${NC}"
        ;;
    
    "volumes")
        echo "${BLUE}📦 Volume Management:${NC}"
        docker volume ls
        echo ""
        echo "Volume usage:"
        docker system df --format "table {{.Type}}\t{{.TotalCount}}\t{{.Size}}" | grep -E "(Local Volumes|TYPE)"
        ;;
    
    "logs")
        echo "${BLUE}📋 Container Logs:${NC}"
        if [ -n "$2" ]; then
            docker logs -f --tail 100 "$2"
        else
            echo "Available containers:"
            docker ps --format "{{.Names}}"
            echo ""
            echo "Usage: $0 logs <container_name>"
        fi
        ;;
    
    "restart")
        if [ -n "$2" ]; then
            echo "${YELLOW}🔄 Restarting container: $2${NC}"
            docker restart "$2"
            echo "${GREEN}✅ Container restarted${NC}"
        else
            echo "Usage: $0 restart <container_name>"
        fi
        ;;
    
    "ingest")
        echo "${GREEN}🚀 Starting data ingestion...${NC}"
        echo "Essential containers needed: mcp-postgres, mcp-redis"
        
        # Check if essential containers are running
        postgres_running=$(docker ps --format "{{.Names}}" | grep "mcp-postgres")
        redis_running=$(docker ps --format "{{.Names}}" | grep "mcp-redis")
        
        if [ -z "$postgres_running" ]; then
            echo "${RED}❌ mcp-postgres is not running${NC}"
            echo "Starting mcp-postgres..."
            docker start mcp-postgres
        fi
        
        if [ -z "$redis_running" ]; then
            echo "${RED}❌ mcp-redis is not running${NC}"
            echo "Starting mcp-redis..."
            docker start mcp-redis
        fi
        
        echo "${GREEN}✅ Essential containers are running${NC}"
        echo "Ready for data ingestion!"
        ;;
    
    *)
        echo "Usage: $0 {status|essential|cleanup|volumes|logs|restart|ingest}"
        echo ""
        echo "Commands:"
        echo "  status    - Show current Docker status"
        echo "  essential - Keep only essential containers (mcp-postgres, mcp-redis, charm)"
        echo "  cleanup   - Quick cleanup of unused resources"
        echo "  volumes   - Show volume information"
        echo "  logs      - Show container logs (logs <container_name>)"
        echo "  restart   - Restart a container (restart <container_name>)"
        echo "  ingest    - Prepare environment for data ingestion"
        echo ""
        echo "Examples:"
        echo "  $0 status"
        echo "  $0 essential"
        echo "  $0 cleanup"
        echo "  $0 logs mcp-postgres"
        echo "  $0 restart mcp-postgres"
        echo "  $0 ingest"
        ;;
esac
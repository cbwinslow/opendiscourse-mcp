#!/bin/bash
# Docker Cleanup Script for OpenDiscourse Project
# This script helps clean up unused containers, images, and volumes

set -e

echo "🧹 Docker Cleanup for OpenDiscourse Project"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $*"
}

# Function to ask for confirmation
confirm() {
    read -p "$1 [y/N]: " response
    case "$response" in
        [yY][eE][sS]|[yY])
            true
            ;;
        *)
            false
            ;;
    esac
}

echo ""
echo "📊 Current Docker Usage:"
docker system df

echo ""
echo "🔍 Analysis of containers..."

# Show problematic containers
echo ""
echo "${YELLOW}⚠️  Problematic Containers (Restarting/Failed):${NC}"
problematic_containers=$(docker ps -a --filter "status=exited" --filter "status=created" --format "{{.Names}}" | tr '\n' ' ')
restarting_containers=$(docker ps --filter "status=restarting" --format "{{.Names}}" | tr '\n' ' ')

if [ -n "$problematic_containers" ]; then
    echo "Stopped containers: $problematic_containers"
fi

if [ -n "$restarting_containers" ]; then
    echo "Restarting containers: $restarting_containers"
fi

# Show unused volumes
echo ""
echo "${YELLOW}📦 Unused Volumes:${NC}"
unused_volumes=$(docker volume ls -qf dangling=true)
if [ -n "$unused_volumes" ]; then
    docker volume ls -f dangling=true
else
    echo "No dangling volumes found"
fi

# Show unused images
echo ""
echo "${YELLOW}🖼️  Unused Images:${NC}"
unused_images=$(docker images -f "dangling=true" -q)
if [ -n "$unused_images" ]; then
    docker images -f "dangling=true"
else
    echo "No dangling images found"
fi

echo ""
echo "🔧 Cleanup Options:"

# Option 1: Remove problematic containers
if confirm "Remove stopped and problematic containers?"; then
    echo ""
    log "🗑️  Removing stopped containers..."
    docker rm $(docker ps -a --filter "status=exited" --filter "status=created" -q) 2>/dev/null || true
    
    log "🔄 Stopping and removing restarting containers..."
    restarting_containers=$(docker ps --filter "status=restarting" --format "{{.Names}}")
    for container in $restarting_containers; do
        log "Stopping $container..."
        docker stop "$container" || true
        log "Removing $container..."
        docker rm "$container" || true
    done
    
    echo "${GREEN}✅ Container cleanup completed${NC}"
fi

# Option 2: Remove unused volumes
if confirm "Remove unused volumes? (WARNING: This will delete data!)"; then
    echo ""
    log "📦 Removing unused volumes..."
    docker volume prune -f
    echo "${GREEN}✅ Volume cleanup completed${NC}"
fi

# Option 3: Remove unused images
if confirm "Remove unused/dangling images?"; then
    echo ""
    log "🖼️  Removing unused images..."
    docker image prune -f
    echo "${GREEN}✅ Image cleanup completed${NC}"
fi

# Option 4: Clean up build cache
if confirm "Clean up Docker build cache?"; then
    echo ""
    log "🏗️  Cleaning build cache..."
    docker builder prune -f
    echo "${GREEN}✅ Build cache cleanup completed${NC}"
fi

# Option 5: Selective cleanup for specific projects
echo ""
if confirm "Perform selective cleanup for specific failed projects?"; then
    echo ""
    log "🎯 Cleaning up specific failed project containers..."
    
    # Clean up specific problematic containers
    failed_containers="ai-automation-n8n-1 ai-automation-loki-1 ai-automation-dify-worker-1 docker-mcp-server supermemory-ai mcp-context-forge"
    
    for container in $failed_containers; do
        if docker ps -a --format "{{.Names}}" | grep -q "^${container}$"; then
            log "Removing failed container: $container"
            docker stop "$container" 2>/dev/null || true
            docker rm "$container" 2>/dev/null || true
        fi
    done
    
    # Clean up associated volumes
    echo ""
    log "📦 Cleaning up associated volumes..."
    
    # List of volumes that might be safe to remove
    safe_to_remove_volumes="ai-automation_n8n_data ai-automation_n8n_postgres 4d9eb1060ee0deeeb0813744ae17ca85dc770ad43b6463618ef7136dcc761e5a a09b96d7b5a08a5ac41baf55d107aed99aa30b8263b90be25233a7583f67930e"
    
    for volume in $safe_to_remove_volumes; do
        if docker volume ls -q --filter name=^${volume}$ | grep -q .; then
            log "Removing volume: $volume"
            docker volume rm "$volume" 2>/dev/null || true
        fi
    done
    
    echo "${GREEN}✅ Selective cleanup completed${NC}"
fi

# Option 6: Full system cleanup
echo ""
if confirm "Perform full Docker system cleanup? (WARNING: This removes all unused containers, networks, images, and build cache)"; then
    echo ""
    log "🧹 Performing full system cleanup..."
    docker system prune -af --volumes
    echo "${GREEN}✅ Full system cleanup completed${NC}"
fi

echo ""
echo "📊 Final Docker Usage After Cleanup:"
docker system df

echo ""
echo "🏃 Running containers after cleanup:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"

echo ""
echo "💡 Recommendations:"
echo "1. Keep only essential containers running:"
echo "   - mcp-postgres (database)"
echo "   - mcp-redis (cache)"
echo "   - charm (if using)"
echo "   - buildx_buildkit_* (if building images)"
echo ""
echo "2. Consider using docker-compose for better management"
echo "3. Set up automatic cleanup with cron:"
echo "   0 2 * * 0 docker system prune -f"
echo ""
echo "✨ Cleanup completed successfully!"
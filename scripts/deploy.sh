#!/bin/bash

# Production Deployment Script for Outreach Agent
# This script handles pulling latest images and restarting services

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REPO_DIR="/app/outreach-agent"
COMPOSE_FILE="docker-compose.prod.yml"
LOG_FILE="/var/log/outreach-agent-deploy.log"

# Functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   error "This script must be run as root"
fi

# Main deployment flow
log "Starting Outreach Agent deployment..."

# Navigate to repo directory
if [ ! -d "$REPO_DIR" ]; then
    error "Repository directory not found at $REPO_DIR"
fi

cd "$REPO_DIR" || error "Failed to navigate to $REPO_DIR"
log "Working directory: $(pwd)"

# Check Docker and Docker Compose
if ! command -v docker &> /dev/null; then
    error "Docker is not installed"
fi

if ! command -v docker-compose &> /dev/null; then
    error "Docker Compose is not installed"
fi

log "Docker version: $(docker --version)"
log "Docker Compose version: $(docker-compose --version)"

# Pull latest changes from git
log "Pulling latest changes from git..."
git fetch origin
git pull origin main || error "Failed to pull from git"

# Check if production compose file exists
if [ ! -f "$COMPOSE_FILE" ]; then
    warning "$COMPOSE_FILE not found, using docker-compose.yml"
    COMPOSE_FILE="docker-compose.yml"
fi

# Pull latest images
log "Pulling latest Docker images..."
docker-compose -f "$COMPOSE_FILE" pull || error "Failed to pull Docker images"

# Backup current database (optional but recommended)
if [ -f "data/outreach.db" ]; then
    BACKUP_DIR="backups/$(date +'%Y%m%d_%H%M%S')"
    mkdir -p "$BACKUP_DIR"
    cp data/outreach.db "$BACKUP_DIR/outreach.db.backup"
    log "Database backed up to: $BACKUP_DIR"
fi

# Stop current services
log "Stopping current services..."
docker-compose -f "$COMPOSE_FILE" down || warning "Services were not running"

# Start services
log "Starting services..."
docker-compose -f "$COMPOSE_FILE" up -d || error "Failed to start services"

# Wait for services to be healthy
log "Waiting for services to become healthy..."
sleep 10

# Check service health
BACKEND_HEALTH=$(docker-compose -f "$COMPOSE_FILE" ps backend | grep -c "healthy" || echo "0")
FRONTEND_HEALTH=$(docker-compose -f "$COMPOSE_FILE" ps frontend | grep -c "healthy" || echo "0")

if [ "$BACKEND_HEALTH" -eq 0 ] || [ "$FRONTEND_HEALTH" -eq 0 ]; then
    warning "Services may not be fully healthy yet. Showing logs:"
    docker-compose -f "$COMPOSE_FILE" logs --tail=20
fi

# Display service status
log "Service status:"
docker-compose -f "$COMPOSE_FILE" ps

# Show URLs
log ""
log "==================================="
log "✅ Deployment completed successfully!"
log "==================================="
log "Application URLs:"
log "  Frontend: http://localhost:3000"
log "  Backend: http://localhost:8000"
log "  API Docs: http://localhost:8000/docs"
log "==================================="
log ""

# View logs
log "Recent logs (last 10 lines):"
docker-compose -f "$COMPOSE_FILE" logs --tail=10

# Cleanup old images (optional)
log "Cleaning up unused Docker images..."
docker image prune -f || warning "Failed to prune images"

log "Deployment finished!"

#!/bin/bash

# Health Check Script for Outreach Agent Services

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

BACKEND_URL="http://localhost:8000/docs"
FRONTEND_URL="http://localhost:3000"

echo "Checking Outreach Agent Services Health..."
echo ""

# Check Backend
echo -n "Backend (${BACKEND_URL}): "
if curl -sf "$BACKEND_URL" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Healthy${NC}"
else
    echo -e "${RED}✗ Unhealthy${NC}"
fi

# Check Frontend
echo -n "Frontend (${FRONTEND_URL}): "
if curl -sf "$FRONTEND_URL" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Healthy${NC}"
else
    echo -e "${RED}✗ Unhealthy${NC}"
fi

# Docker container status
echo ""
echo "Docker Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep outreach || echo -e "${YELLOW}No Outreach containers found${NC}"

echo ""
echo "Tip: Check logs with: docker-compose logs -f [backend|frontend]"

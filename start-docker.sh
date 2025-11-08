#!/bin/bash
# =============================================================================
# Geopard Docker Startup Script for Linux/Mac
# =============================================================================
# This script starts the Geopard application using Docker Compose
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}========================================================================${NC}"
echo -e "${BLUE}  🌍 Geopard - AI-Powered Geodata Assistant for Canton Luzern${NC}"
echo -e "${BLUE}========================================================================${NC}"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} Docker is not installed"
    echo ""
    echo "Please install Docker from: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is available
if ! docker compose version &> /dev/null && ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} Docker Compose is not installed"
    echo ""
    echo "Please install Docker Compose from: https://docs.docker.com/compose/install/"
    exit 1
fi

# Use docker compose (v2) or docker-compose (v1)
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo -e "${GREEN}[OK]${NC} Docker is installed and running"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}[WARNING]${NC} .env file not found"
    echo ""
    
    if [ -f .env.example ]; then
        echo "Creating .env from .env.example..."
        cp .env.example .env
        echo ""
        echo -e "${RED}[IMPORTANT]${NC} Please edit .env file with your Azure credentials:"
        echo "  - AZURE_OPENAI_API_KEY"
        echo "  - AZURE_OPENAI_ENDPOINT"
        echo "  - AZURE_SEARCH_ENDPOINT"
        echo "  - AZURE_SEARCH_KEY"
        echo ""
        echo "Then run this script again."
        exit 1
    else
        echo -e "${RED}[ERROR]${NC} No .env.example template found"
        exit 1
    fi
fi

echo -e "${GREEN}[OK]${NC} Environment file found"
echo ""

# Stop any existing containers
echo "Stopping any existing containers..."
$DOCKER_COMPOSE down 2>/dev/null || true

# Build and start the containers
echo ""
echo "Building Docker image..."
echo "This may take a few minutes on first run..."
echo ""
$DOCKER_COMPOSE build

echo ""
echo "Starting Geopard application..."
echo ""
$DOCKER_COMPOSE up -d

echo ""
echo -e "${BLUE}========================================================================${NC}"
echo -e "${GREEN}  ✓ Geopard is now running!${NC}"
echo -e "${BLUE}========================================================================${NC}"
echo ""
echo -e "  ${GREEN}Web Interface:${NC}  http://localhost:8000"
echo -e "  ${GREEN}API Docs:${NC}       http://localhost:8000/docs"
echo -e "  ${GREEN}Health Check:${NC}   http://localhost:8000/health"
echo ""
echo -e "  ${YELLOW}To view logs:${NC}     $DOCKER_COMPOSE logs -f"
echo -e "  ${YELLOW}To stop:${NC}          $DOCKER_COMPOSE down"
echo ""
echo -e "${BLUE}========================================================================${NC}"
echo ""

# Wait for container to be healthy
echo "Waiting for application to start..."
sleep 5

# Check container status
if $DOCKER_COMPOSE ps | grep -q "Up"; then
    echo -e "${GREEN}[OK]${NC} Application is running"
    echo ""
    
    # Try to open browser on Linux
    if command -v xdg-open &> /dev/null; then
        xdg-open http://localhost:8000 2>/dev/null || true
    elif command -v open &> /dev/null; then
        # macOS
        open http://localhost:8000 2>/dev/null || true
    fi
else
    echo -e "${YELLOW}[WARNING]${NC} Container may still be starting up"
    echo "Check logs with: $DOCKER_COMPOSE logs -f"
fi

echo ""

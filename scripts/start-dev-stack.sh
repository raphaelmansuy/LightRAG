#!/bin/bash

# Start LightRAG Development Stack
# This script starts all services: PostgreSQL, Redis, API Server, and WebUI

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         🚀 Starting LightRAG Development Stack                       ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════╝${NC}"

# Change to project root
cd "$PROJECT_ROOT"

# Step 1: Start Docker containers
echo -e "\n${YELLOW}[1/4]${NC} Starting Docker containers (PostgreSQL + Redis)..."
docker-compose -f docker-compose.test-db.yml up -d --build

echo -e "${GREEN}✓${NC} Docker containers started"

# Step 2: Wait for PostgreSQL to be ready
echo -e "\n${YELLOW}[2/4]${NC} Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
  if docker exec lightrag-audit-postgres pg_isready -U lightrag -d lightrag_audit > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} PostgreSQL is ready"
    break
  fi
  if [ $i -eq 30 ]; then
    echo -e "${RED}✗${NC} PostgreSQL failed to start after 30 seconds"
    exit 1
  fi
  sleep 1
done

# Step 3: Start API Server
echo -e "\n${YELLOW}[3/4]${NC} Starting LightRAG API Server on port 9621..."
cd "$PROJECT_ROOT"

# Export environment variables for the API
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5433
export POSTGRES_USER=lightrag
export POSTGRES_PASSWORD=lightrag123
export POSTGRES_DATABASE=lightrag_audit
export REDIS_HOST=localhost
export REDIS_PORT=6380
export LIGHTRAG_MULTI_TENANT_STRICT=true
export LIGHTRAG_REQUIRE_USER_AUTH=true
export LLM_BINDING=ollama
export LLM_BINDING_HOST=http://localhost:11434
export EMBEDDING_BINDING=ollama
export EMBEDDING_BINDING_HOST=http://localhost:11434

# Start API server in background
python -m lightrag.api.lightrag_server --host 0.0.0.0 --port 9621 > /tmp/lightrag-api.log 2>&1 &
API_PID=$!
echo $API_PID > /tmp/lightrag-api.pid

echo -e "${GREEN}✓${NC} API Server started (PID: $API_PID)"

# Wait for API to be ready
echo -e "\n   Waiting for API to be ready..."
for i in {1..30}; do
  if curl -s http://localhost:9621/health > /dev/null 2>&1; then
    echo -e "   ${GREEN}✓${NC} API is ready"
    break
  fi
  if [ $i -eq 30 ]; then
    echo -e "   ${RED}✗${NC} API failed to start after 30 seconds"
    tail -20 /tmp/lightrag-api.log
    kill $API_PID 2>/dev/null || true
    exit 1
  fi
  sleep 1
done

# Step 4: Start WebUI
echo -e "\n${YELLOW}[4/4]${NC} Starting WebUI dev server on port 5173..."
cd "$PROJECT_ROOT/lightrag_webui"
npm run dev > /tmp/lightrag-webui.log 2>&1 &
WEBUI_PID=$!
echo $WEBUI_PID > /tmp/lightrag-webui.pid

echo -e "${GREEN}✓${NC} WebUI Server started (PID: $WEBUI_PID)"

# Wait for WebUI to be ready
echo -e "\n   Waiting for WebUI to be ready..."
for i in {1..30}; do
  if curl -s http://localhost:5173/ > /dev/null 2>&1; then
    echo -e "   ${GREEN}✓${NC} WebUI is ready"
    break
  fi
  if [ $i -eq 30 ]; then
    echo -e "   ${YELLOW}⚠${NC}  WebUI may take longer to start, continuing anyway..."
    break
  fi
  sleep 1
done

# Display final status
echo -e "\n${BLUE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                   ✅ Stack Started Successfully!                     ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════╝${NC}"

echo -e "\n${GREEN}Services Running:${NC}"
echo -e "  • PostgreSQL:  localhost:5433 (lightrag_audit)"
echo -e "  • Redis:       localhost:6380"
echo -e "  • API:         ${BLUE}http://localhost:9621${NC}"
echo -e "  • WebUI:       ${BLUE}http://localhost:5173${NC}"

echo -e "\n${GREEN}Useful Links:${NC}"
echo -e "  • API Docs:    ${BLUE}http://localhost:9621/docs${NC}"
echo -e "  • OpenAPI:     ${BLUE}http://localhost:9621/openapi.json${NC}"

echo -e "\n${GREEN}Process IDs:${NC}"
echo -e "  • API Server:  $API_PID"
echo -e "  • WebUI:       $WEBUI_PID"

echo -e "\n${YELLOW}To view logs:${NC}"
echo -e "  • API:   tail -f /tmp/lightrag-api.log"
echo -e "  • WebUI: tail -f /tmp/lightrag-webui.log"

echo -e "\n${YELLOW}To stop the stack:${NC}"
echo -e "  • Run: bash scripts/stop-dev-stack.sh"

echo ""

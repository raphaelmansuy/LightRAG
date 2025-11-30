#!/bin/bash

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Multi-Tenant Isolation Test...${NC}"

# Function to kill server on port 9621
cleanup_server() {
    if lsof -i :9621 > /dev/null; then
        echo "Stopping existing server on port 9621..."
        lsof -i :9621 | grep Python | awk '{print $2}' | xargs kill -9
        sleep 2
        echo "Server stopped."
    fi
}

# Ensure clean start
cleanup_server

echo "Starting server with test configuration..."

# Set environment variables for local testing
export LLM_BINDING="ollama"
export LLM_MODEL="granite4:latest"
export EMBEDDING_BINDING="ollama"
export EMBEDDING_MODEL="bge-m3:latest"
export LIGHTRAG_API_KEY="admin123" # Example key if needed, though auth is handled by user/pass usually

echo "Environment Configured:"
echo "  LLM_BINDING: $LLM_BINDING"
echo "  LLM_MODEL: $LLM_MODEL"
echo "  EMBEDDING_BINDING: $EMBEDDING_BINDING"
echo "  EMBEDDING_MODEL: $EMBEDDING_MODEL"

# Start server in background
nohup python -m lightrag.api.lightrag_server --port 9621 > server.log 2>&1 &
SERVER_PID=$!
echo "Server started with PID $SERVER_PID. Waiting for startup..."
sleep 10

# Run the test script
echo -e "${GREEN}Running test script...${NC}"
python e2e/test_multitenant_isolation.py
TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}Tests Passed!${NC}"
else
    echo -e "${RED}Tests Failed!${NC}"
fi

# Optional: Kill server if we started it?
# For now, let's leave it running as it might be useful for debugging or subsequent tests.
# If you want to kill it, uncomment below:
# if [ ! -z "$SERVER_PID" ]; then
#     kill $SERVER_PID
# fi

exit $TEST_EXIT_CODE

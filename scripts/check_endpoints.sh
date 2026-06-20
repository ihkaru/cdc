#!/bin/bash
# check_endpoints.sh - Wrapper script to execute the BPS API route diagnostics inside the Docker container.

# Change to repository root directory
cd "$(dirname "$0")/.." || exit 1

PID_DIR="/tmp/fasih-nexus-local"
CONTAINER_NAME="fasih-nexus-rpa"

echo "=========================================================================="
echo "          🚨  FasihNexus — BPS API Route & Performance Check  🚨          "
echo "=========================================================================="

# 1. Check if RPA Docker container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  echo "❌ Error: Docker container '${CONTAINER_NAME}' is not running!"
  echo "   Please start the infrastructure using './start-local.sh' or './start-docker.sh' first."
  exit 1
fi

echo "✓ Docker container '${CONTAINER_NAME}' is active."
echo "📡 Launching diagnostic script inside container..."
echo ""

# 2. Execute Python check script inside the container
docker exec -it "$CONTAINER_NAME" python /app/scripts/check_endpoints.py

echo ""
echo "=========================================================================="
echo "                     Diagnostics Run Finished                             "
echo "=========================================================================="

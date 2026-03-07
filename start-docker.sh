#!/bin/bash
# start-docker.sh - Start Full Docker Environment

echo "================================================="
echo " Starting Full Docker Production/Test Environment"
echo "================================================="

docker compose up -d

echo ""
echo " ✅ All services started in background."
echo " 🌍 Dashboard accessible at: http://localhost:3000"
echo " 📝 To view logs: docker compose logs -f"
echo "================================================="

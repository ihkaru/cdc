#!/bin/bash
# start-docker.sh - Start Full Docker Environment
#
# Usage:
#   ./start-docker.sh                   # Start normal (pakai image cached)
#   ./start-docker.sh --build           # Rebuild semua service lalu start
#   ./start-docker.sh --build rpa       # Rebuild hanya service 'rpa' lalu start
#   ./start-docker.sh --build dashboard rpa   # Rebuild beberapa service sekaligus

echo "================================================="
echo " Starting Full Docker Production/Test Environment"
echo "================================================="

# 🧹 Zombie Cleanup: Hapus sisa-sisa browser lama agar tidak menumpuk di Docker volume
echo "🧹 Cleaning up old browser profiles and temp files..."
rm -rf /tmp/playwright_reporting*
rm -rf /tmp/fasih_storage_state_*.json
rm -rf /tmp/.com.google.Chrome.*

if [[ "$1" == "--build" ]]; then
    shift  # buang argumen --build
    SERVICES=("$@")  # sisa argumen = nama service (boleh kosong = semua)

    if [[ ${#SERVICES[@]} -eq 0 ]]; then
        echo "🔨 Mode: Rebuild SEMUA service..."
        docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build --force-recreate
    else
        echo "🔨 Mode: Rebuild service: ${SERVICES[*]}"
        docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build --force-recreate "${SERVICES[@]}"
    fi
else
    echo "▶  Mode: Start normal (image cached, tanpa rebuild)"
    docker compose -f docker-compose.yml -f docker-compose.local.yml up -d
fi


echo ""
echo " ✅ All services started in background."
echo " 🌍 Dashboard accessible at: http://127.0.0.1:3000"
echo " 📝 To view logs: docker compose logs -f"
echo "================================================="

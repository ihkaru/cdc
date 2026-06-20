#!/bin/bash
# stop-local.sh — Stop ALL FasihNexus local services (local + Docker)
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.local.yml"

echo "🛑 Stopping ALL FasihNexus services..."

# Kill local processes by PID file
PID_FILE="/tmp/fasih-nexus.pids"
if [ -f "$PID_FILE" ]; then
  while IFS=: read -r name pid; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      echo "  ↓ Stopping $name (pgid=$pid)..."
      kill -- -"$pid" 2>/dev/null || true
      sleep 0.2; kill -9 -- -"$pid" 2>/dev/null || true
    fi
  done < "$PID_FILE"
  rm -f "$PID_FILE"
fi

# Fallback
pkill -f "bun run dev" 2>/dev/null || true
pkill -f "quasar dev"  2>/dev/null || true
rm -f /tmp/fasih-nexus.lock

# Stop Docker containers
cd "$PROJECT_DIR"
$COMPOSE down --remove-orphans
echo "✅ All services stopped."

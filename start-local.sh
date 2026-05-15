#!/bin/bash
# start-local.sh - Start Development Environment with Local HMR
# Uses process groups and PID files for clean shutdown without zombie processes.

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_DIR="/tmp/fasih-nexus-local"
mkdir -p "$PID_DIR"

# ─── Cleanup Function ───────────────────────────────────────────
cleanup() {
  echo ""
  echo "🛑 Stopping local servers..."

  # Kill each tracked process group
  for pidfile in "$PID_DIR"/*.pid; do
    [ -f "$pidfile" ] || continue
    pid=$(cat "$pidfile")
    name=$(basename "$pidfile" .pid)
    if kill -0 "$pid" 2>/dev/null; then
      echo "   Stopping $name (pgid $pid)..."
      # Kill entire process group (negative PID = group)
      kill -- -"$pid" 2>/dev/null || true
      # Wait briefly, then force-kill stragglers
      sleep 0.3
      kill -9 -- -"$pid" 2>/dev/null || true
    fi
    rm -f "$pidfile"
  done

  echo " ✅ Local servers stopped."
  exit 0
}

# Trap all relevant signals + script exit
trap cleanup INT TERM HUP QUIT EXIT

echo "================================================="
echo " Starting Local Development Environment (HMR) "
echo "================================================="

# ─── Step 1: Infrastructure (DB, VPN, S3) ───────────────────────
echo "[1/3] Starting Infrastructure in Docker..."
# Docker will automatically pick up docker-compose.override.yml 
# so ports 5432, 8000, 8333 will be exposed to localhost automatically.
docker compose up -d postgres vpn rpa vpn-auth master volume filer s3 archiver || { echo "❌ Infra failed to start. Aborting."; exit 1; }

# Ensure dashboard container is stopped in Docker to free up port 3000 for local Bun/Quasar
echo "[2/3] Ensuring Dashboard Docker container is stopped..."
docker compose stop dashboard

# ─── Step 2: Environment variables ──────────────────────────────
echo "[3/3] Preparing Local Environment Variables..."
if [ -f "$PROJECT_DIR/.env" ]; then
  set -a
  source "$PROJECT_DIR/.env"
  set +a

  # Default Better Auth Secret if not set
  export BETTER_AUTH_SECRET="${BETTER_AUTH_SECRET:-a_very_long_random_string_for_local_dev}"

  # Override DATABASE_URL to use localhost instead of docker alias
  # Using 127.0.0.1 to avoid Docker IPv6 vs IPv4 binding mismatches
  LOCAL_DB_URL=$(echo "$DATABASE_URL" | sed 's/@postgres:/@127.0.0.1:/')
  export DATABASE_URL="$LOCAL_DB_URL"
  echo "      DB URL overridden for local access: $DATABASE_URL"

  # RPA runs inside Docker (network_mode: service:vpn), accessible on localhost:8000
  export RPA_URL="http://localhost:8000"
  export VPN_AUTH_URL="http://localhost:8001"

  # S3 endpoint override for local dashboard access
  export S3_ENDPOINT="http://localhost:8333"
  echo "      S3 Endpoint overridden for local access: $S3_ENDPOINT"
else
  echo "      WARNING: .env file not found in root directory!"
fi

echo "================================================="
echo " Starting Backend (Elysia) and Frontend (Quasar) "
echo "================================================="

cd "$PROJECT_DIR/dashboard" || { echo "dashboard directory not found"; exit 1; }

echo "[4/4] Migrating Database Schema locally..."
DATABASE_URL="$LOCAL_DB_URL" bunx drizzle-kit push

echo "      ENCRYPTION_KEY status: ${ENCRYPTION_KEY:+LOADED (Length: ${#ENCRYPTION_KEY})}"

# ─── Start Backend (Bun) as its own process group ───────────────
setsid bun run dev &
BACKEND_PID=$!
echo $BACKEND_PID > "$PID_DIR/backend.pid"

# ─── Start Frontend (Quasar) as its own process group ───────────
cd client || { echo "dashboard/client directory not found"; exit 1; }
setsid bunx quasar dev &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$PID_DIR/frontend.pid"

echo "-------------------------------------------------"
echo " ✅ Backend is running  (PID group: $BACKEND_PID)"
echo " ✅ Frontend is running (PID group: $FRONTEND_PID)"
echo " 📁 PID files stored in: $PID_DIR/"
echo " 🛑 Press Ctrl+C to stop both local servers"
echo "-------------------------------------------------"

# Wait indefinitely for background jobs
wait

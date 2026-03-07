#!/bin/bash
# start-local.sh - Start Development Environment with Local HMR
# Uses process groups and PID files for clean shutdown without zombie processes.

CDC_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_DIR="/tmp/cdc-local"
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

# ─── Step 1: Database (required) ────────────────────────────────
echo "[1/3] Starting Database in Docker..."
docker compose up -d postgres || { echo "❌ Database failed to start. Aborting."; exit 1; }

# ─── Step 1b: VPN + RPA (optional — may fail if cookie expired) ─
echo "      Starting VPN and RPA..."
if ! docker compose up -d vpn rpa 2>&1; then
  echo ""
  echo "⚠️  VPN/RPA failed to start (cookie probably expired)."
  echo "   Dashboard will still launch — update the cookie via UI."
  echo ""
fi

# Ensure dashboard container is stopped to free up port 3000
echo "[2/3] Stopping Dashboard Docker container (if running)..."
docker compose stop dashboard

# ─── Step 2: Environment variables ──────────────────────────────
echo "[3/3] Preparing Local Environment Variables..."
if [ -f "$CDC_DIR/.env" ]; then
  set -a
  source "$CDC_DIR/.env"
  set +a

  # Override DATABASE_URL to use localhost instead of docker alias
  # Using 127.0.0.1 to avoid Docker IPv6 vs IPv4 binding mismatches
  LOCAL_DB_URL=$(echo "$DATABASE_URL" | sed 's/@postgres:/@127.0.0.1:/')
  export DATABASE_URL="$LOCAL_DB_URL"
  echo "      DB URL overridden for local access: $DATABASE_URL"

  # RPA runs inside Docker (network_mode: service:vpn), accessible on localhost:8000
  export RPA_URL="http://localhost:8000"
else
  echo "      WARNING: .env file not found in root directory!"
fi

echo "================================================="
echo " Starting Backend (Elysia) and Frontend (Quasar) "
echo "================================================="

cd "$CDC_DIR/dashboard" || { echo "dashboard directory not found"; exit 1; }

echo "[4/4] Migrating Database Schema locally..."
DATABASE_URL="$LOCAL_DB_URL" bunx drizzle-kit push

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

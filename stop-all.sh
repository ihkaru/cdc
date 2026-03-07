#!/bin/bash
# stop-all.sh - Clean Teardown of Docker and Local Servers
# Reads PID files first for precise cleanup, falls back to pkill as safety net.

echo "================================================="
echo " Stopping All Environments (Docker & Local Tools)"
echo "================================================="

PID_DIR="/tmp/cdc-local"

# ─── Step 1: Kill tracked local processes via PID files ─────────
echo "[1/3] Stopping tracked local processes..."
if [ -d "$PID_DIR" ]; then
  for pidfile in "$PID_DIR"/*.pid; do
    [ -f "$pidfile" ] || continue
    pid=$(cat "$pidfile")
    name=$(basename "$pidfile" .pid)
    if kill -0 "$pid" 2>/dev/null; then
      echo "      Stopping $name (pgid $pid)..."
      kill -- -"$pid" 2>/dev/null || true
      sleep 0.3
      kill -9 -- -"$pid" 2>/dev/null || true
    else
      echo "      $name (pid $pid) already stopped."
    fi
    rm -f "$pidfile"
  done
  rmdir "$PID_DIR" 2>/dev/null || true
else
  echo "      No PID directory found, skipping."
fi

# ─── Step 2: Fallback pkill for any orphaned processes ──────────
echo "[2/3] Cleaning up any orphaned local processes (safety net)..."
pkill -f "quasar dev" 2>/dev/null || true
pkill -f "bun run dev" 2>/dev/null || true

# ─── Step 3: Stop Docker containers ────────────────────────────
echo "[3/3] Stopping Docker services..."
docker compose down

echo "-------------------------------------------------"
echo " ✅ Everything has been stopped gracefully."
echo "     Ready for a fresh start!"
echo "-------------------------------------------------"

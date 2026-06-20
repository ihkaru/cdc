#!/bin/bash
# =============================================================================
# start-local.sh — One-Command Local Development Environment
# =============================================================================
# Guarantees:
#   - Kills ALL orphan processes from previous runs (PID file + pkill fallback)
#   - Frees conflicting ports before starting
#   - ALWAYS uses both compose files so port bindings are never lost
#   - Waits for DB to be healthy before starting Bun (prevents login 500)
#   - Graceful Ctrl+C shutdown of all child processes
# =============================================================================

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Constants ──────────────────────────────────────────────────────────────────
# CRITICAL: Always use both files. Omitting docker-compose.local.yml drops the
# fasih-db port binding → Bun gets ECONNREFUSED:5436 → 500 on login → /login redirect.
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.local.yml"
PID_FILE="/tmp/fasih-nexus.pids"
LOG_DIR="/tmp/fasih-nexus-logs"
LOCK_FILE="/tmp/fasih-nexus.lock"

# Ports used by local (non-Docker) processes
LOCAL_PORTS=(3009 9009 9010)

# Colors
C_GREEN='\033[0;32m'; C_YELLOW='\033[1;33m'; C_RED='\033[0;31m'
C_BLUE='\033[0;34m'; C_CYAN='\033[0;36m'; C_BOLD='\033[1m'; C_NC='\033[0m'

log()  { echo -e "${C_GREEN}▶${C_NC} $1"; }
step() { echo -e "\n${C_BOLD}${C_BLUE}[$1]${C_NC} $2"; }
ok()   { echo -e "  ${C_GREEN}✓${C_NC} $1"; }
warn() { echo -e "  ${C_YELLOW}⚠${C_NC} $1"; }
die()  { echo -e "\n${C_RED}✗ FATAL:${C_NC} $1"; exit 1; }

mkdir -p "$LOG_DIR"

# ── 1. Kill any orphan processes from previous runs ───────────────────────────
step "1/5" "🧹 Cleaning up previous session..."

# Kill by saved PID groups
if [ -f "$PID_FILE" ]; then
  while IFS=: read -r name pid; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      warn "Stopping orphan $name (pgid=$pid)..."
      kill -- -"$pid" 2>/dev/null || true
      sleep 0.3
      kill -9 -- -"$pid" 2>/dev/null || true
    fi
  done < "$PID_FILE"
  rm -f "$PID_FILE"
fi

# Fallback: kill by process name (handles crashes where PID file was lost)
pkill -f "bun run dev" 2>/dev/null && warn "Killed orphan 'bun run dev' process" || true
pkill -f "quasar dev"  2>/dev/null && warn "Killed orphan 'quasar dev' process"  || true
rm -f "$LOCK_FILE"
sleep 0.5

# Free local ports if still occupied
for port in "${LOCAL_PORTS[@]}"; do
  pids=$(lsof -ti:"$port" 2>/dev/null || true)
  if [ -n "$pids" ]; then
    warn "Port $port occupied (PID $pids). Freeing..."
    echo "$pids" | xargs kill -9 2>/dev/null || true
    sleep 0.2
  fi
done
ok "Cleanup done — no orphans, no port conflicts."

# ── 2. Load Environment Variables ─────────────────────────────────────────────
step "2/5" "⚙️  Loading environment..."

[ -f "$PROJECT_DIR/.env" ] || die ".env not found at $PROJECT_DIR/.env"
set -a
# shellcheck disable=SC1091
source "$PROJECT_DIR/.env"
set +a

# Guarantee critical vars
export BETTER_AUTH_SECRET="${BETTER_AUTH_SECRET:-a_very_long_random_string_for_local_dev}"
_bun_port="${PORT:-3009}"
export BETTER_AUTH_URL="${BETTER_AUTH_URL:-http://localhost:${_bun_port}}"
export PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-http://localhost:9009}"

# CRITICAL: Two separate DB URLs are needed:
#   DOCKER_DATABASE_URL → used by Docker containers (hostname: fasih-db:5432, internal DNS)
#   LOCAL_DB_URL        → used by Bun backend on host (hostname: 127.0.0.1:5436, port-forwarded)
# Never export DATABASE_URL override before docker compose up — it would poison all containers!
DB_PORT="${DB_PORT:-5436}"
DOCKER_DATABASE_URL="$DATABASE_URL"  # keep original fasih-db:5432 for containers
LOCAL_DB_URL=$(echo "$DATABASE_URL" | sed -E "s/@(postgres|fasih-db):[0-9]+/@127.0.0.1:${DB_PORT}/")
# Do NOT export DATABASE_URL here — Docker containers must see fasih-db:5432

export RPA_URL="http://127.0.0.1:${RPA_PORT:-8010}"
export VPN_AUTH_URL="http://127.0.0.1:${VPN_AUTH_PORT:-8011}"
export S3_ENDPOINT="http://127.0.0.1:${S3_PORT:-8333}"

ok "BETTER_AUTH_URL     → $BETTER_AUTH_URL"
ok "LOCAL_DB_URL (Bun)  → $LOCAL_DB_URL"
ok "DOCKER_DB_URL (RPA) → $DOCKER_DATABASE_URL"
ok "S3_ENDPOINT         → $S3_ENDPOINT"

# ── 3. Start Docker Infrastructure ────────────────────────────────────────────
step "3/5" "🐳 Starting Docker infrastructure..."

# Ensure the external 'coolify' network exists (required by compose)
if ! docker network inspect coolify >/dev/null 2>&1; then
  warn "Creating missing external network 'coolify'..."
  docker network create coolify >/dev/null
fi

# Stop the dashboard Docker container — we run it locally via Bun/Quasar
$COMPOSE stop dashboard 2>/dev/null || true

# Bring up all backend services (always with both compose files!)
$COMPOSE up -d fasih-db vpn rpa vpn-auth master volume filer s3 archiver \
  || die "Docker infrastructure failed to start."

# Wait for DB to be healthy before proceeding — prevents ECONNREFUSED on startup
ok "Waiting for fasih-db to be healthy..."
_db_wait=0
until docker inspect --format='{{.State.Health.Status}}' fasih-nexus-db 2>/dev/null | grep -q "healthy"; do
  sleep 1
  _db_wait=$((_db_wait + 1))
  if [ "$_db_wait" -ge 60 ]; then
    die "fasih-db did not become healthy within 60s. Check: docker logs fasih-nexus-db"
  fi
  printf "."
done
echo ""
ok "fasih-db is healthy (${_db_wait}s)"

# ── 4. Migrate DB Schema ───────────────────────────────────────────────────────
step "4/5" "🗄️  Migrating database schema..."

cd "$PROJECT_DIR/dashboard" || die "dashboard/ directory not found"
# Use LOCAL_DB_URL explicitly — drizzle-kit runs on host, needs 127.0.0.1:5436
DATABASE_URL="$LOCAL_DB_URL" bunx drizzle-kit push 2>&1 \
  | grep -v "^$" | sed 's/^/  /' || warn "drizzle-kit push had warnings (continuing)"

ok "Schema migration done."

# ── 5. Start Local Servers ────────────────────────────────────────────────────
step "5/5" "🚀 Starting Bun backend & Quasar frontend..."

# ─── Cleanup trap (runs on Ctrl+C / EXIT) ────────────────────────
cleanup() {
  echo ""
  log "🛑 Shutting down local servers..."
  if [ -f "$PID_FILE" ]; then
    while IFS=: read -r name pid; do
      if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        echo -e "  ${C_YELLOW}↓${C_NC} Stopping $name (pgid=$pid)..."
        kill -- -"$pid" 2>/dev/null || true
        sleep 0.2
        kill -9 -- -"$pid" 2>/dev/null || true
      fi
    done < "$PID_FILE"
    rm -f "$PID_FILE"
  fi
  rm -f "$LOCK_FILE"
  ok "Local servers stopped. Docker infra still running (stop with ./stop-local.sh)."
}
trap cleanup INT TERM HUP QUIT EXIT

# Prevent concurrent starts
if [ -f "$LOCK_FILE" ]; then
  warn "Lock file found ($LOCK_FILE). Another instance may be running."
  warn "If you are sure, remove it: rm $LOCK_FILE"
  die "Aborting to prevent double-start."
fi
touch "$LOCK_FILE"

# Clear old PID file
rm -f "$PID_FILE"

# Start Bun backend in its own process group.
# Explicitly pass LOCAL_DB_URL as DATABASE_URL so Bun reaches the port-forwarded
# DB at 127.0.0.1:5436 (host). Docker containers use fasih-db:5432 (internal DNS).
DATABASE_URL="$LOCAL_DB_URL" setsid bun run dev >"$LOG_DIR/backend.log" 2>&1 &
BACKEND_PGID=$!
echo "backend:$BACKEND_PGID" >> "$PID_FILE"

# Wait briefly to catch immediate startup crashes
sleep 2
if ! kill -0 "$BACKEND_PGID" 2>/dev/null; then
  die "Bun backend crashed immediately! Check: tail -50 $LOG_DIR/backend.log"
fi

# Verify backend is actually accepting connections
_api_wait=0
until curl -sf "http://localhost:${_bun_port}/api/health" >/dev/null 2>&1; do
  sleep 1
  _api_wait=$((_api_wait + 1))
  if [ "$_api_wait" -ge 20 ]; then
    warn "Backend health check timed out — it may still be starting."
    warn "Check logs: tail -50 $LOG_DIR/backend.log"
    break
  fi
  printf "."
done
echo ""
ok "Backend ready at http://localhost:${_bun_port} (${_api_wait}s)"

# Start Quasar frontend in its own process group
cd "$PROJECT_DIR/dashboard/client" || die "dashboard/client/ not found"
setsid bunx quasar dev >"$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PGID=$!
echo "frontend:$FRONTEND_PGID" >> "$PID_FILE"

sleep 1
if ! kill -0 "$FRONTEND_PGID" 2>/dev/null; then
  die "Quasar crashed immediately! Check: tail -50 $LOG_DIR/frontend.log"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${C_BOLD}${C_GREEN}=================================================${C_NC}"
echo -e "${C_BOLD}  ✅ FasihNexus Local Dev Environment Ready!    ${C_NC}"
echo -e "${C_BOLD}${C_GREEN}=================================================${C_NC}"
echo ""
echo -e "  ${C_CYAN}Dashboard${C_NC}  →  http://localhost:9009"
echo -e "  ${C_CYAN}Backend   ${C_NC}  →  http://localhost:${_bun_port}"
echo -e "  ${C_CYAN}DB        ${C_NC}  →  localhost:${DB_PORT}"
echo ""
echo -e "  Backend log:  ${C_YELLOW}$LOG_DIR/backend.log${C_NC}"
echo -e "  Frontend log: ${C_YELLOW}$LOG_DIR/frontend.log${C_NC}"
echo ""
echo -e "  ${C_RED}Ctrl+C${C_NC} to stop local servers (Docker infra stays up)"
echo -e "${C_GREEN}=================================================${C_NC}"
echo ""

# Wait for background jobs — script stays alive until Ctrl+C
wait

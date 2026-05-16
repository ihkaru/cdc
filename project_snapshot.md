# FasihNexus Architecture Snapshot
Generated at: Sat May 16 07:13:14 PM WIB 2026
Scope: Infrastructure, Entrypoints, and Critical Business Logic.

## 📂 High-Level Structure
```text
.
|____rpa
| |____src
| |____requirements.txt
| |____README.md
| |____config
| |____Dockerfile
| |____scripts
| |____venv
| |____tmp_explore_api.py
| |____tmp_test_users.py
| |____tmp_test_datatable.py
| |____tmp_test_survey.py
| |____check_counts.py
| |____check_counts_simple.py
| |____debug_metadata.py
| |____test_cookie.py
| |____portal_failure.html
| |____sso_redirect_failure.png
| |____portal_error.png
| |____sso_timeout.png
| |____sso_timeout.html
| |____scratch_test_refresh.py
| |____scratch_test_proxy.py
| |____scratch_test_s3_cookies.py
| |____monitor_bps_network.py
| |____test_s3_headers.py
|____dashboard
| |____server
| |____package.json
| |____tsconfig.json
| |____README.md
| |____Dockerfile
| |____client
| |____bun.lock
| |____drizzle.config.ts
| |____test_db.ts
| |____entrypoint.sh
|____n8n-workflows
| |____fasih_sync.json
|____vpn
| |____Dockerfile
| |____entrypoint.sh
|____new_vpn_cookie.txt
|____GEMINI.md
|____docs
| |____adr
| |____references
|____api_exploration.log
|____full_payload_dump.log
|____tmp
| |____routes.txt
|____archiver_logs.txt
|____failed_ids.txt
|____successfully_mirrored_ids.txt
|____test_copy.txt
|____rpa_logs_debug.txt
|____data_dump.txt
|____full_data_dump.txt
|____test.jpg
|____README.md
|____update_cookie.sql
|____project_snapshot.md
|____docker-compose.yml
|____analyze_repo.sh
|____start-local.sh
|____start-docker.sh
|____stop-all.sh
|____tmp_explore_api.py
|____grab_payload.py
|____fix_db_paths.py
|____query_stats.py
|____query_stats2.py
|____get_failed_8.py
|____query_status3.py
|____query_8.py
|____query_success_now.py
|____find_8.py
|____find_8_host.py
|____get_the_8.py
|____parse_host.py
|____benchmark_fasih.sh
|____update_cookie.py
|____check-health.sh
|____check-stability.sh
|____test-routine-sync.sh
|____benchmark_api.sh
|____docker-compose.coolify.yml
|____benchmark_ux_lookup.sh
|____scratch_benchmark.py
|____artifacts
| |____portal_initial.png
| |____portal_failure.png
| |____portal_failure.html
| |____portal_failure_v14.png
| |____portal_failure_v14.html
| |____portal_initial_v15.png
| |____portal_failure_v15.png
| |____portal_failure_v15.html
|____debug_assignment.json
|____docker-compose.local.yml
|____dump_project.sh
```

## 🐳 Docker & Infrastructure (The Foundation)
### ./docker-compose.yml
```yaml
services:
  # --- UI & API Gateway (The Bridge) ---
  dashboard:
    build: ./dashboard
    container_name: fasih-nexus-dashboard
    networks:
      - fasih_internal
      - coolify
    labels:
      - "traefik.enable=true"
      - "traefik.docker.network=coolify"
      - "coolify.managed=true"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - RPA_URL=http://vpn:8000
      - VPN_AUTH_URL=http://vpn:8001
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      - BETTER_AUTH_SECRET=${BETTER_AUTH_SECRET}
      - BETTER_AUTH_URL=${BETTER_AUTH_URL}
      - PUBLIC_BASE_URL=${PUBLIC_BASE_URL}
      - VPN_USER=${VPN_USER}
      - VPN_PASS=${VPN_PASS}
    depends_on:
      fasih-db:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "bun -e \"fetch('http://127.0.0.1:3000/api/health').then(r => r.ok ? process.exit(0) : process.exit(1))\""]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 15s
    restart: unless-stopped

  # --- VPN Gateway (Network Owner) ---
  vpn:
    build: ./vpn
    container_name: fasih-nexus-vpn
    privileged: true
    devices:
      - /dev/net/tun
      - /dev/ppp
    dns:
      - 127.0.0.11
      - 172.16.2.2
      - 172.16.2.3
      - 8.8.8.8
    networks:
      - fasih_internal
    labels:
      - "coolify.managed=false"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - VPN_HOST=akses.bps.go.id
      - VPN_TEST_URL=https://fasih-sm.bps.go.id
      - VPN_TRUSTED_CERT=${VPN_TRUSTED_CERT}
      - VPN_USER=${VPN_USER}
      - VPN_PASS=${VPN_PASS}
      - VPN_COOKIE=${VPN_COOKIE}
    extra_hosts:
      - "fasih-sm.bps.go.id:10.1.110.13"
    depends_on:
      fasih-db:
        condition: service_healthy
      s3:
        condition: service_started
    healthcheck:
      test: [ "CMD-SHELL", "curl -fks --connect-timeout 15 https://fasih-sm.bps.go.id/oauth_login.html -o /dev/null && echo ok || exit 1" ]
      interval: 45s
      timeout: 20s
      retries: 5
      start_period: 60s
    restart: unless-stopped
    stop_grace_period: 15s

  # --- RPA Engines (Sharing VPN Namespace) ---
  rpa:
    build: ./rpa
    image: fasih-nexus-rpa:latest
    container_name: fasih-nexus-rpa
    network_mode: "service:vpn"
    labels:
      - "coolify.managed=false"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      - PYTHONPATH=/app:/app/src
      - SKIP_DETAIL_FETCH=${SKIP_DETAIL_FETCH:-false}
      - FASIH_CONCURRENCY=${FASIH_CONCURRENCY:-3}
      - FETCH_CONCURRENCY=${FETCH_CONCURRENCY:-3}
      - TARGET_URL=${TARGET_URL:-https://fasih-sm.bps.go.id}
      - VPN_USER=${VPN_USER}
      - VPN_PASS=${VPN_PASS}
    depends_on:
      vpn:
        condition: service_started
    command: sh -c "echo '10.1.110.13 fasih-sm.bps.go.id' >> /etc/hosts && python -m uvicorn src.app:app --host 0.0.0.0 --port 8000"
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=15)\""]
      interval: 45s
      timeout: 20s
      retries: 5
    restart: unless-stopped

  vpn-auth:
    image: fasih-nexus-rpa:latest
    container_name: fasih-nexus-vpn-auth
    network_mode: "service:vpn"
    labels:
      - "coolify.managed=false"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    depends_on:
      vpn:
        condition: service_started
      rpa:
        condition: service_started
    command: sh -c "echo '10.1.110.13 fasih-sm.bps.go.id' >> /etc/hosts && python -m uvicorn src.app:app --host 0.0.0.0 --port 8001"
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=5)\""]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  archiver:
    image: fasih-nexus-rpa:latest
    container_name: fasih-nexus-archiver
    network_mode: "service:vpn"
    labels:
      - "coolify.managed=false"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - S3_ACCESS_KEY=${S3_ACCESS_KEY:-fasihadmin}
      - S3_SECRET_KEY=${S3_SECRET_KEY:-fasihsecret}
      - S3_BUCKET=${S3_BUCKET:-survey-images}
      - S3_ENDPOINT=http://s3:8333
      - PYTHONPATH=/app:/app/src
    depends_on:
      vpn:
        condition: service_started
      rpa:
        condition: service_started
    command: python src/archiver.py
    restart: unless-stopped

  # --- Data Persistence ---
  fasih-db:
    image: postgres:16-alpine
    container_name: fasih-nexus-db
    networks:
      - fasih_internal
    labels:
      - "coolify.managed=false"
    volumes:
      - pg_data_v3:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: fasih
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: fasih_dashboard
      POSTGRES_HOST_AUTH_METHOD: trust
    healthcheck:
      test: [ "CMD-SHELL", "pg_isready -U fasih -d fasih_dashboard" ]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # --- SeaweedFS Stack ---
  master:
    image: chrislusf/seaweedfs:latest
    command: "master -ip=master"
    networks:
      - fasih_internal
    labels:
      - "coolify.managed=false"
    restart: unless-stopped

  volume:
    image: chrislusf/seaweedfs:latest
    command: "volume -mserver=master:9333 -port=8080 -dir=/data"
    networks:
      - fasih_internal
    labels:
      - "coolify.managed=false"
    depends_on:
      - master
    volumes:
      - seaweed_data:/data
    restart: unless-stopped

  filer:
    image: chrislusf/seaweedfs:latest
    command: 'filer -master=master:9333'
    networks:
      - fasih_internal
    labels:
      - "coolify.managed=false"
    depends_on:
      - master
      - volume
      - fasih-db
    environment:
      - WEED_FILER_POSTGRES_ENABLED=true
      - WEED_FILER_POSTGRES_HOSTNAME=fasih-db
      - WEED_FILER_POSTGRES_PORT=5432
      - WEED_FILER_POSTGRES_USERNAME=fasih
      - WEED_FILER_POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - WEED_FILER_POSTGRES_DATABASE=fasih_dashboard
      - WEED_FILER_POSTGRES_SSLMODE=disable
    restart: unless-stopped

  s3:
    image: chrislusf/seaweedfs:latest
    container_name: fasih-nexus-s3
    command: "s3 -filer=filer:8888"
    networks:
      - fasih_internal
    labels:
      - "coolify.managed=false"
    environment:
      - SEAWEEDFS_S3_ACCESS_KEY=${S3_ACCESS_KEY:-fasihadmin}
      - SEAWEEDFS_S3_SECRET_KEY=${S3_SECRET_KEY:-fasihsecret}
    depends_on:
      - filer
    restart: unless-stopped

networks:
  fasih_internal:
    driver: bridge
  coolify:
    external: true

volumes:
  pg_data_v3:
  seaweed_data:
```

### ./analyze_repo.sh
```yaml
#!/bin/bash

# Array direktori yang akan di-exclude, disatukan jadi pipe untuk tree dan find
TARGET_DIR="."
EXCLUDES="node_modules|dist|.git|.vuepress|.quasar|vendor|__pycache__|.env|.venv|venv|out|.turbo|.next|coverage|data"

echo "================================================="
echo "📁 REPOSITORY STRUCTURE (excluding build/modules)"
echo "================================================="
if command -v tree &> /dev/null; then
  # Use tree with -h (size) or alternatively pipe to awk, but doing this natively is hard.
  # We will use a custom find approach for both since the user specifically requested *line counts*, 
  # which `tree` does not natively support (it only supports file sizes).
  
  # Recursive function to print tree with line counts
  export EXCLUDES
  print_tree() {
    local dir="$1"
    local prefix="$2"
    
    # Get items, ignoring excluded dirs
    local items=($(ls -A "$dir" 2>/dev/null | grep -Ev "^(${EXCLUDES})$"))
    local count=${#items[@]}
    
    for ((i=0; i<count; i++)); do
      local item="${items[$i]}"
      local path="$dir/$item"
      local is_last=$((i == count - 1))
      
      local branch="├── "
      local next_prefix="$prefix│   "
      if [ "$is_last" -eq 1 ]; then
        branch="└── "
        next_prefix="$prefix    "
      fi
      
      if [ -d "$path" ]; then
        echo "${prefix}${branch}${item}/"
        print_tree "$path" "$next_prefix"
      elif [ -f "$path" ]; then
        local lines=$(wc -l < "$path" 2>/dev/null || echo "?")
        echo "${prefix}${branch}${item} (${lines} lines)"
      fi
    done
  }
  
  echo "."
  print_tree "$TARGET_DIR" ""
else
  # Mocking tree using find
  find "$TARGET_DIR" -type d -regextype posix-extended -regex ".*/($EXCLUDES).*" -prune -o -print | while read -r filepath; do
    if [ -f "$filepath" ]; then
      lines=$(wc -l < "$filepath" 2>/dev/null || echo "?")
      echo "$filepath ($lines lines)" | sed -e 's;[^/]*/;|____;g;s;____|; |;g'
    else
      echo "$filepath" | sed -e 's;[^/]*/;|____;g;s;____|; |;g'
    fi
  done
fi

echo ""
echo "================================================="
echo "🗄️ LARGE FILES (>400 LINES)"
echo "================================================="
echo "Finding files..."

# Mencari seluruh file, mengecualikan folder-folder berat
find "$TARGET_DIR" \
    -type d -regextype posix-extended -regex ".*/($EXCLUDES).*" -prune \
    -o -type f -not -name "package*.json" -not -name "*bun.lock*" -not -name "yarn.lock" -not -name "pnpm-lock.yaml" -print0 | xargs -0 -I{} wc -l "{}" 2>/dev/null | \
    awk '$1 > 400 && $2 != "total" {print $0}' | \
    sort -nr | \
    awk '{printf "\033[31m[%d lines]\033[0m %s\n", $1, $2}'

echo "================================================="
echo "✅ Analysis Complete."
```

### ./start-local.sh
```yaml
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
# Using -f docker-compose.yml -f docker-compose.local.yml to ensure local volumes are mounted
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d fasih-db vpn rpa vpn-auth master volume filer s3 archiver || { echo "❌ Infra failed to start. Aborting."; exit 1; }


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

  # Override DATABASE_URL to use 127.0.0.1 instead of docker alias
  # Using 127.0.0.1 to avoid Docker IPv6 vs IPv4 binding mismatches
  LOCAL_DB_URL=$(echo "$DATABASE_URL" | sed -E 's/@(postgres|fasih-db):/@127.0.0.1:/')
  export DATABASE_URL="$LOCAL_DB_URL"
  echo "      DB URL overridden for local access: $DATABASE_URL"

  # RPA runs inside Docker (network_mode: service:vpn), accessible on 127.0.0.1:8000
  export RPA_URL="http://127.0.0.1:8000"
  export VPN_AUTH_URL="http://127.0.0.1:8001"

  # S3 endpoint override for local dashboard access
  export S3_ENDPOINT="http://127.0.0.1:8333"
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
```

### ./start-docker.sh
```yaml
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
```

### ./stop-all.sh
```yaml
#!/bin/bash
# stop-all.sh - Clean Teardown of Docker and Local Servers
# Reads PID files first for precise cleanup, falls back to pkill as safety net.

echo "================================================="
echo " Stopping All Environments (Docker & Local Tools)"
echo "================================================="

PID_DIR="/tmp/fasih-nexus-local"

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
pkill -f "server/index.ts" 2>/dev/null || true
pkill -f "elysia" 2>/dev/null || true

# ─── Step 3: Stop Docker containers ────────────────────────────
echo "[3/3] Stopping Docker services..."
docker compose down

echo "-------------------------------------------------"
echo " ✅ Everything has been stopped gracefully."
echo "     Ready for a fresh start!"
echo "-------------------------------------------------"
```

### ./benchmark_fasih.sh
```yaml
#!/usr/bin/env bash
# Script wrapper benchmark kecepatan penarikan data dari FASIH-SM.
# Dijalankan di dalam container Docker cdc-rpa agar memanfaatkan tunnel VPN yang aktif.
# Sesuai pedoman operasional BPS Rule #7 (wajib menyertakan -w /app/src).

set -e

echo "======================================================================"
echo " MENGINISIASI PROSES BENCHMARK DATA FASIH-SM VIA VPN CONTAINER        "
echo "======================================================================"

# Memeriksa apakah container fasih-nexus-rpa sedang aktif
if ! docker ps --format '{{.Names}}' | grep -q "^fasih-nexus-rpa$"; then
    echo "❌ Error: Container 'fasih-nexus-rpa' tidak terdeteksi aktif."
    echo "Pastikan sistem layanan sync sudah berjalan (misal via ./start-docker.sh atau ./start-local.sh)."
    exit 1
fi

echo "📦 Menyalin script benchmark dan api_client terbaru ke dalam container fasih-nexus-rpa (tanpa rebuild)..."
docker cp rpa/src/benchmark_api.py fasih-nexus-rpa:/app/src/benchmark_api.py
docker cp rpa/src/api_client.py fasih-nexus-rpa:/app/src/api_client.py
docker cp rpa/src/main.py fasih-nexus-rpa:/app/src/main.py
docker cp rpa/src/worker/full_mode.py fasih-nexus-rpa:/app/src/worker/full_mode.py

echo "🚀 Mengirim perintah eksekusi ke dalam container fasih-nexus-rpa..."
# Menjalankan tanpa flag -t agar aman dieksekusi di background/CI pipeline tanpa error TTY
docker exec -w /app/src fasih-nexus-rpa python benchmark_api.py
```

### ./check-health.sh
```yaml
#!/bin/bash
# FasihNexus Pre-Flight Validator (Health Check)
# Digunakan untuk memastikan kode siap deploy ke Coolify/Production.

set -e

# Warna untuk output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}      FasihNexus - Pre-Flight Validator          ${NC}"
echo -e "${BLUE}=================================================${NC}"

# 1. Validasi Environment File
echo -n "[1/4] Checking .env integrity... "
if [ ! -f .env ]; then
    echo -e "${RED}FAILED${NC}"
    echo "      Error: .env file missing. Please copy from .env.example"
    exit 1
fi
# Cek apakah variabel kritikal ada isinya
MISSING_VARS=0
check_var() {
    if ! grep -q "^$1=" .env || grep -q "^$1=[[:space:]]*$" .env; then
        echo -e "\n      ${RED}⚠️  Warning: $1 is empty or missing in .env${NC}"
        MISSING_VARS=$((MISSING_VARS + 1))
    fi
}
check_var "BETTER_AUTH_SECRET"
check_var "ENCRYPTION_KEY"
check_var "DATABASE_URL"

if [ $MISSING_VARS -eq 0 ]; then echo -e "${GREEN}OK${NC}"; else echo -e "      Status: ${RED}Incomplete${NC}"; fi

# 2. Validasi Docker Compose
echo -n "[2/4] Validating Docker Compose schema... "
if docker compose config > /dev/null 2>&1; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
    docker compose config
    exit 1
fi

# 3. Type-Check Backend (Elysia)
echo -e "[3/4] Running TypeScript check on Server (Backend)... "
cd dashboard/server
if bun x tsc --noEmit; then
    echo -e "      ${GREEN}Backend Types OK${NC}"
else
    echo -e "      ${RED}Backend Type Errors Detected${NC}"
    exit 1
fi
cd ../..

# 4. Type-Check Frontend (Quasar/Vue)
echo -e "[4/4] Running TypeScript check on Client (Frontend)... "
cd dashboard/client
# Menggunakan vue-tsc untuk validasi template Vue + TS
if bun x vue-tsc --noEmit; then
    echo -e "      ${GREEN}Frontend Types OK${NC}"
else
    echo -e "      ${RED}Frontend Type Errors Detected${NC}"
    exit 1
fi
cd ../..

echo -e "${BLUE}=================================================${NC}"
echo -e "${GREEN}✅ PASSED: FasihNexus is ready for deployment!${NC}"
echo -e "${BLUE}=================================================${NC}"
```

### ./check-stability.sh
```yaml
#!/bin/bash

# =================================================
#      FasihNexus - Stability & Health Checker
# =================================================
# This script simulates Traefik's routing logic by 
# verifying Docker Health status and connectivity.

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🔍 Starting Stability Audit...${NC}"

# 1. Wait and Check Docker Health Status (The Traefik "Golden Rule")
SERVICES=("fasih-nexus-db" "fasih-nexus-vpn" "fasih-nexus-rpa" "fasih-nexus-dashboard")
MAX_RETRIES=12
RETRY_COUNT=0
echo -e "${YELLOW}⏳ Waiting for all services to become HEALTHY...${NC}"

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    STILL_STARTING=false
    for service in "${SERVICES[@]}"; do
        HEALTH=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "$service" 2>/dev/null)
        if [ "$HEALTH" == "starting" ]; then
            STILL_STARTING=true
            break
        fi
    done

    if [ "$STILL_STARTING" = false ]; then
        break
    fi

    echo -ne "   ...waiting for startup (${RETRY_COUNT}/${MAX_RETRIES})\r"
    sleep 5
    RETRY_COUNT=$((RETRY_COUNT+1))
done
echo -e "\n"

ALL_HEALTHY=true
for service in "${SERVICES[@]}"; do
    STATE=$(docker inspect --format='{{.State.Status}}' "$service" 2>/dev/null)
    HEALTH=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "$service" 2>/dev/null)
    
    if [ -z "$STATE" ] || [ "$STATE" != "running" ]; then
        echo -e "${RED}❌ $service: NOT RUNNING (Status: ${STATE:-missing})${NC}"
        ALL_HEALTHY=false
    elif [ "$HEALTH" == "unhealthy" ] || ([ "$service" == "fasih-nexus-vpn" ] && [ "$HEALTH" == "starting" ] && [ $RETRY_COUNT -eq $MAX_RETRIES ]); then
        if [ "$service" == "fasih-nexus-vpn" ]; then
            echo -e "${YELLOW}⚠️ $service: Detected GHOST SESSION or CONNECTION FAILURE.${NC}"
            echo -e "${YELLOW}🛠️  Attempting Self-Healing (Auto-fetching fresh SAML cookie)...${NC}"
            
            # Load credentials from .env
            VPN_USER=$(grep VPN_USER .env | cut -d '=' -f2)
            VPN_PASS=$(grep VPN_PASS .env | cut -d '=' -f2)
            
            if [ -n "$VPN_USER" ] && [ -n "$VPN_PASS" ]; then
                # Trigger RPA Auto-Fetch (vpn-auth runs on port 8000)
                RESP=$(curl -s -X POST http://127.0.0.1:8000/vpn/auto-fetch \
                    -H "Content-Type: application/json" \
                    -d "{\"sso_username\":\"$VPN_USER\", \"sso_password\":\"$VPN_PASS\"}")
                
                if echo "$RESP" | grep -q "success"; then
                    echo -e "${GREEN}✅ Auto-fetch success! VPN will reconnect shortly via DB trigger.${NC}"
                    echo -e "${YELLOW}⏳ Waiting 15s for reconnection...${NC}"
                    sleep 15
                    # Re-check status once
                    HEALTH=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "$service" 2>/dev/null)
                    if [ "$HEALTH" == "healthy" ]; then
                        echo -e "${GREEN}✅ $service: RECOVERED & HEALTHY${NC}"
                        continue
                    fi
                else
                    echo -e "${RED}❌ Auto-fetch failed: $RESP${NC}"
                fi
            else
                echo -e "${RED}❌ Self-healing skipped: VPN_USER/PASS not found in .env${NC}"
            fi
        fi
        
        echo -e "${RED}❌ $service: $HEALTH (Traefik will DROP traffic!)${NC}"
        ALL_HEALTHY=false
    elif [ "$HEALTH" == "starting" ]; then
        echo -e "${RED}❌ $service: TIMEOUT (Still starting after 60s)${NC}"
        ALL_HEALTHY=false
    elif [ "$HEALTH" == "no-healthcheck" ]; then
        echo -e "${GREEN}✅ $service: Running (No explicit healthcheck defined)${NC}"
    else
        echo -e "${GREEN}✅ $service: HEALTHY${NC}"
    fi
done

# 3. Network Connectivity Check (Simulation of Real Traffic)
echo -e "\n${YELLOW}🌐 Simulating Traffic Routing...${NC}"

# Dashboard API Health (with retry)
DASHBOARD_OK=false
for i in {1..5}; do
    if curl -s -f http://127.0.0.1:3000/api/health > /dev/null; then
        DASHBOARD_OK=true
        break
    fi
    sleep 2
done

if [ "$DASHBOARD_OK" = true ]; then
    echo -e "${GREEN}✅ Dashboard API: Reachable at port 3000${NC}"
else
    echo -e "${RED}❌ Dashboard API: Failed to respond at port 3000${NC}"
    ALL_HEALTHY=false
fi

# RPA API Health (with retry)
RPA_OK=false
for i in {1..5}; do
    if curl -s -f http://127.0.0.1:8000/health > /dev/null; then
        RPA_OK=true
        break
    fi
    sleep 2
done

if [ "$RPA_OK" = true ]; then
    echo -e "${GREEN}✅ RPA Sync Engine: Reachable at port 8000${NC}"
else
    echo -e "${RED}❌ RPA Sync Engine: Failed to respond at port 8000${NC}"
    ALL_HEALTHY=false
fi

# 4. Final Verdict
echo -e "\n================================================="
if [ "$ALL_HEALTHY" = true ]; then
    echo -e "${GREEN}✅ STABILITY VERIFIED: All systems are green.${NC}"
    exit 0
else
    echo -e "${RED}❌ STABILITY FAILED: Fix the issues above before push!${NC}"
    exit 1
fi
```

### ./test-routine-sync.sh
```yaml
#!/bin/bash
# test-routine-sync.sh
# Script to verify the Routine Sync Scheduler functionality.

DB_CONTAINER="fasih-nexus-db"
DB_USER="fasih"
DB_NAME="fasih_dashboard"

echo "🚀 Starting Routine Sync Test..."

# 1. Rebuild and Restart RPA to apply changes
echo "🔄 Rebuilding RPA service..."
docker compose up -d --build rpa

# 2. Wait for VPN to stabilize
echo "⏳ Waiting for VPN to stabilize..."
MAX_RETRIES=20
for i in $(seq 1 $MAX_RETRIES); do
    if docker logs fasih-nexus-vpn 2>&1 | grep -q "Connected to gateway"; then
        echo "✅ VPN appears to be connected."
        # Extra wait for DNS/Routing
        sleep 10
        break
    fi
    echo "   waiting for VPN... ($i/$MAX_RETRIES)"
    sleep 5
done

# 3. Pick a survey and set interval to 1 minute
SURVEY_ID=$(docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -t -A -c "SELECT id FROM survey_configs WHERE is_active = true LIMIT 1;")
SURVEY_NAME=$(docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -t -A -c "SELECT survey_name FROM survey_configs WHERE id = '$SURVEY_ID';")

if [ -z "$SURVEY_ID" ]; then
    echo "❌ No active survey found to test."
    exit 1
fi

echo "📋 Testing with survey: $SURVEY_NAME ($SURVEY_ID)"
echo "⏱️ Setting interval to 1 minute..."
docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "UPDATE survey_configs SET interval_minutes = 1 WHERE id = '$SURVEY_ID';"

# 4. Get latest sync log ID before waiting
LAST_LOG_ID=$(docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -t -A -c "SELECT MAX(id) FROM sync_logs WHERE survey_config_id = '$SURVEY_ID';")
echo "🔍 Last Log ID before test: ${LAST_LOG_ID:-None}"

# 5. Wait for the scheduler (Scheduler waits 30s on startup + check every 60s)
echo "⏳ Waiting 120 seconds for scheduler to trigger..."
sleep 120

# 6. Check if a new log appeared
NEW_LOG=$(docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -t -A -c "SELECT id, status, notes FROM sync_logs WHERE survey_config_id = '$SURVEY_ID' AND id > '${LAST_LOG_ID:-0}' AND notes LIKE '%Automated routine sync%' ORDER BY id DESC LIMIT 1;")

if [ -n "$NEW_LOG" ]; then
    echo "✅ SUCCESS! Routine sync triggered."
    echo "📄 Log Detail: $NEW_LOG"
else
    echo "❌ FAILURE! Routine sync not triggered."
    echo "📝 Checking RPA logs for errors..."
    docker logs fasih-nexus-rpa | grep -i "scheduler" | tail -n 20
fi

# 6. Cleanup: Revert interval
echo "🧹 Cleaning up: Reverting interval to 30 minutes..."
docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "UPDATE survey_configs SET interval_minutes = 30 WHERE id = '$SURVEY_ID';"

echo "🏁 Test finished."
```

### ./benchmark_api.sh
```yaml
#!/bin/bash

# ==========================================================
# FasihNexus API Benchmark Tool
# Mengukur performa end-to-end dari Dashboard ke Robot RPA
# ==========================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}       FasihNexus API Performance Audit          ${NC}"
echo -e "${BLUE}=================================================${NC}"

# 1. Test Dashboard Base Latency (Bun/Elysia)
echo -ne "🚀 [1/3] Dashboard Base Latency... "
START=$(date +%s%N)
curl -s -o /dev/null http://127.0.0.1:9000/api/surveys/vpn/status
END=$(date +%s%N)
DIFF=$((($END - $START)/1000000))
echo -e "${GREEN}${DIFF}ms${NC}"

# 2. Test VPN Tunnel Latency (Direct to FASIH-SM via RPA Proxy)
echo -ne "🔒 [2/3] VPN Tunnel Reachability... "
START=$(date +%s%N)
curl -s -o /dev/null http://127.0.0.1:8000/vpn/check
END=$(date +%s%N)
DIFF=$((($END - $START)/1000000))
if [ $DIFF -lt 2000 ]; then
    echo -e "${GREEN}${DIFF}ms (Fast)${NC}"
else
    echo -e "${YELLOW}${DIFF}ms (High Latency - VPN Bottleneck?)${NC}"
fi

# 3. Test Metadata Lookup (Playwright SSO Flow)
echo -e "${YELLOW}🤖 [3/3] RPA Metadata Lookup (SSO Login Flow)...${NC}"
echo -e "   (Ini akan memakan waktu 15-45 detik karena robot harus login SSO)"

# Membaca kredensial dari .env jika ada untuk simulasi
SSO_USER=$(grep SSO_USER .env | cut -d '=' -f2 | xargs)
SSO_PASS=$(grep SSO_PASS .env | cut -d '=' -f2 | xargs)

if [ -z "$SSO_USER" ]; then
    echo -e "${RED}   Gagal: SSO_USER tidak ditemukan di .env. Lewati tes lookup.${NC}"
else
    START_LOOKUP=$(date +%s)
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST http://127.0.0.1:8000/lookup/metadata \
        -H "Content-Type: application/json" \
        -d "{\"sso_username\": \"$SSO_USER\", \"sso_password\": \"$SSO_PASS\"}")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
    END_LOOKUP=$(date +%s)
    DURATION=$((END_LOOKUP - START_LOOKUP))

    if [ "$HTTP_CODE" == "200" ]; then
        echo -e "${GREEN}   ✅ Success in ${DURATION}s${NC}"
    else
        echo -e "${RED}   ❌ Failed with code ${HTTP_CODE} in ${DURATION}s${NC}"
    fi
fi

echo -e "${BLUE}=================================================${NC}"
echo -e "Audit Selesai."
```

### ./docker-compose.coolify.yml
```yaml
# FasihNexus - Coolify Production Stack
# This configuration solves the network_mode vs networks conflict and ensures 
# deterministic Traefik routing.

services:
  # --- UI & API Gateway ---
  dashboard:
    build: ./dashboard
    container_name: fasih-nexus-dashboard
    networks:
      - fasih_internal
      - coolify
    labels:
      - "traefik.enable=true"
      - "traefik.docker.network=coolify" # FORCE Traefik to use the public network IP
      # Note: Route rules and SSL will be automatically handled by Coolify UI
    environment:
      - DATABASE_URL=postgres://fasih:${POSTGRES_PASSWORD}@fasih-db:5432/fasih_dashboard
      - RPA_URL=http://vpn:8000        # Talking to RPA via VPN container
      - VPN_AUTH_URL=http://vpn:8001   # Talking to VPN-Auth via VPN container
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      - BETTER_AUTH_SECRET=${BETTER_AUTH_SECRET}
      - BETTER_AUTH_URL=${BETTER_AUTH_URL}
      - PUBLIC_BASE_URL=${PUBLIC_BASE_URL}
      - S3_ACCESS_KEY=${S3_ACCESS_KEY:-fasihadmin}
      - S3_SECRET_KEY=${S3_SECRET_KEY:-fasihsecret}
      - S3_BUCKET=${S3_BUCKET:-survey-images}
      - S3_ENDPOINT=http://s3:8333
    depends_on:
      fasih-db:
        condition: service_healthy
    restart: unless-stopped

  # --- VPN Gateway (The black box) ---
  vpn:
    build: ./vpn
    container_name: fasih-nexus-vpn
    privileged: true
    devices:
      - /dev/net/tun
      - /dev/ppp
    networks:
      - fasih_internal # Isolated from Coolify/Traefik
    environment:
      - DATABASE_URL=postgres://fasih:${POSTGRES_PASSWORD}@fasih-db:5432/fasih_dashboard
      - VPN_HOST=akses.bps.go.id
      - VPN_TEST_URL=https://fasih-sm.bps.go.id
      - VPN_USER=${VPN_USER}
      - VPN_PASS=${VPN_PASS}
      - VPN_COOKIE=${VPN_COOKIE}
    depends_on:
      fasih-db:
        condition: service_healthy
    extra_hosts:
      - "fasih-sm.bps.go.id:10.1.110.13"
    healthcheck:
      test: [ "CMD-SHELL", "curl -fks --connect-timeout 15 https://fasih-sm.bps.go.id/oauth_login.html -o /dev/null && echo ok || exit 1" ]
      interval: 45s
      timeout: 20s
      retries: 5
      start_period: 60s
    restart: unless-stopped

  # --- RPA Engines (Behind VPN) ---
  rpa:
    build: ./rpa
    container_name: fasih-nexus-rpa
    network_mode: "service:vpn" # Attached to VPN network stack
    environment:
      - DATABASE_URL=postgres://fasih:${POSTGRES_PASSWORD}@fasih-db:5432/fasih_dashboard
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      - PYTHONPATH=/app:/app/src
    depends_on:
      vpn:
        condition: service_started
    restart: unless-stopped

  vpn-auth:
    image: fasih-nexus-rpa:latest
    container_name: fasih-nexus-vpn-auth
    network_mode: "service:vpn" # Also behind VPN for SSO reliability
    environment:
      - DATABASE_URL=postgres://fasih:${POSTGRES_PASSWORD}@fasih-db:5432/fasih_dashboard
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      - PYTHONPATH=/app:/app/src
    depends_on:
      vpn:
        condition: service_started
    command: python -m uvicorn src.app:app --host 0.0.0.0 --port 8001
    restart: unless-stopped

  archiver:
    image: fasih-nexus-rpa:latest
    container_name: fasih-nexus-archiver
    network_mode: "service:vpn"
    environment:
      - DATABASE_URL=postgres://fasih:${POSTGRES_PASSWORD}@fasih-db:5432/fasih_dashboard
      - S3_ACCESS_KEY=${S3_ACCESS_KEY:-fasihadmin}
      - S3_SECRET_KEY=${S3_SECRET_KEY:-fasihsecret}
      - S3_ENDPOINT=http://s3:8333
      - PYTHONPATH=/app:/app/src
    depends_on:
      vpn:
        condition: service_started
    command: python src/archiver.py
    restart: unless-stopped

  # --- Data Persistence ---
  fasih-db:
    image: postgres:16-alpine
    container_name: fasih-nexus-db
    networks:
      - fasih_internal
    volumes:
      - pg_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=fasih
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=fasih_dashboard
    healthcheck:
      test: [ "CMD-SHELL", "pg_isready -U fasih -d fasih_dashboard" ]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # --- SeaweedFS Stack ---
  master:
    image: chrislusf/seaweedfs:latest
    command: "master -ip=master"
    networks:
      - fasih_internal
    restart: unless-stopped

  volume:
    image: chrislusf/seaweedfs:latest
    command: "volume -mserver=master:9333 -port=8080 -dir=/data"
    networks:
      - fasih_internal
    depends_on:
      - master
    volumes:
      - seaweed_data:/data
    restart: unless-stopped

  filer:
    image: chrislusf/seaweedfs:latest
    command: 'filer -master=master:9333'
    networks:
      - fasih_internal
    depends_on:
      - master
      - volume
      - fasih-db
    environment:
      - WEED_FILER_POSTGRES_ENABLED=true
      - WEED_FILER_POSTGRES_HOSTNAME=fasih-db
      - WEED_FILER_POSTGRES_PORT=5432
      - WEED_FILER_POSTGRES_USERNAME=fasih
      - WEED_FILER_POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - WEED_FILER_POSTGRES_DATABASE=fasih_dashboard
      - WEED_FILER_POSTGRES_SSLMODE=disable
    restart: unless-stopped

  s3:
    image: chrislusf/seaweedfs:latest
    command: "s3 -filer=filer:8888"
    networks:
      - fasih_internal
    environment:
      - SEAWEEDFS_S3_ACCESS_KEY=${S3_ACCESS_KEY:-fasihadmin}
      - SEAWEEDFS_S3_SECRET_KEY=${S3_SECRET_KEY:-fasihsecret}
    depends_on:
      - filer
    restart: unless-stopped

networks:
  fasih_internal:
    driver: bridge
  coolify:
    external: true

volumes:
  pg_data:
  seaweed_data:
```

### ./benchmark_ux_lookup.sh
```yaml
#!/bin/bash

# RPA berbagi network dengan container VPN (network_mode: service:vpn)
# Port 8000 tidak di-expose ke host — akses lewat IP VPN container di Docker bridge network
API_URL="http://172.18.0.5:8000/lookup/metadata"
# Membaca kredensial dari .env (pastikan file .env ada di direktori root)
SSO_USER="ihzakarunia@bps.go.id"
SSO_PASS='Fikrizaki2!'

echo "================================================="
echo "   FasihNexus UX Benchmark: RCA Transparent Mode "
echo "================================================="
echo "👤 User: $SSO_USER"
echo "-------------------------------------------------"

run_benchmark() {
    local label=$1
    echo "🚀 Running Request: $label..."
    
    # Capture response and time
    start_time=$(date +%s%N)
    response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL" \
        -H "Content-Type: application/json" \
        -d "{\"sso_username\": \"$SSO_USER\", \"sso_password\": \"$SSO_PASS\"}")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    end_time=$(date +%s%N)
    
    duration_ms=$(( (end_time - start_time) / 1000000 ))

    if [ "$http_code" -eq 200 ]; then
        echo "✅ SUCCESS in ${duration_ms}ms"
        
        # Extract timings using jq if available, else raw
        if command -v jq >/dev/null 2>&1; then
            echo "--- RCA Breakdown ---"
            echo "$body" | jq -r '.debug_timings | to_entries | .[] | "📍 \(.key): \(.value)ms"'
            is_cache=$(echo "$body" | jq -r '.debug_timings.cache_hit')
            if [ "$is_cache" == "true" ]; then
                echo "✨ RESULT: CACHE HIT (Premium UX)"
            else
                echo "❄️  RESULT: COLD START (Browser Required)"
            fi
        else
            echo "Body: $body"
        fi
    else
        echo "❌ FAILED with Status: $http_code"
        echo "Error: $body"
    fi
    echo "-------------------------------------------------"
}

# 1. Cold Start
run_benchmark "1. COLD START (Fresh Session)"

# 2. Warm Start
echo "⏳ Waiting 2 seconds for DB stability..."
sleep 2
run_benchmark "2. WARM START (Cached Session)"

# 3. Concurrent Check
echo "🔥 Stress Test: Concurrent Request..."
run_benchmark "3. REPEAT (Consistency Check)"

echo "Done."
```

### ./docker-compose.local.yml
```yaml
# This file is automatically merged with docker-compose.yml by Docker.
# It contains local development specific configurations (ports, volumes, etc.)

services:
  dashboard:
    ports:
      - "3000:3000"
    volumes:
      - ./dashboard/server:/app/server
      - ./dashboard/entrypoint.sh:/app/entrypoint.sh

  rpa:
    volumes:
      - ./rpa:/app

  vpn-auth:
    volumes:
      - ./rpa:/app

  archiver:
    volumes:
      - ./rpa:/app

  vpn:
    # Exposed ports here are actually serving rpa (8000) and vpn-auth (8001)
    # because they share the vpn container's network namespace.
    ports:
      - "8000:8000"
      - "8001:8001"

  fasih-db:
    ports:
      - "5432:5432"

  master:
    ports:
      - "9333:9333"

  s3:
    ports:
      - "8333:8333"

```

### ./dump_project.sh
```yaml
#!/bin/bash
# dump_project.sh - Highly Optimized Snapshot (Architecture & Core Logic Only)
# This version avoids bloating the context with repetitive or non-essential code.

OUTPUT_FILE="project_snapshot.md"
TARGET_DIR="."

# Strict exclusion pattern
EXCLUDES="node_modules|dist|.git|.quasar|vendor|__pycache__|venv|*.lock|migrations|references|artifacts|tmp|*.log|*.txt|*.jpg|*.png|*.pdf|*.json|*.html"

echo "🚀 Generating HIGHLY OPTIMIZED project dump to $OUTPUT_FILE..."

{
  echo "# FasihNexus Architecture Snapshot"
  echo "Generated at: $(date)"
  echo "Scope: Infrastructure, Entrypoints, and Critical Business Logic."
  echo ""
  
  echo "## 📂 High-Level Structure"
  echo '```text'
  if command -v tree &> /dev/null; then
    tree -L 2 -I "node_modules|dist|.git|venv|data"
  else
    find . -maxdepth 2 -not -path '*/.*' | grep -Ev "node_modules|dist|.git" | sed -e 's;[^/]*/;|____;g;s;____|; |;g'
  fi
  echo '```'
  echo ""

  echo "## 🐳 Docker & Infrastructure (The Foundation)"
  find . -maxdepth 1 -name "docker-compose*.yml" -o -name "*.sh" | while read -r file; do
    echo "### $file"
    echo '```yaml'
    cat "$file"
    echo '```'
    echo ""
  done

  echo "## 📜 Project Documentation"
  [ -f "GEMINI.md" ] && echo "### GEMINI.md" && echo '```markdown' && cat GEMINI.md && echo '```' && echo ""
  [ -f "README.md" ] && echo "### README.md" && echo '```markdown' && cat README.md && echo '```' && echo ""

  echo "## ⚙️ Configuration & Environment"
  # Include .env (raw as requested) and main package definitions
  [ -f ".env" ] && echo "### .env" && echo '```bash' && cat .env && echo '```'
  find . -maxdepth 2 -name "package.json" -o -name "requirements.txt" | while read -r file; do
    echo "### $file"
    echo '```json'
    cat "$file"
    echo '```'
  done

  echo "## 🏗️ Essential Code (Entrypoints & Schema)"
  # We only include the most critical files to keep the dump under a reasonable limit.
  CRITICAL_FILES=(
    "dashboard/server/index.ts"
    "dashboard/server/db/schema.ts"
    "dashboard/server/db/index.ts"
    "rpa/src/app.py"
    "rpa/src/auth.py"
    "rpa/src/main.py"
    "vpn/entrypoint.sh"
    "dashboard/entrypoint.sh"
  )

  for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
      echo "### $file"
      # Determine block type
      case "$file" in
        *.py) echo '```python' ;;
        *.ts) echo '```typescript' ;;
        *.sh) echo '```bash' ;;
        *) echo '```' ;;
      esac
      cat "$file"
      echo '```'
      echo ""
    fi
  done

  echo "## 📜 Recent Activity"
  echo "Last 5 Git Commits:"
  echo '```'
  git log -n 5 --oneline 2>/dev/null || echo "Git history unavailable."
  echo '```'

} > "$OUTPUT_FILE"

echo "✅ Optimized Dump complete! Saved to $OUTPUT_FILE"
```

## 📜 Project Documentation
### GEMINI.md
```markdown
# FasihNexus — FASIH-SM Data Sync Platform

Platform otomasi sinkronisasi data survei dari aplikasi **FASIH-SM** (fasih-sm.bps.go.id) milik BPS yang berada di balik FortiVPN. Sistem berjalan sebagai multi-container Docker dan terdiri dari 6 komponen utama yang dioptimalkan untuk arsitektur **Hybrid Network Bridge** di Coolify.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                       docker-compose                        │
│                                                             │
│  ┌──────────────┐         ┌──────────┐      ┌────────────┐  │
│  │   Coolify    │         │fasih_int │      │  Storage   │  │
│  │   Network    │         │ network  │      │ (Postgres/ │  │
│  └──────┬───────┘         └────┬─────┘      │ SeaweedFS) │  │
│         │                      │            └─────┬──────┘  │
│         │         ┌────────────┴──────────┐       │         │
│         └─────────┤       Dashboard       ├───────┘         │
│                   └────────────┬──────────┘                 │
│                                │                            │
│                   ┌────────────┴──────────┐                 │
│                   │      VPN Gateway      │                 │
│                   │ (dns: 127.0.0.11)     │                 │
│                   └─────┬──────┬──────┬───┘                 │
│                         │      │      │                     │
│                   ┌─────┴──┐┌──┴───┐┌──┴──────┐             │
│                   │  RPA   ││Auth  ││Archiver │             │
│                   └────────┘└──────┘└─────────┘             │
│                    (network_mode: service:vpn)              │
└─────────────────────────────────────────────────────────────┘
```

## Komponen

### 1. `vpn/` — VPN Gateway (Network Owner)
- **Tech**: Debian slim + openfortivpn (compiled with SAML support)
- **Fungsi**: Menyediakan tunnel VPN. Menggunakan **DNS Pinning** (`dns: 127.0.0.11`) agar service yang menumpang (`network_mode: service:vpn`) tetap bisa mengakses service internal Docker (fasih-db, s3) yang berada di network `fasih_internal`.
- **Auth**: SAML cookie (`SVPNCOOKIE`).

### 2. `rpa/` — RPA Sync Engine
- **Tech**: Python 3, FastAPI, Playwright
- **Fungsi**: Sinkronisasi data assignment (Login → Navigate → Rotate Filter → Fetch → Upsert).
- **Struktur**: 
  - `api.py`: FastAPI wrapper.
  - `src/main.py`: Orchestrator utama.
  - `src/db/repository.py`: Upsert logic (batch 500 records).

### 3. `vpn-auth/` — Auth Helper
- **Tech**: Python (FastAPI)
- **Fungsi**: Berjalan di port 8001 (shared network stack dengan VPN) untuk menangani validasi SSO tanpa mengganggu port 8000 (RPA).

### 4. `archiver/` — Image Vault
- **Tech**: Python (SQLAlchemy + Boto3)
- **Fungsi**: Mirroring foto dari BPS S3 ke SeaweedFS lokal. Dilengkapi mekanisme *self-healing* untuk URL yang expired.

### 5. `dashboard/` — Web Dashboard & Bridge
- **Backend**: Bun + Elysia
- **Frontend**: Vue 3 + Quasar
- **Fungsi**: UI manajemen, visualisasi BI, dan jembatan network (terhubung ke `coolify` dan `fasih_internal`).

### 6. `Infrastructure/`
- **PostgreSQL 16-alpine**: Database utama.
- **SeaweedFS**: S3-compatible storage untuk Image Vault.

## Skalabilitas (5M+ Baris)

Platform ini dioptimalkan untuk dataset besar:
- **Aggregasi SQL**: Scorecard dan bar chart dihitung di level database.
- **Cursor-based Pagination**: Menghindari degradasi performa pada tabel `assignments` yang besar.
- **Batch Processing**: Sinkronisasi dan upload label menggunakan chunking (500-1000 baris).

## Cara Menjalankan

Sistem menggunakan bash scripts sebagai entrypoint development:
- `./start-local.sh`: Mode HMR (Dashboard di host, DB & VPN di Docker).
- `./start-docker.sh`: Mode produksi penuh.
- `./check-health.sh`: Validasi integritas `.env` dan Docker schema.
- `./check-stability.sh`: Audit konektivitas internal (simulasi Traefik).

## Known Gotchas & Best Practices (Crucial)

1. **DNS & Host Pinning**: Service `vpn` WAJIB memiliki `dns: 127.0.0.11` DAN semua `extra_hosts` (misal: `fasih-sm.bps.go.id:10.1.110.13`). Service yang menumpang (`network_mode: service:vpn`) TIDAK BOLEH memiliki `extra_hosts` sendiri karena akan konflik dengan namespace network owner.
2. **MTU Sensitivity**: BPS internal network sangat sensitif terhadap fragmentasi paket. Jika login RPA atau VPN sering timeout/hang saat kirim data (POST), turunkan MTU ke **1200** (default 1500/1350 mungkin masih terlalu besar).
3. **Playwright Timeouts**: Jaringan Keycloak/SSO BPS sering mengalami latensi tinggi (>5s per request). Pastikan semua action Playwright (`goto`, `fill`, `click`, `wait_for_selector`) memiliki timeout minimal **60s-120s**.
4. **Coolify Network Settings**: Pada resource Docker Compose di Coolify, opsi **"Connect to Predefined Network"** harus **DIMATIKAN** (OFF) untuk menghindari error `mutually exclusive network_mode`.
5. **VPN Restart**: Jika container VPN restart, session di Fortinet mungkin menggantung. User perlu update cookie via Dashboard.
6. **Internal Scheduler Delay**: RPA scheduler sengaja menunggu 30 detik saat startup agar VPN tunnel stabil sebelum mulai query database.
7. **VPN Health Dependency**: Service yang menumpang di VPN (`rpa`, `archiver`, `vpn-auth`) WAJIB menggunakan `condition: service_healthy` pada `depends_on: vpn` untuk memastikan tunnel sudah benar-benar established sebelum aplikasi mulai berjalan.

---
**Status**: Production Hardened (Hybrid Network Bridge Model).

## The Golden Rules of BPS VPN Sync (Hard-won Lessons)

1. **The 5-Second Portal Stabilization**: Portal Fortinet BPS (`akses.bps.go.id`) memuat script background secara asinkron. Mengklik tombol SAML/SSO sebelum indikator loading berhenti (atau < 5 detik) akan memicu **403 Forbidden**. Selalu gunakan `asyncio.sleep(5)` setelah navigasi ke portal.
2. **Internal DNS Consistency**: Dalam stack Docker, `DATABASE_URL` WAJIB menggunakan hostname servis sesuai `docker-compose.yml` (contoh: `fasih-db`), BUKAN `localhost` atau `postgres`. Kesalahan kecil di sini membuat kontainer VPN "buta" terhadap cookie di database.
3. **HTTP/2 & Fingerprinting Protection**: Gateway BPS sangat sensitif terhadap fingerprint browser otomatis. Selalu paksa protokol **HTTP/1.1** (`--disable-http2`) dan gunakan User-Agent Mobile (Android/Pixel) yang konsisten di RPA (Playwright) dan VPN (OpenConnect) untuk menghindari blokir silent.
4. **MTU Sensitivity (Fragmentation)**: Jaringan internal BPS sering menjatuhkan paket yang terfragmentasi. Jika login berhasil tapi ambil data (POST) selalu timeout/hang, pastikan MTU diatur ke **1000-1100**. Default 1500 akan gagal di lingkungan Cloud/VPN tertentu.
5. **Self-Healing Loop**: Jika VPN gagal konek dengan cookie, sistem akan menghapus cookie dari DB. Jika ini terjadi berulang, jangan paksa VPN restart, tapi periksa apakah `rpa` berhasil ambil cookie baru atau justru terjebak di Keycloak.
6. **Strict Origin Validation (Better Auth)**: Better Auth sangat ketat membedakan `localhost` dan `127.0.0.1`. Jika mengakses via `localhost`, pastikan `BETTER_AUTH_URL` di `.env` dan `trustedOrigins` di `auth.ts` juga menggunakan `localhost`. Ketidaksinkronan akan memicu error `403 Invalid Origin`.
7. **Decoupled Startup (Circular Dependency)**: Kontainer RPA WAJIB menggunakan `condition: service_started` pada `depends_on: vpn` (BUKAN `service_healthy`). Hal ini agar RPA bisa jalan untuk mengambil cookie saat VPN sedang mati/diskonek.
8. **DNS Prioritization & Host Pinning**: Saat VPN aktif, ia akan menimpa `/etc/resolv.conf`. Pastikan DNS Docker `127.0.0.11` tetap di posisi paling atas dan IP database dipetakan secara manual ke `/etc/hosts` agar kontainer RPA tetap bisa menyimpan data ke DB saat berada di dalam tunnel.
9. **Routing Shadow Effect (The "Zombie" Route)**: Kontainer dengan `network_mode: service:vpn` sering gagal mendeteksi tabel routing kernel yang diupdate asinkron oleh OpenConnect/OpenFortiVPN. Jika RPA mendapat error `101 Network Unreachable` saat VPN sudah `Connected`, kontainer RPA WAJIB di-restart untuk menyegarkan view stack jaringannya.
10. **Auth Wrapper Resilience**: Selalu sediakan pembungkus `auto_login(page, user, pass)` yang mengembalikan tuple `(success, cookies, error_msg)`. Pastikan fungsi ini menunggu mendarat di domain target (`fasih-sm.bps.go.id`) sebelum mengembalikan cookie untuk menjamin integritas session (XSRF & laravel_session).
```

### README.md
```markdown
# FasihNexus — FASIH-SM Data Sync Platform

Platform otomasi sinkronisasi data survei dari aplikasi **FASIH-SM** (fasih-sm.bps.go.id) milik BPS. Sistem berjalan sebagai multi-container Docker dan terdiri dari 6 komponen utama yang dioptimalkan untuk deployment **Coolify**.

## Fitur Utama

- 🔄 **Sinkronisasi Otomatis** — Robot RPA login ke FASIH-SM via SSO dan mengambil data assignment survei
- 🖼️ **Image Vault** — Archiver otomatis meng-mirror foto BPS ke SeaweedFS lokal (S3 compatible)
- 📊 **Dashboard BI** — Visualisasi scorecard, bar chart, tabel data, dan peta titik sebaran (WebGL MapLibre)
- 🏷️ **Label Management** — Upload/download label Excel dengan schema dinamis per survey
- 🔒 **Hardened VPN** — Tunnel VPN dengan auto-reconnect, DNS pinning, dan SAML cookie support
- 🚀 **Coolify Ready** — Arsitektur Hybrid Network Bridge untuk kestabilan GitHub App Autodeploy

## Arsitektur (Hybrid Network Bridge)

Sistem menggunakan model "Bridge" di mana Dashboard bertindak sebagai penghubung antara network publik (Coolify/Traefik) dan network internal yang terisolasi.

```
┌─────────────────────────────────────────────────────────────┐
│                       docker-compose                        │
│                                                             │
│  ┌──────────────┐         ┌──────────┐      ┌────────────┐  │
│  │   Coolify    │         │fasih_int │      │  Storage   │  │
│  │   Network    │         │ network  │      │ (Postgres/ │  │
│  └──────┬───────┘         └────┬─────┘      │ SeaweedFS) │  │
│         │                      │            └─────┬──────┘  │
│         │         ┌────────────┴──────────┐       │         │
│         └─────────┤       Dashboard       ├───────┘         │
│                   └────────────┬──────────┘                 │
│                                │                            │
│                   ┌────────────┴──────────┐                 │
│                   │      VPN Gateway      │                 │
│                   │ (dns: 127.0.0.11)     │                 │
│                   └─────┬──────┬──────┬───┘                 │
│                         │      │      │                     │
│                   ┌─────┴──┐┌──┴───┐┌──┴──────┐             │
│                   │  RPA   ││Auth  ││Archiver │             │
│                   └────────┘└──────┘└─────────┘             │
│                    (network_mode: service:vpn)              │
└─────────────────────────────────────────────────────────────┘
```

## Komponen

### 1. `vpn/` — VPN Gateway (Owner of Network Stack)
- **Tech**: Debian slim + openfortivpn (Custom SAML Support)
- **Fungsi**: Menyediakan tunnel ke BPS. Menggunakan `dns: 127.0.0.11` untuk menjamin resolusi DNS internal bagi service yang menumpang di stack-nya.
- **Auth**: SAML cookie (`SVPNCOOKIE`).

### 2. `rpa/` — RPA Sync Engine
- **Tech**: Python 3, FastAPI, Playwright
- **Fungsi**: Robot sinkronisasi sekuensial (Login → Navigate → Fetch → Upsert).
- **Deployment**: Berjalan di dalam network namespace VPN.

### 3. `vpn-auth/` — SSO Auth Helper
- **Tech**: Python (FastAPI)
- **Fungsi**: Menyediakan endpoint untuk validasi session SSO (Port 8001).

### 4. `archiver/` — Image Vault Worker
- **Tech**: Python (SQLAlchemy + Boto3)
- **Fungsi**: Sinkronisasi foto dari BPS S3 ke lokal SeaweedFS. Mendukung self-healing URL expired.

### 5. `dashboard/` — UI & Bridge
- **Tech**: Bun + Elysia (Backend), Vue 3 + Quasar (Frontend)
- **Fungsi**: Orchestrator utama dan satu-satunya service yang terekspos ke Traefik/Internet.

### 6. `Infrastructure/` — Persistence
- **PostgreSQL 16**: Database utama.
- **SeaweedFS**: S3-compatible storage untuk Image Vault.

## Cara Menjalankan

### 1. Environment Setup
```bash
cp .env.example .env
# Isi variabel wajib: POSTGRES_PASSWORD, ENCRYPTION_KEY, BETTER_AUTH_SECRET, dll.
```

### 2. Deployment di Coolify (GitHub App Autodeploy)
1. Buat resource **Docker Compose** baru.
2. Hubungkan ke repository ini (branch `main`).
3. **PENTING**: Di tab Settings, pastikan **"Connect to Predefined Network"** dalam kondisi **OFF**.
4. Isi Environment Variables di UI Coolify sesuai `.env.example`.
5. Klik **Deploy**.

## Troubleshooting & Hard-won Lessons

1. **Circular Dependency Resolution**: Service yang menumpang di VPN (RPA, Archiver) harus menggunakan `condition: service_started` pada `depends_on: vpn`. Ini memungkinkan RPA melakukan login SSO ke portal publik untuk menyetor cookie ke database sebelum VPN mencoba menyambung.
2. **Routing Refresh (The "Shadow" Interface)**: Dalam mode `network_mode: service:vpn`, kontainer yang menumpang terkadang tidak mendeteksi interface `tun0`/`ppp0` atau tabel routing baru jika ia sudah menyala sebelum tunnel VPN terbentuk. **Solusi**: Restart kontainer RPA setelah VPN dipastikan `Connected`.
3. **Portal SAML Stabilization**: Portal BPS (`akses.bps.go.id`) memerlukan waktu ~5 detik untuk memuat skrip latar belakang setelah halaman tampil. Mengklik tombol login terlalu cepat akan memicu error **403 Forbidden**. Gunakan `asyncio.sleep(5)` wajib di Playwright.
4. **DNS & Host Pinning**: VPN secara agresif menimpa `/etc/resolv.conf`. Gunakan DNS Pinning (`127.0.0.11` di baris pertama) dan lakukan pemetaan manual IP database ke `/etc/hosts` di dalam kontainer VPN agar layanan internal tetap dapat saling berkomunikasi.
5. **MTU Sensitivity**: Selalu gunakan MTU **1000** untuk interface VPN. Angka yang lebih besar (1500/1350) sering menyebabkan paket data besar (JSON survey) terfragmentasi dan gagal terkirim (timeout).

## Lisensi

Internal BPS — tidak untuk distribusi publik.
```

## ⚙️ Configuration & Environment
### .env
```bash
# PostgreSQL
POSTGRES_USER=fasih
POSTGRES_PASSWORD=changeme_generate_random
POSTGRES_DB=fasih_dashboard
DATABASE_URL=postgresql://fasih:changeme_generate_random@postgres:5432/fasih_dashboard

# RPA - encryption key for SSO passwords
ENCRYPTION_KEY=24f81eeee1f9b8bce1b51d4aa48d288895cf7f0e0b5e2f5a488b63491c07bbda

# VPN BPS
VPN_HOST=akses.bps.go.id
VPN_USER=arinif@bps.go.id
VPN_PASS=p4sswordarin
VPN_TRUSTED_CERT=de74481c56635274320d58e3267de977acbd6ea8cdbc5450042010d7e9544659
VPN_COOKIE=xrV/Va6G7w0/20ue/gNroS7prlNEZsuOCaRO5TXt6lCJqhPeLqTaf9gLoHzjkudravdojS/fqAWGT8Slrt/IT3D4h0Jqus8peIhUPF6H2J24FlsALAEg1bNypuHH6Gg1W9pRNbBe3fIytgbb3ALhqxheeD6BTssVmIWNwriURYjIIkHI9ClhRq3uC/xSkJnAb1k5TapV8qpG8X5qWkkewoT5XasayHx9H6OahZ3xxBqJWp/fV4RxEal4KVA7Hsu8T8FLDdEpvl4LKC/8esth6XnaJrUjhxSPQbNqWvIYNIbceHpF/7yThccZ9UUxGDLRBEXep7mMDlD1Tan0riFSYUc0moZLUys=
SKIP_DETAIL_FETCH=false

# SeaweedFS Image Vault
S3_ACCESS_KEY=cdcadmin
S3_SECRET_KEY=cdc_secure_secret_2026
S3_BUCKET=survey-images
S3_ENDPOINT=http://s3:8333
STORAGE_LOCAL_DOMAIN=http://127.0.0.1:3000
PUBLIC_BASE_URL=http://127.0.0.1:9000

# Better Auth
BETTER_AUTH_SECRET=c6065adbae6f2d29b152b61de771feb2c1508a8281677ad81f9f190c9675b6c2
BETTER_AUTH_URL=http://127.0.0.1:3000
```
### ./rpa/requirements.txt
```json
playwright>=1.40.0
python-dotenv>=1.0.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
cryptography>=42.0.0
pydantic>=2.0.0
aiohttp>=3.9.0
uvloop>=0.21.0
aioboto3>=12.0.0
aiobotocore>=2.11.0
```
### ./dashboard/package.json
```json
{
  "name": "fasih-dashboard",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "bun run --watch server/index.ts",
    "build": "cd client && bun install && bunx quasar build",
    "start": "bun run server/index.ts",
    "db:push": "bunx drizzle-kit push"
  },
  "dependencies": {
    "@aws-sdk/client-s3": "^3.1027.0",
    "@aws-sdk/s3-request-presigner": "^3.1027.0",
    "@better-auth/utils": "^0.4.0",
    "@elysiajs/cors": "^1.4.1",
    "@elysiajs/static": "^1.4.7",
    "argon2": "^0.44.0",
    "better-auth": "^1.6.11",
    "drizzle-orm": "^0.45.1",
    "elysia": "^1.4.27",
    "postgres": "^3.4.8",
    "xlsx": "^0.18.5"
  },
  "devDependencies": {
    "@types/bun": "latest",
    "drizzle-kit": "^0.31.9"
  }
}```
## 🏗️ Essential Code (Entrypoints & Schema)
### dashboard/server/index.ts
```typescript
import { Elysia } from "elysia";
import { cors } from "@elysiajs/cors";
import { staticPlugin } from "@elysiajs/static";
import { surveysRoutes } from "./routes/surveys";
import { assignmentsRoutes } from "./routes/assignments";
import { logsRoutes } from "./routes/logs";
import { syncRoutes } from "./routes/sync";
import { labelsRoutes } from "./routes/labels";
import { visualizationsRoutes } from "./routes/visualizations";
import { storageRoutes } from "./routes/storage";
import { syncStateRoutes } from "./routes/sync-state";

import { auth } from "./auth";
import { authMiddleware, getAuthContext } from "./middleware/auth";

// Best practice per dokumentasi resmi better-auth:
// Gunakan .mount(auth.handler) agar semua HTTP method (GET, POST, dll)
// ditangani langsung — tidak ada konflik wildcard dengan Elysia.
// Ref: https://www.better-auth.com/docs/integrations/elysia

const loginAttempts = new Map<string, { count: number, last: number }>();

const authRoutes = new Elysia({ prefix: "/api/auth" })
    .onBeforeHandle(({ path, request, set }) => {
        if (path === "/api/auth/sign-in/email") {
            const ip = request.headers.get("x-forwarded-for") || "unknown";
            const now = Date.now();
            const attempt = loginAttempts.get(ip) || { count: 0, last: 0 };
            
            if (now - attempt.last < 1000) { // 1s cooldown between attempts
                set.status = 429;
                return { error: "Too fast. Slow down." };
            }
            
            if (attempt.count > 10 && now - attempt.last < 60000) { // Max 10 attempts per minute
                set.status = 429;
                return { error: "Too many login attempts. Try again in a minute." };
            }
            
            loginAttempts.set(ip, { 
                count: now - attempt.last > 60000 ? 1 : attempt.count + 1, 
                last: now 
            });
        }
    })
    .post("/sign-up/email", ({ set }) => {
        // Block public registration for security hardening.
        // Users should be created via admin console or direct DB insert.
        set.status = 403;
        return { error: "Public registration is disabled for security hardening." };
    })
    .get("/me/roles", ({ user, roles }: any) => {
        if (!user) return { roles: [] };
        return { user, roles };
    })
    .get("/*", async (ctx) => {
        return auth.handler(ctx.request);
    })
    .all("/*", async (ctx) => {
        return auth.handler(ctx.request);
    });

const app = new Elysia()
    .use(cors({
        credentials: true,
        origin: process.env.PUBLIC_BASE_URL || "http://127.0.0.1:3000",
        allowedHeaders: ["Content-Type", "Authorization"],
        methods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    }))
    .get("/api/health", () => ({ status: "ok", timestamp: new Date().toISOString() }))
    .use(authRoutes)
    .derive(async ({ request }) => {
        return await getAuthContext(request);
    })
    // Global Security Gate & Headers
    .onBeforeHandle(({ path, user, set, request }: any) => {
        // 1. Security Headers
        set.headers["X-Frame-Options"] = "DENY";
        set.headers["X-Content-Type-Options"] = "nosniff";
        set.headers["X-XSS-Protection"] = "1; mode=block";
        set.headers["Referrer-Policy"] = "strict-origin-when-cross-origin";

        // 2. Global Auth Check (BOLA Prevention)
        const isPublicAuth = path.startsWith("/api/auth/") || path === "/api/health";
        // Status endpoints are public — they're read-only UI indicators with no sensitive data
        const isPublicStatus = path === "/api/surveys/sync/status" || path === "/api/surveys/vpn/status";
        const isProtectedApi = path.startsWith("/api/") || path.startsWith("/storage/");

        if (isProtectedApi && !isPublicAuth && !isPublicStatus && !user) {
            console.warn(`[Security] 401 Unauthorized ${request.method} ${path} (User: ${user ? 'found' : 'null'})`);
            set.status = 401;
            return { error: "Unauthorized" };
        }
        
        if (isProtectedApi) {
            console.log(`[Security] 200 Authorized ${request.method} ${path} for user ${user?.email || 'unknown'}`);
        }
    })
    // Protected Routes
    .use(surveysRoutes)
    .use(assignmentsRoutes)
    .use(logsRoutes)
    .use(syncRoutes)
    .use(labelsRoutes)
    .use(visualizationsRoutes)
    .use(storageRoutes)
    .use(syncStateRoutes)
    // Serve static files and fallback to index.html for SPA
    .get("*", async ({ path, set }) => {
        // IMPORTANT: Never serve index.html for API routes
        if (path.startsWith("/api/")) {
            set.status = 404;
            return { error: "API route not found" };
        }

        const filePath = path === "/" ? "/index.html" : path;
        const file = Bun.file(`client/dist/spa${filePath}`);

        if (await file.exists()) return file;

        // Return index.html for non-existent routes (SPA fallback)
        // unless it looks like an asset that SHOULD have existed
        if (path.startsWith("/assets/") || path.includes(".")) {
            return new Response("Not Found", { status: 404 });
        }

        return Bun.file("client/dist/spa/index.html");
    })
    .listen(process.env.PORT || 3000);

console.log(`🚀 Dashboard running at http://127.0.0.1:${app.server?.port}`);
```

### dashboard/server/db/schema.ts
```typescript
import { pgTable, text, integer, boolean, timestamp, uuid, jsonb, index, primaryKey } from "drizzle-orm/pg-core";
import { relations } from "drizzle-orm";

// --- EXISTING TABLES ---

export const surveyConfigs = pgTable("survey_configs", {
  id: uuid("id").primaryKey().defaultRandom(),
  surveyName: text("survey_name").notNull(),
  ssoUsername: text("sso_username").notNull(),
  ssoPasswordEncrypted: text("sso_password_encrypted").notNull(),
  filterProvinsi: text("filter_provinsi").default(""),
  filterKabupaten: text("filter_kabupaten").default(""),
  filterRotation: text("filter_rotation").default("pengawas"),
  intervalMinutes: integer("interval_minutes").default(30),
  isActive: boolean("is_active").default(true),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
});

export const assignments = pgTable("assignments", {
  id: text("id").primaryKey(),
  surveyConfigId: uuid("survey_config_id").references(() => surveyConfigs.id, { onDelete: "cascade" }),
  codeIdentity: text("code_identity"),
  surveyPeriodId: text("survey_period_id"),
  assignmentStatusAlias: text("assignment_status_alias"),
  currentUserUsername: text("current_user_username"),
  dataJson: jsonb("data_json"),
  flatData: jsonb("flat_data"),
  dateModifiedRemote: text("date_modified_remote"),
  dateSynced: timestamp("date_synced", { withTimezone: true }).defaultNow(),
  syncedToApi: boolean("synced_to_api").default(false),
  localImageMirrored: boolean("local_image_mirrored").default(false),
  localImagePaths: jsonb("local_image_paths").default({}),
  syncLogId: integer("sync_log_id").references(() => syncLogs.id, { onDelete: "set null" }),
}, (table) => [
  index("idx_assignments_survey_config_id").on(table.surveyConfigId),
  index("idx_assignments_survey_date").on(table.surveyConfigId, table.dateSynced),
  index("idx_assignments_survey_code").on(table.surveyConfigId, table.codeIdentity),
  index("idx_assignments_survey_status").on(table.surveyConfigId, table.assignmentStatusAlias),
  index("idx_assignments_synced").on(table.syncedToApi),
]);

export const syncLogs = pgTable("sync_logs", {
  id: integer("id").primaryKey().generatedAlwaysAsIdentity(),
  surveyConfigId: uuid("survey_config_id").references(() => surveyConfigs.id, { onDelete: "cascade" }),
  startedAt: timestamp("started_at", { withTimezone: true }),
  finishedAt: timestamp("finished_at", { withTimezone: true }),
  totalFetched: integer("total_fetched").default(0),
  totalNew: integer("total_new").default(0),
  totalUpdated: integer("total_updated").default(0),
  totalSkipped: integer("total_skipped").default(0),
  totalFailed: integer("total_failed").default(0),
  totalImages: integer("total_images").default(0),
  imagesMirrored: integer("images_mirrored").default(0),
  status: text("status").default("running"),
  notes: text("notes"),
  timings: jsonb("timings"),
}, (table) => [
  index("idx_sync_logs_survey").on(table.surveyConfigId),
  index("idx_sync_logs_status").on(table.status),
]);

export const labelSchemas = pgTable("label_schemas", {
  id: integer("id").primaryKey().generatedAlwaysAsIdentity(),
  surveyConfigId: uuid("survey_config_id")
    .references(() => surveyConfigs.id, { onDelete: "cascade" }).notNull(),
  columns: jsonb("columns").notNull(),
  uploadedAt: timestamp("uploaded_at", { withTimezone: true }).defaultNow(),
});

export const labelData = pgTable("label_data", {
  id: integer("id").primaryKey().generatedAlwaysAsIdentity(),
  surveyConfigId: uuid("survey_config_id")
    .references(() => surveyConfigs.id, { onDelete: "cascade" }).notNull(),
  codeIdentity: text("code_identity").notNull(),
  data: jsonb("data").notNull(),
}, (table) => [
  index("idx_label_data_survey_code").on(table.surveyConfigId, table.codeIdentity),
]);

export const visualizationConfigs = pgTable("visualization_configs", {
  id: integer("id").primaryKey().generatedAlwaysAsIdentity(),
  surveyConfigId: uuid("survey_config_id")
    .references(() => surveyConfigs.id, { onDelete: "cascade" }).notNull(),
  name: text("name").notNull(),
  chartType: text("chart_type").notNull(),
  config: jsonb("config").notNull(),
  sortOrder: integer("sort_order").default(0),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
});

export const systemSettings = pgTable("system_settings", {
  key: text("key").primaryKey(),
  value: text("value").notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
});

// --- AUTH & RBAC TABLES ---

export const users = pgTable("users", {
  id: text("id").primaryKey(),
  name: text("name").notNull(),
  email: text("email").notNull().unique(),
  emailVerified: boolean("email_verified").notNull().default(false),
  image: text("image"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

export const sessions = pgTable("sessions", {
  id: text("id").primaryKey(),
  userId: text("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  token: text("token").notNull().unique(),
  expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
  ipAddress: text("ip_address"),
  userAgent: text("user_agent"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

export const accounts = pgTable("accounts", {
  id: text("id").primaryKey(),
  userId: text("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  accountId: text("account_id").notNull(),
  providerId: text("provider_id").notNull(),
  accessToken: text("access_token"),
  refreshToken: text("refresh_token"),
  accessTokenExpiresAt: timestamp("access_token_expires_at", { withTimezone: true }),
  refreshTokenExpiresAt: timestamp("refresh_token_expires_at", { withTimezone: true }),
  scope: text("scope"),
  password: text("password"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

export const verifications = pgTable("verifications", {
  id: text("id").primaryKey(),
  identifier: text("identifier").notNull(),
  value: text("value").notNull(),
  expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

// --- RBAC ---

export const roles = pgTable("roles", {
  id: text("id").primaryKey(),
  name: text("name").notNull().unique(), // e.g. "admin", "user"
  description: text("description"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
});

export const permissions = pgTable("permissions", {
  id: text("id").primaryKey(),
  name: text("name").notNull().unique(), // e.g. "survey:write", "user:manage"
  description: text("description"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
});

export const usersToRoles = pgTable("users_to_roles", {
  userId: text("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  roleId: text("role_id").notNull().references(() => roles.id, { onDelete: "cascade" }),
}, (t) => ({
  pk: primaryKey({ columns: [t.userId, t.roleId] }),
}));

export const rolesToPermissions = pgTable("roles_to_permissions", {
  roleId: text("role_id").notNull().references(() => roles.id, { onDelete: "cascade" }),
  permissionId: text("permission_id").notNull().references(() => permissions.id, { onDelete: "cascade" }),
}, (t) => ({
  pk: primaryKey({ columns: [t.roleId, t.permissionId] }),
}));

// --- RELATIONS ---

export const usersRelations = relations(users, ({ many }) => ({
  roles: many(usersToRoles),
}));

export const rolesRelations = relations(roles, ({ many }) => ({
  users: many(usersToRoles),
  permissions: many(rolesToPermissions),
}));

export const permissionsRelations = relations(permissions, ({ many }) => ({
  roles: many(rolesToPermissions),
}));

export const usersToRolesRelations = relations(usersToRoles, ({ one }) => ({
  user: one(users, { fields: [usersToRoles.userId], references: [users.id] }),
  role: one(roles, { fields: [usersToRoles.roleId], references: [roles.id] }),
}));

export const rolesToPermissionsRelations = relations(rolesToPermissions, ({ one }) => ({
  role: one(roles, { fields: [rolesToPermissions.roleId], references: [roles.id] }),
  permission: one(permissions, { fields: [rolesToPermissions.permissionId], references: [permissions.id] }),
}));
```

### dashboard/server/db/index.ts
```typescript
import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import * as schema from "./schema";

const connectionString = process.env.DATABASE_URL || "postgresql://fasih:changeme@127.0.0.1:5432/fasih_dashboard";

const client = postgres(connectionString, {
    max: 20,
    idle_timeout: 30,
    connect_timeout: 10,
});
export const db = drizzle(client, { schema });
```

### rpa/src/app.py
```python
import os
import sys
from pathlib import Path

# Self-healing path: Ensure the directory containing this file is in sys.path
# This allows 'import db', 'import routes' etc. to work regardless of the working directory.
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

import os

from datetime import datetime, timezone
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager


# Database and Route imports

from db.connection import init_db, get_session
from db.models import SyncLog

from routes.sync import router as sync_router
from routes.lookup import router as lookup_router

@asynccontextmanager
async def lifespan(fastapi_app):
    """On startup: clean up stale 'running' jobs and resume 'queued' ones."""
    try:
        init_db()
        session = get_session()
        # Only mark 'running' as failed. 'queued' jobs should be preserved and resumed.
        stale = (
            session.query(SyncLog)
            .filter(SyncLog.status == "running")
            .all()
        )
        if stale:
            for job in stale:
                job.status = "failed"
                job.finished_at = datetime.now(timezone.utc)
                job.notes = "Killed by container restart while running"
            session.commit()
            print(f"🧹 Startup cleanup: marked {len(stale)} stale RUNNING job(s) as failed.")
        
        # Check if we should re-trigger the worker
        queued_count = session.query(SyncLog).filter(SyncLog.status == "queued").count()
        session.close()

        if queued_count > 0:
            from worker.queue import _queue_worker
            import asyncio
            print(f"🔄 Startup: Found {queued_count} queued jobs. Auto-triggering worker...")
            asyncio.create_task(_queue_worker())

        # Start Routine Sync Scheduler
        from worker.scheduler import routine_sync_loop
        import asyncio
        print("🕒 Startup: Starting Routine Sync Scheduler...")
        asyncio.create_task(routine_sync_loop())

        # 4. Headless VPN Bootstrap: Fetch cookie using environment credentials
        vpn_user = os.getenv("VPN_USER")
        vpn_pass = os.getenv("VPN_PASS")
        if vpn_user and vpn_pass:
            from auth import fetch_vpn_cookie, sync_cookie_to_db
            async def bootstrap_vpn():
                # Delay slightly to let the server stabilize
                await asyncio.sleep(5)
                print(f"🌐 [Startup] Auto-bootstrapping VPN for {vpn_user}...")
                cookie = await fetch_vpn_cookie(vpn_user, vpn_pass)
                if cookie:
                    await sync_cookie_to_db(cookie)
                    print("✅ [Startup] VPN Auto-bootstrap successful.")
                else:
                    print("❌ [Startup] VPN Auto-bootstrap failed.")
            
            asyncio.create_task(bootstrap_vpn())

    except Exception as e:
        print(f"⚠️ Startup cleanup/recovery failed: {e}")
    
    yield  # Server runs here

app = FastAPI(title="FASIH-SM RPA Sync API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sync_router)
app.include_router(lookup_router)
```

### rpa/src/auth.py
```python
import os
import asyncio
import psycopg2
import json
from playwright.async_api import async_playwright

async def launch_stealth_browser(p):
    """Launch a browser optimized for BPS portal compatibility."""
    return await p.chromium.launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--disable-http2', # Critical: BPS Portal handles HTTP/1.1 better
        ]
    )

async def perform_sso_login(page, username, password, target_url="https://fasih-sm.bps.go.id"):
    """
    Core logic to perform SAML login on a given page.
    Returns (success, error_message)
    """
    try:
        # 1. Early check: Are we already on Keycloak/SSO?
        if "sso.bps.go.id" in page.url:
            print("   🔒 [Auth] Already on Keycloak SSO. Filling credentials...")
        else:
            # 2. Navigate to Target App directly
            target_domain = target_url.split("://")[1].split("/")[0]
            if target_domain not in page.url and "sso.bps.go.id" not in page.url:
                print(f"🚀 [Auth] Navigating to target {target_domain}...")
                await page.goto(target_url, wait_until="domcontentloaded", timeout=120000)
                
                # Apply 5-Second Stabilization Rule specifically for VPN Portal (akses.bps.go.id)
                if "akses.bps.go.id" in target_url:
                    print("   ⏳ [Auth] Waiting 5s for VPN Portal background scripts to stabilize...")
                    await asyncio.sleep(5)
                else:
                    await asyncio.sleep(2)
            
            # 3. Wait for SAML Button or FASIH-SM SSO Selection
            print(f"🚀 [Auth] Detecting SSO/SAML login button...")
            saml_selectors = [
                "#saml-login-bn", 
                ".btn-saml", 
                "button:has-text('Login SSO')", 
                "button:has-text('SAML')",
                "a[href*='/oauth2/authorization/ics']",
                "a:has-text('Login SSO BPS')"
            ]
            combined_selector = ", ".join(saml_selectors)
            
            try:
                await page.wait_for_selector(combined_selector, timeout=60000)
                # We wait 1s for event listeners to attach
                await asyncio.sleep(1) 
                print("   🖱️ [Auth] Clicking SSO/SAML button...")
                await page.click(combined_selector, force=True)
            except Exception:
                print("   ⚠️ [Auth] SSO button not found or not needed. Checking for SSO redirect...")
                # We don't return False here, we let the next block handle Keycloak

        # 4. Transition to Keycloak (SSO)
        print(f"🚀 [Auth] Handling Keycloak SSO... Current URL: {page.url}")
        try:
            # Wait for the SSO page input to be ready
            await page.wait_for_selector("#username", timeout=60000)
            print(f"   ✅ [Auth] SSO Page reached: {page.url}")
        except Exception as e:
            print(f"   ❌ [Auth] Timeout waiting for #username. Stuck at URL: {page.url}")
            if "sso.bps.go.id" not in page.url:
                return False, f"Gagal dialihkan ke SSO: {str(e)}"
            else:
                return False, f"Berada di SSO tapi #username tidak ditemukan. URL: {page.url}"
        
        # 5. Fill Credentials
        print(f"🚀 [Auth] Filling credentials...")
        await page.fill("#username", username)
        await page.fill("#password", password)
        
        # Fast submit
        await page.click("#kc-login")
        
        # 6. Check for immediate error messages
        try:
            await page.wait_for_selector(".alert-error, .kc-feedback-text, .main-sidebar, .user-panel", timeout=10000)
            if await page.query_selector(".alert-error, .kc-feedback-text"):
                err_text = "Username atau password salah (SSO)"
                err_el = await page.query_selector(".kc-feedback-text")
                if err_el: err_text = await err_el.inner_text()
                print(f"   ❌ [Auth] Login failed: {err_text}")
                return False, err_text
        except:
            pass

        return True, None

    except Exception as e:
        print(f"❌ [Auth] Error in perform_sso_login: {e}")
        return False, str(e)

async def auto_login(page, username, password):
    """
    Robust login flow for RPA workers.
    """
    try:
        print(f"🚀 [Auth] Starting automated login for {username}...")
        
        # 1. Start from Target App (SSO will trigger automatically)
        success, err_msg = await perform_sso_login(page, username, password)
        if not success:
            return False, {}, err_msg
            
        # 2. Wait for landing on the target app
        print("   ⏳ [Auth] Waiting for redirect to FASIH-SM...")
        try:
            # Wait for elements that signify a successful login in FASIH-SM
            await page.wait_for_selector(".main-sidebar, .user-panel, a[href*='logout'], .navbar", timeout=60000)
            print("   ✅ [Auth] Dashboard detected!")
        except Exception:
            # If not detected, check if we are at least on the domain
            if "fasih-sm.bps.go.id" in page.url:
                print(f"   ℹ️ [Auth] On target domain but sidebar missing. Proceeding.")
            else:
                return False, {}, "Dashboard tidak terjangkau setelah SSO"
        
        # 3. Capture cookies
        cookies_list = await page.context.cookies()
        cookies_dict = {c['name']: c['value'] for c in cookies_list}
        
        # Check critical session cookies
        has_session = any(name in cookies_dict for name in ['XSRF-TOKEN', 'laravel_session'])
        if has_session:
            print(f"✅ [Auth] Session captured ({len(cookies_dict)} cookies).")
            return True, cookies_dict, None
        else:
            return False, {}, "Missing session cookies"
            
    except Exception as e:
        print(f"❌ [Auth] auto_login failed: {e}")
        return False, {}, str(e)

async def fetch_vpn_cookie(username, password):
    """
    Automate flow for VPN container. Returns the raw SVPNCOOKIE value.
    """
    browser = None
    try:
        async with async_playwright() as p:
            browser = await launch_stealth_browser(p)
            context = await new_stealth_context(browser)
            page = await context.new_page()
            
            success, err_msg = await perform_sso_login(page, username, password, target_url="https://akses.bps.go.id/remote/login")
            if not success:
                print(f"❌ [Auth] Failed to login to VPN portal: {err_msg}")
                await browser.close()
                return None
            
            # Polling for SVPNCOOKIE
            print(f"🚀 [Auth] Polling for SVPNCOOKIE (max 90s)...")
            start_time = asyncio.get_event_loop().time()
            while (asyncio.get_event_loop().time() - start_time) < 90:
                cookies = await context.cookies()
                vpn_cookie = next((c['value'] for c in cookies if c['name'] == 'SVPNCOOKIE'), None)
                if vpn_cookie:
                    print(f"✅ [Auth] SVPNCOOKIE found.")
                    await browser.close()
                    return vpn_cookie
                await asyncio.sleep(2)
            
            await browser.close()
            return None
    except Exception as e:
        print(f"❌ [Auth] Error in fetch_vpn_cookie: {e}")
        if browser: await browser.close()
        return None

async def sync_cookie_to_db(cookie):
    """Save the fresh cookie to the system_settings table."""
    try:
        db_url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO system_settings (key, value) VALUES ('vpn_cookie', %s) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
            (cookie,)
        )
        conn.commit()
        cur.close()
        conn.close()
        print("✅ [Auth] Cookie successfully synchronized to database.")
        return True
    except Exception as e:
        print(f"❌ [Auth] Database sync failed: {e}")
        return False

async def new_stealth_context(browser, **kwargs):
    """Legacy wrapper for creating a stealth context with merged options."""
    defaults = {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "viewport": {'width': 1280, 'height': 800},
        "is_mobile": False,
        "has_touch": False,
        "locale": "en-US",
        "timezone_id": "Asia/Jakarta"
    }
    options = {**defaults, **kwargs}
    return await browser.new_context(**options)
```

### rpa/src/main.py
```python
"""
FasihNexus Sync Engine — Main Orchestrator (API First)

Fully automated robot yang:
1. Login SSO BPS otomatis via Playwright (Headless) untuk mendapatkan Cookie.
2. Menggunakan API/aiohttp murni untuk:
   a. Navigasi dan temukan ID Survey
   b. Dapatkan Region Metadata & List Pengguna (Pengawas/Pencacah)
   c. Iterate pagination Datatable Assignment (bypass limit batas baris via filter)
   d. Fetch form detail individual secara concurrent
3. Upsert ke PostgreSQL
4. Berjalan otomatis setiap N menit

Usage:
    python src/main.py                  # Start scheduler
    python src/main.py --once           # Jalankan 1 cycle saja
    python src/main.py --test-login     # Test login saja
"""
import argparse
import asyncio
import os
import re
import sys
import time
import json
from datetime import datetime, timezone

from playwright.async_api import async_playwright

# Self-healing path: Ensure both the current directory (src) and its parent (root) are in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
for d in [current_dir, parent_dir]:
    if d not in sys.path:
        sys.path.insert(0, d)

from config.settings import Settings
from auth import auto_login, launch_stealth_browser, new_stealth_context
from api_client import FasihApiClient
from pages.detail_page import fetch_assignments_concurrent
from db.connection import init_db, get_session
from db.repository import upsert_assignment, log_sync_run, SyncStats, BatchUpserterBulk, get_existing_modifications_by_ids_batched
from connectivity import ensure_connected


async def run_sync_cycle(settings: Settings, dry_run: bool = False):
    """
    Satu siklus lengkap sinkronisasi Hybrid-Headless.
    """
    started_at = datetime.now(timezone.utc)
    stats = SyncStats()
    timings = {}
    total_start = time.perf_counter()
    
    # --- FASE 0: KONEKTIVITAS VPN ---
    print("\n--- FASE 0: Memastikan Konektivitas VPN ---")
    await ensure_connected()
    
    print("\n" + "=" * 60)
    print(f"🤖 FasihNexus Sync Engine — Cycle dimulai")
    print(f"   Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Survey: {settings.survey_name}")
    print(f"   Rotasi: {settings.filter_rotation}")
    print(f"   Dry run: {dry_run}")
    print("=" * 60)

    # --- FASE 1: SESSION VALIDATION & LOGIN ---
    print("\n--- FASE 1: Session Validation & Login ---")
    phase_start = time.perf_counter()
    cookies = {}
    
    # Try CACHED cookies first
    from db.connection import get_session
    from db.repository import get_system_setting, set_system_setting
    
    db_session = get_session()
    cache_key = f"sso_cookies_{settings.sso_username}"
    cached_json = get_system_setting(db_session, cache_key)
    db_session.close()

    if cached_json:
        try:
            print(f"   🍪 Ditemukan cached cookies untuk {settings.sso_username}. Memvalidasi...")
            temp_cookies = json.loads(cached_json)
            # Test session dengan API ringan
            api_test = FasihApiClient(temp_cookies)
            # Mencoba fetch survey ID sebagai probe
            survey_id_probe = await api_test.get_survey_id(settings.survey_name)
            await api_test.close()
            
            if survey_id_probe:
                print(f"   ⚡ Sesi CACHE valid! Melewati login browser (Playwright skipped).")
                cookies = temp_cookies
            else:
                print(f"   ⚠️ Sesi CACHE kadaluwarsa. Memerlukan login browser.")
        except Exception as e:
            print(f"   ⚠️ Gagal menggunakan cached cookies: {e}")

    # Fallback to Playwright if no valid cookies
    if not cookies:
        print("   🎭 Memulai Playwright browser untuk login SSO...")
        async with async_playwright() as p:
            browser = await launch_stealth_browser(p)
            context = await new_stealth_context(
                browser,
                viewport={"width": 1280, "height": 800}
            )
            page = await context.new_page()

            login_ok, cookies_dict, err_msg = await auto_login(page, settings.sso_username, settings.sso_password)
            if not login_ok or not cookies_dict:
                print("❌ Login gagal atau cookies tidak didapatkan! Cycle dibatalkan.")
                await browser.close()
                return
                
            cookies = cookies_dict
            await browser.close()
        
        # Save fresh cookies to DB
        try:
            db_session = get_session()
            set_system_setting(db_session, cache_key, json.dumps(cookies))
            db_session.close()
            print(f"   💾 Sesi baru disimpan ke cache untuk {settings.sso_username}")
        except Exception as e:
            print(f"   ⚠️ Gagal menyimpan cookies ke DB: {e}")

    timings["login"] = int((time.perf_counter() - phase_start) * 1000)

    # Inisialisasi API Client
    api = FasihApiClient(cookies)

    # --- FASE 2: RESOLVE METADATA SURVEY & REGION ---
    print("\n--- FASE 2: Resolving API Metadata ---")
    phase_start = time.perf_counter()
    survey_id = await api.get_survey_id(settings.survey_name)
    if not survey_id:
        return

    period_id, role_ids, role_group_id = await api.get_survey_period_and_roles(survey_id)
    if not period_id or not role_ids:
        return

    prov_code, region_filter, region_full_code, region_group_id = await api.get_region_metadata(settings.filter_provinsi, settings.filter_kabupaten, survey_id)
    timings["metadata"] = int((time.perf_counter() - phase_start) * 1000)
    
    # Init DB (Central PostgreSQL only)
    if not dry_run:
        init_db()
        session = get_session()
        print(f"   📂 Using central PostgreSQL database")

    # --- FASE 3: ROTASI & FETCH ASSIGNMENTS ---
    print("\n--- FASE 3: Extract Assignment Metadata ---")
    
    pengawas_list, pencacah_list = await api.get_users_by_region(
        period_id, role_ids, region_filter or region_full_code or "", role_group_id
    )
    
    # Tentukan strategi iterasi berdasarkan setelan config rotasi
    filters_to_run = []
    if settings.filter_rotation == "pencacah" and pencacah_list:
        for idx, user in enumerate(pencacah_list):
            filters_to_run.append({
                "label": f"[{idx+1}/{len(pencacah_list)}] Pencacah: {user['fullname']}",
                "pengawas_id": None,
                "pencacah_id": user['userId']
            })
    elif pengawas_list:
        for idx, user in enumerate(pengawas_list):
            filters_to_run.append({
                "label": f"[{idx+1}/{len(pengawas_list)}] Pengawas: {user['fullname']}",
                "pengawas_id": user['userId'],
                "pencacah_id": None
            })
    else:
        filters_to_run.append({
            "label": "[1/1] Wilayah Saja (Tanpa Pengawas/Pencacah)",
            "pengawas_id": None,
            "pencacah_id": None
        })

    all_metadata_map = {}
    
    async def fetch_user_metadata(f):
        print(f"🔄 {f['label']}")
        metadata = await api.get_assignments_metadata(
            period_id, 
            prov_uuid=prov_code,
            kab_uuid=region_filter if region_filter != prov_code else None,
            pengawas_id=f['pengawas_id'], 
            pencacah_id=f['pencacah_id'],
            region_group_id=region_group_id
        )
        print(f"   📊 Ditemukan {len(metadata)} entries ({f['label']}).")
        return metadata

    # Fetch all user metadata in parallel
    metadata_results = await asyncio.gather(*(fetch_user_metadata(f) for f in filters_to_run))
    for metadata in metadata_results:
        for m in metadata:
            all_metadata_map[m['id']] = m

    unique_assignments = list(all_metadata_map.values())
    print(f"\n--- FASE 4: Fetch Detailed Assignment Data ---")
    phase_start = time.perf_counter()
    print(f"   🔗 Total Assignment Unik: {len(unique_assignments)}")
    
    if dry_run:
        stats.total_fetched = len(unique_assignments)
    else:
        if unique_assignments:
            # ── DELTA SYNC: Skip detail fetch untuk records yang tidak berubah ──
            # Bandingkan dateModifiedRemote dari datatable dengan yang tersimpan di DB.
            # get_existing_modifications_by_ids_batched menggunakan chunking 10k agar
            # aman untuk 300k+ IDs tanpa membuat IN clause raksasa.
            all_ids = [m["id"] for m in unique_assignments]
            existing_dates = get_existing_modifications_by_ids_batched(session, all_ids)

            to_fetch = []
            _debug_logged = False
            for m in unique_assignments:
                rec_id = m["id"]
                remote_date = m.get("dateModifiedRemote")
                if rec_id not in existing_dates:
                    to_fetch.append(m)
                elif existing_dates[rec_id] != remote_date:
                    if not _debug_logged and existing_dates[rec_id] and remote_date:
                        print(f"   🔬 [TIMESTAMP DEBUG] DB date: {repr(existing_dates[rec_id])} vs API date: {repr(remote_date)}")
                        _debug_logged = True
                    to_fetch.append(m)
            skipped_delta = len(unique_assignments) - len(to_fetch)

            print(f"\n   🔄 Delta check: {len(to_fetch)} perlu di-fetch, "
                  f"{skipped_delta} di-skip (tidak berubah sejak sync terakhir)")

            # Jika semua sudah up-to-date, tidak perlu fetch apapun
            if not to_fetch:
                print("   ✅ Semua data sudah up-to-date — tidak ada yang perlu di-sync!")
                stats.total_skipped = len(unique_assignments)
                timings["fetch"] = 0
            else:
                urls_to_fetch = [
                    f"{os.getenv('TARGET_URL', 'https://fasih-sm.bps.go.id')}/survey-collection/assignment-detail/{m['id']}/{survey_id}"
                    for m in to_fetch
                ]

                # Fetch secara concurrent — concurrency=100 optimal untuk VPN BPS
                # (lebih tinggi berisiko 429, lebih rendah terlalu lambat)
                results = await fetch_assignments_concurrent(cookies, urls_to_fetch, concurrency=settings.fetch_concurrency)
                timings["fetch"] = int((time.perf_counter() - phase_start) * 1000)

                # Upsert
                print("\n   💾 Menyimpan ke database (Bulk)...")
                phase_start = time.perf_counter()

                upserter = BatchUpserterBulk(session, batch_size=2000)
                for i, data in enumerate(results):
                    data["_survey_config_id"] = getattr(settings, "id", "default")
                    upserter.add(data)

                stats = upserter.finish()
                stats.total_skipped += skipped_delta
                stats.total_failed += len(to_fetch) - len(results)
            
            # (Note: BatchUpserterBulk handles commits internally or during finish)
        else:
            print("   ⚠️ Tidak ada assignment ditemukan untuk kriteria ini.")
            stats.total_fetched = 0
            stats.total_upserted = 0

        # Logging
        timings["upsert"] = int((time.perf_counter() - phase_start) * 1000)
        timings["total"] = int((time.perf_counter() - total_start) * 1000)
        
        log = log_sync_run(session, started_at, stats, survey_config_id=getattr(settings, "id", "default"), timings=timings)
        session.close()
        
    # Graceful shutdown of persistent API session
    if 'api' in locals():
        await api.close()

    print(f"\n🎉 Cycle selesai!")
    print(f"   {stats}")


async def test_login(settings: Settings):
    print("🧪 Test Mode: Login saja")
    async with async_playwright() as p:
        browser = await launch_stealth_browser(p)
        context = await new_stealth_context(browser, viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        ok, cookies, err_msg = await auto_login(page, settings.sso_username, settings.sso_password)
        if ok:
            print(f"✅ Login berhasil! Didapatkan {len(cookies)} cookies.")
        else:
            print("❌ Login gagal!")

        await context.close()
        await browser.close()


def run_scheduler(settings: Settings):
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_sync_cycle,
        trigger=IntervalTrigger(minutes=settings.interval_minutes),
        args=[settings],
        id="fasih_sync",
        name="FASIH-SM Sync Cycle",
        max_instances=1,
        misfire_grace_time=None,
        replace_existing=True,
    )

    print(f"⏰ Scheduler dimulai — interval: {settings.interval_minutes} menit")
    print(f"   Cycle pertama akan berjalan segera + setiap {settings.interval_minutes} menit setelahnya.")
    print(f"   Tekan Ctrl+C untuk berhenti.\n")

    scheduler.start()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_sync_cycle(settings))
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        print("\n\n🛑 Scheduler dihentikan oleh user.")
        scheduler.shutdown()
    finally:
        loop.close()


def main():
    parser = argparse.ArgumentParser(description="FasihNexus Sync Engine — Sinkronisasi data otomatis")
    parser.add_argument("--once", action="store_true", help="Jalankan 1 cycle saja")
    parser.add_argument("--test-login", action="store_true", help="Test login saja")
    parser.add_argument("--dry-run", action="store_true", help="Enumerate filter tanpa fetch")
    args = parser.parse_args()

    settings = Settings.from_env()
    errors = settings.validate()
    
    if errors and not args.dry_run:
        print("❌ Konfigurasi error:")
        for err in errors:
            print(f"   - {err}")
        sys.exit(1)

    if args.test_login:
        asyncio.run(test_login(settings))
    elif args.once or args.dry_run:
        asyncio.run(run_sync_cycle(settings, dry_run=args.dry_run))
    else:
        run_scheduler(settings)

if __name__ == "__main__":
    main()
```

### vpn/entrypoint.sh
```bash
#!/bin/sh

# Base config
mkdir -p /etc/openfortivpn

# Add public DNS fallback so we can always resolve akses.bps.go.id for auto-reconnect
echo "nameserver 8.8.8.8" >> /etc/resolv.conf
echo "nameserver 1.1.1.1" >> /etc/resolv.conf

# Clean up only specifically if we need to, but let's avoid wiping extra_hosts for now
# as it breaks fasih-sm.bps.go.id pinning from docker-compose.

# Wait a bit for Docker DNS to be fully ready
sleep 2

# Inject database IP into /etc/hosts so it survives DNS overrides
for i in 1 2 3; do
    DB_IP=$(getent hosts fasih-db | awk '{print $1}')
    [ -n "$DB_IP" ] && break
    sleep 1
done

if [ -n "$DB_IP" ]; then
    echo "📌 Mapping fasih-db -> $DB_IP in /etc/hosts"
    echo "$DB_IP fasih-db" >> /etc/hosts
fi

# Inject S3 IP into /etc/hosts
for i in 1 2 3; do
    S3_IP=$(getent hosts fasih-nexus-s3 | awk '{print $1}')
    if [ -z "$S3_IP" ]; then S3_IP=$(getent hosts s3 | awk '{print $1}'); fi
    [ -n "$S3_IP" ] && break
    sleep 1
done

if [ -n "$S3_IP" ]; then
    echo "📌 Mapping fasih-nexus-s3 -> $S3_IP in /etc/hosts"
    echo "$S3_IP fasih-nexus-s3" >> /etc/hosts
    echo "$S3_IP s3" >> /etc/hosts
fi

# 📉 Set eth0 MTU to 900 to prevent fragmentation on BPS network
echo "📉 Setting eth0 MTU to 900..."
ip link set eth0 mtu 900 2>/dev/null || true

GATEWAY_IP=$(ip route | grep default | awk '{print $3}')

# 🛠️ DYNAMIC FIX: Ensure internal Docker network stays on eth0
# We detect the actual subnet of eth0 to avoid hardcoding 172.16.0.0/12
# which might change in production environments like Coolify.
LOCAL_SUBNET=$(ip route show dev eth0 | grep "proto kernel" | awk '{print $1}')
if [ -n "$GATEWAY_IP" ] && [ -n "$LOCAL_SUBNET" ]; then
    echo "🛣️  Pinning local Docker network ($LOCAL_SUBNET) to eth0 via $GATEWAY_IP"
    ip route add "$LOCAL_SUBNET" dev eth0 via "$GATEWAY_IP" 2>/dev/null || true
fi
# Helper function to handle graceful shutdown
cleanup() {
    echo "🛑 Caught termination signal! Shutting down..."
    kill $(jobs -p) 2>/dev/null
    exit 0
}

trap cleanup INT TERM

# Background Watcher: Monitors DB for cookie changes and triggers restart
monitor_cookie_changes() {
    LAST_COOKIE=""
    while true; do
        sleep 10
        if [ -n "$DATABASE_URL" ] && [ -n "$VPN_PID" ]; then
            CURRENT_DB_COOKIE=$(psql "$DATABASE_URL" -t -A -c "SELECT value FROM system_settings WHERE key='vpn_cookie'" 2>/dev/null)
            if [ -n "$CURRENT_DB_COOKIE" ] && [ "$CURRENT_DB_COOKIE" != "$LAST_COOKIE" ]; then
                if [ -n "$LAST_COOKIE" ]; then
                    echo "🔄 DB Cookie changed! Triggering organic VPN reconnect..."
                    # Check if VPN_PID is actually running before killing
                    if [ -n "$VPN_PID" ] && kill -0 "$VPN_PID" 2>/dev/null; then
                        kill "$VPN_PID" 2>/dev/null
                    fi
                fi
                LAST_COOKIE="$CURRENT_DB_COOKIE"
            fi
        fi
    done
}

monitor_cookie_changes &

# SMART Route Enforcement Helper
apply_smart_routing() {
    echo "⏳ Waiting for interface tun0 or ppp0 to apply Smart Routing..."
    VPN_IF=""
    for i in $(seq 1 30); do
        if [ -d "/sys/class/net/tun0" ]; then VPN_IF="tun0"; break; fi
        if [ -d "/sys/class/net/ppp0" ]; then VPN_IF="ppp0"; break; fi
        sleep 1
    done

    if [ -n "$VPN_IF" ]; then
        # Wait for IP address
        for i in $(seq 1 10); do
            if ip addr show "$VPN_IF" 2>/dev/null | grep -q "inet "; then
                echo "✅ Interface $VPN_IF is fully UP. Applying route fixes..."
                break
            fi
            sleep 1
        done
        
        # Resolve target and force route
        TARGET_DOMAIN="fasih-sm.bps.go.id"
        echo "🔍 Resolving $TARGET_DOMAIN..."
        
        TARGET_IP=""
        for j in 1 2 3 4 5; do
            TARGET_IP=$(getent hosts "$TARGET_DOMAIN" | awk 'NR==1 {print $1}')
            [ -n "$TARGET_IP" ] && break
            sleep 2
        done
        
        if [ -n "$TARGET_IP" ]; then
            echo "📍 Site $TARGET_DOMAIN resolved to $TARGET_IP"
            
            grep -v "$TARGET_DOMAIN" /etc/hosts > /tmp/hosts && cat /tmp/hosts > /etc/hosts
            echo "$TARGET_IP $TARGET_DOMAIN" >> /etc/hosts
            echo "📌 Pinned $TARGET_DOMAIN -> $TARGET_IP in /etc/hosts"

            echo "🔌 Prioritizing Docker DNS and injecting BPS Nameservers..."
            echo -e "nameserver 127.0.0.11\nnameserver 10.10.11.11\nnameserver 10.10.11.12\n$(grep -vE '127.0.0.11|10.10.11.11|10.10.11.12' /etc/resolv.conf)" > /etc/resolv.conf
            
            if ! ip route get "$TARGET_IP" 2>/dev/null | grep -q "dev $VPN_IF"; then
                echo "🛠️  Forcing route for $TARGET_IP via $VPN_IF..."
                ip route add "$TARGET_IP"/32 dev "$VPN_IF" 2>/dev/null || true
            fi

            echo "🌐 Routing BPS DNS servers via $VPN_IF..."
            ip route add 172.16.2.2/32 dev "$VPN_IF" 2>/dev/null || true
            ip route add 172.16.2.3/32 dev "$VPN_IF" 2>/dev/null || true
            ip route add 10.0.0.0/8 dev "$VPN_IF" 2>/dev/null || true
            
            echo "📉 Setting $VPN_IF MTU to 900..."
            ip link set dev "$VPN_IF" mtu 900 || true
            
            echo "✅ BPS Routing updated."
        else
            echo "⚠️  Could not resolve $TARGET_DOMAIN (DNS Timeout)."
        fi
        return 0
    fi
    echo "❌ No VPN interface appeared. Skipping Smart Routing."
}

echo "🚀 Starting VPN Architecture (Self-Healing Enabled)..."

while true; do
    # --- Cleanup stale ppp0 interface to prevent 'Interface ppp0: Exist' on reconnect ---
    if ip link show ppp0 > /dev/null 2>&1; then
        echo "🧹 Removing stale ppp0 interface..."
        ip link set ppp0 down 2>/dev/null || true
        ip link delete ppp0 2>/dev/null || true
        sleep 1
    fi



    # Priority: database ALWAYS (env var is usually stale)
    COOKIE=""
    
    # Try reading cookie from PostgreSQL
    if [ -n "$DATABASE_URL" ]; then
        DB_COOKIE=$(psql "$DATABASE_URL" -t -A -c "SELECT value FROM system_settings WHERE key='vpn_cookie'" 2>/dev/null)
        if [ -n "$DB_COOKIE" ]; then
            COOKIE="$DB_COOKIE"
            echo "🔑 Fresh cookie loaded from database (Length: ${#COOKIE})"
        else
            echo "⏳ No cookie found in database. Triggering RPA auto-fetch via internet..."
            # RPA shares the same network namespace, so we use 127.0.0.1
            # We also pass the credentials we already have in our environment.
            curl -s -X POST "http://127.0.0.1:8000/vpn/auto-fetch" \
                -H "Content-Type: application/json" \
                -d "{\"sso_username\":\"$VPN_USER\", \"sso_password\":\"$VPN_PASS\"}" > /dev/null 2>&1 || true
            sleep 10
        fi
    fi

    # ONLY fallback to env var if DB is not available (Legacy mode)
    if [ -z "$DATABASE_URL" ] && [ -n "${VPN_COOKIE}" ]; then
        COOKIE="${VPN_COOKIE}"
        echo "🔑 Cookie loaded from env var (Legacy Fallback)"
    fi

    if [ -n "$COOKIE" ]; then
        VAL=$(echo "$COOKIE" | grep -o 'SVPNCOOKIE=[^;]*' | sed 's/^SVPNCOOKIE=//')
        if [ -z "$VAL" ]; then VAL="$COOKIE"; fi

        echo "🔗 Connecting with cookie (OpenConnect Mode)..."
        echo "🚀 Using DTLS + Android Spoofing for 'Lightning Fast' performance"
        
        # 📱 Android Spoofing for 'Lightning Fast' performance
        ANDROID_UA="Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36 FortiClient/7.2.4"
        
        # We try OpenConnect first as it supports DTLS
        openconnect --protocol=fortinet \
            "${VPN_HOST}:${VPN_PORT:-443}" \
            --cookie="SVPNCOOKIE=$VAL" \
            --useragent="$ANDROID_UA" \
            --os=android \
            --reconnect-timeout 60 \
            --passwd-on-stdin \
            --servercert "pin-sha256:u5HMq39pIYRefHyrvy+wZgxcW/a+Oa5N0x65brFLNsA=" \
            --background \
            --pid-file=/tmp/vpn.pid <<EOF
$VAL
EOF
        
        # Wait for the background process to start
        sleep 2
        if [ -f /tmp/vpn.pid ]; then
            VPN_PID=$(cat /tmp/vpn.pid)
            apply_smart_routing
            # 🛡️ Robust background wait: wait $PID only works for direct children.
            # Since openconnect daemonizes, we must use a kill -0 loop.
            echo "🛡️ Monitoring VPN PID $VPN_PID..."
            while kill -0 "$VPN_PID" 2>/dev/null; do
                sleep 5
            done
        else
            echo "⚠️ OpenConnect failed to start (PID file missing). Falling back to openfortivpn..."
            openfortivpn "${VPN_HOST}:${VPN_PORT:-443}" \
                --cookie="$VAL" \
                ${VPN_TRUSTED_CERT:+--trusted-cert "$VPN_TRUSTED_CERT"} \
                --set-dns=1 \
                --pppd-use-peerdns=1 &
            VPN_PID=$!
            apply_smart_routing
            wait $VPN_PID
        fi
    else
        echo "👤 Using Username/Password Mode (OpenConnect)..."
        # 📱 Android Spoofing for Password Mode
        ANDROID_UA="Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36 FortiClient/7.2.4"
        
        openconnect --protocol=fortinet \
            "${VPN_HOST}:${VPN_PORT:-443}" \
            -u "$VPN_USER" \
            --useragent="$ANDROID_UA" \
            --os=android \
            --passwd-on-stdin \
            --servercert "pin-sha256:u5HMq39pIYRefHyrvy+wZgxcW/a+Oa5N0x65brFLNsA=" \
            --background \
            --pid-file=/tmp/vpn.pid <<EOF
$VPN_PASS
EOF
            
        sleep 5 
        if [ -f /tmp/vpn.pid ] && kill -0 $(cat /tmp/vpn.pid) 2>/dev/null; then
            VPN_PID=$(cat /tmp/vpn.pid)
            apply_smart_routing
            wait $VPN_PID
        else
            echo "⚠️ OpenConnect failed to stay alive. Falling back to openfortivpn..."
            # ... (rest of fallback)
            cat <<EOF > /etc/openfortivpn/config
host = ${VPN_HOST}
port = ${VPN_PORT:-443}
username = ${VPN_USER}
password = ${VPN_PASS}
${VPN_TRUSTED_CERT:+trusted-cert = $VPN_TRUSTED_CERT}
set-dns = 1
pppd-use-peerdns = 1
EOF
            openfortivpn -c /etc/openfortivpn/config &
            VPN_PID=$!
            apply_smart_routing
            wait $VPN_PID
        fi
        echo "⚠️ VPN connection closed."
        VPN_PID=""
    fi

    EXIT_CODE=$?
    echo "⚠️ VPN Disconnected (Code: $EXIT_CODE). Cleaning up before reconnect..."
    
    # --- Self-Healing: If connection failed and we used a cookie, it might be stale ---
    if [ "$EXIT_CODE" -ne 0 ] && [ -n "$COOKIE" ] && [ -n "$DATABASE_URL" ]; then
        echo "🧐 VPN failed while using a cookie. Checking if it should be cleared..."
        # If openfortivpn exits with error, we assume the cookie might be dead.
        # We clear it from DB so the next loop can try Password Mode or wait for Auto-Fetch.
        psql "$DATABASE_URL" -c "DELETE FROM system_settings WHERE key='vpn_cookie'" > /dev/null 2>&1
        echo "🗑️  Stale cookie cleared from database to allow fallback/refresh."
        unset VPN_COOKIE
    fi
    
    # --- Cleanup stale ppp0 interface to prevent 'Interface ppp0: Exist' on reconnect ---
    if ip link show ppp0 > /dev/null 2>&1; then
        echo "🧹 Removing stale ppp0 interface..."
        ip link set ppp0 down 2>/dev/null || true
        ip link delete ppp0 2>/dev/null || true
        sleep 1
    fi
    
    echo "🔄 Reconnecting in 30 seconds..."
    sleep 30
done
```

### dashboard/entrypoint.sh
```bash
#!/bin/bash
set -e

echo "🚀 Starting Dashboard Container Entrypoint..."

# 1. Wait for Postgres to be ready (optional but good practice)
# Although depends_on with healthcheck is used, sometimes the app is too fast.
# We'll rely on the existing drizzle-kit push which will fail and retry if DB is not ready.

# 2. Run Database Migrations / Sync Schema
echo "🩺 Running Advanced Self-Healing Migration Check..."
# Single robust PL/pgSQL block to handle UUID conversion and sequence cleanup
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "
DO \$\$ 
DECLARE
    r RECORD;
BEGIN 
    SET statement_timeout = '60000'; -- 60 seconds
    RAISE NOTICE 'Starting self-healing process...';

    -- A. Force drop constraints that might block type changes
    BEGIN EXECUTE 'ALTER TABLE assignments DROP CONSTRAINT IF EXISTS assignments_survey_config_id_survey_configs_id_fk'; EXCEPTION WHEN OTHERS THEN NULL; END;
    BEGIN EXECUTE 'ALTER TABLE sync_logs DROP CONSTRAINT IF EXISTS sync_logs_survey_config_id_survey_configs_id_fk'; EXCEPTION WHEN OTHERS THEN NULL; END;

    -- B. Convert any 'id' or '*_id' columns that are still text/character varying to uuid
    FOR r IN (
        SELECT table_name, column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND (column_name = 'id' OR column_name LIKE '%_id')
          AND (data_type = 'text' OR data_type = 'character varying')
          AND table_name IN ('survey_configs', 'assignments', 'sync_logs', 'label_data', 'label_schemas')
    ) LOOP
        RAISE NOTICE 'Converting %.% from text to uuid...', r.table_name, r.column_name;
        BEGIN
            EXECUTE format('ALTER TABLE %I ALTER COLUMN %I TYPE uuid USING %I::uuid', r.table_name, r.column_name, r.column_name);
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'Could not convert %.%, skipping...', r.table_name, r.column_name;
        END;
    END LOOP;

    -- C. Clean up OWNED sequences by first dropping the column dependencies
    FOR r IN (
        SELECT t.relname as table_name, a.attname as column_name, c.relname as sequence_name
        FROM pg_class c
        JOIN pg_depend d ON d.objid = c.oid
        JOIN pg_class t ON t.oid = d.refobjid
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = d.refobjsubid
        WHERE c.relkind = 'S' AND d.deptype = 'a'
          AND (c.relname LIKE 'sync_logs%' OR c.relname LIKE 'label_data%' OR c.relname LIKE 'label_schemas%' OR c.relname LIKE 'visualization_configs%')
    ) LOOP
        RAISE NOTICE 'Cleaning up owned sequence %...', r.sequence_name;
        BEGIN 
            -- Drop both default and identity if they exist
            EXECUTE format('ALTER TABLE %I ALTER COLUMN %I DROP DEFAULT', r.table_name, r.column_name);
            EXECUTE format('ALTER TABLE %I ALTER COLUMN %I DROP IDENTITY IF EXISTS', r.table_name, r.column_name);
            EXECUTE format('DROP SEQUENCE IF EXISTS %I CASCADE', r.sequence_name);
        EXCEPTION WHEN OTHERS THEN 
            RAISE NOTICE 'Could not fully drop %, skipping...', r.sequence_name;
        END;
    END LOOP;

    -- D. Clean up any remaining ORPHAN sequences
    FOR r IN (
        SELECT relname as sequence_name
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind = 'S'
          AND (relname LIKE 'sync_logs%' OR relname LIKE 'label_data%' OR relname LIKE 'label_schemas%' OR relname LIKE 'visualization_configs%')
    ) LOOP
        RAISE NOTICE 'Dropping orphan sequence %...', r.sequence_name;
        BEGIN EXECUTE format('DROP SEQUENCE IF EXISTS %I CASCADE', r.sequence_name); EXCEPTION WHEN OTHERS THEN NULL; END;
    END LOOP;
    
    RAISE NOTICE 'Self-healing process completed successfully.';
END \$\$;
" || echo "   ⚠️ Self-healing check completed with some warnings (non-critical)."

echo "📦 Syncing database schema (drizzle-kit push)..."
# We use push for simplicity in this dev/stage environment.
# In strict production, we would use 'migrate'.
SYNC_SUCCESS=false
for i in {1..10}; do
  if bunx drizzle-kit push; then
    SYNC_SUCCESS=true
    break
  fi
  echo "   ⏳ DB not ready or sync failed, retrying ($i/10)..."
  sleep 5
done

if [ "$SYNC_SUCCESS" = false ]; then
  echo "❌ Database schema sync failed after 10 attempts. Exiting."
  exit 1
fi

# 3. Check if Seeding is needed
# We can check if a flag file exists or just run it (the seeder is idempotent).
echo "🌱 Running employee seeder..."
bun run server/db/seed-pegawai.ts

# 4. Start the main application
echo "🏁 Starting Elysia server..."
exec bun run server/index.ts
```

## 📜 Recent Activity
Last 5 Git Commits:
```
670e670 chore: harden infrastructure, optimize project dump, and sync coolify config
cb9481e chore: implement safe naming for database and harden RPA authentication timeouts
27e6115 chore(deploy): restructure compose files for production stability and local dev
976a054 fix(deploy): remove volume bind mounts to resolve Coolify OCI runtime errors
8287d79 fix(sync): resolve 403 image mirroring, 400 bad request, and stabilize vpn auto-bootstrap
```

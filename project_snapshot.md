# FasihNexus Architecture Snapshot
Generated at: Sun May 17 06:41:59 AM WIB 2026
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
|____benchmark_ux_lookup.sh
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
      - ENCRYPTION_KEY=[REDACTED]
      - BETTER_AUTH_SECRET=[REDACTED]
      - BETTER_AUTH_URL=${BETTER_AUTH_URL}
      - PUBLIC_BASE_URL=${PUBLIC_BASE_URL}
      - VPN_USER=${VPN_USER}
      - VPN_PASS=[REDACTED]
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
      - VPN_PASS=[REDACTED]
      - VPN_COOKIE=[REDACTED]
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
      - "autoheal=true"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - ENCRYPTION_KEY=[REDACTED]
      - PYTHONPATH=/app:/app/src
      - SKIP_DETAIL_FETCH=${SKIP_DETAIL_FETCH:-false}
      - FASIH_CONCURRENCY=${FASIH_CONCURRENCY:-3}
      - FETCH_CONCURRENCY=${FETCH_CONCURRENCY:-3}
      - TARGET_URL=${TARGET_URL:-https://fasih-sm.bps.go.id}
      - VPN_USER=${VPN_USER}
      - VPN_PASS=[REDACTED]
    depends_on:
      vpn:
        condition: service_started
    command: sh -c "echo '10.1.110.13 fasih-sm.bps.go.id' >> /etc/hosts && python -m uvicorn src.app:app --host 0.0.0.0 --port 8000"
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; \
        urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5); \
        urllib.request.urlopen('https://fasih-sm.bps.go.id', timeout=10)\""]
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
      - "autoheal=true"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - ENCRYPTION_KEY=[REDACTED]
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
      - "autoheal=true"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - S3_ACCESS_KEY=${S3_ACCESS_KEY:-fasihadmin}
      - S3_SECRET_KEY=[REDACTED]
      - S3_BUCKET=${S3_BUCKET:-survey-images}
      - S3_ENDPOINT=http://s3:8333
      - PYTHONPATH=/app:/app/src
    depends_on:
      vpn:
        condition: service_started
      rpa:
        condition: service_started
    command: python src/archiver.py
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import time, os; \
        hb = '/tmp/archiver_heartbeat'; \
        exit(0 if os.path.exists(hb) and (time.time() - os.path.getmtime(hb)) < 600 else 1)\""]
      interval: 60s
      timeout: 10s
      retries: 3
      start_period: 30s
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
      - WEED_FILER_POSTGRES_PASSWORD=[REDACTED]
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
      - SEAWEEDFS_S3_SECRET_KEY=[REDACTED]
    depends_on:
      - filer
    restart: unless-stopped

  # --- Infrastructure Watchdog ---
  autoheal:
    image: willfarrell/autoheal:latest
    container_name: fasih-nexus-autoheal
    networks:
      - fasih_internal
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - AUTOHEAL_CONTAINER_LABEL=autoheal
      - AUTOHEAL_INTERVAL=30
    restart: unless-stopped

networks:
  fasih_internal:
    driver: bridge
    driver_opts:
      com.docker.network.driver.mtu: 1400
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
  export BETTER_AUTH_SECRET=[REDACTED]

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
            VPN_PASS=[REDACTED]
            
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
      # CRITICAL: BETTER_AUTH_URL and PUBLIC_BASE_URL MUST match your Coolify domain
      - DATABASE_URL=${DATABASE_URL:-postgres://fasih:${POSTGRES_PASSWORD}@fasih-db:5432/fasih_dashboard}
      - RPA_URL=http://vpn:8000        # Talking to RPA via VPN container
      - VPN_AUTH_URL=http://vpn:8001   # Talking to VPN-Auth via VPN container
      - ENCRYPTION_KEY=[REDACTED]
      - BETTER_AUTH_SECRET=[REDACTED]
      - BETTER_AUTH_URL=${BETTER_AUTH_URL}
      - PUBLIC_BASE_URL=${PUBLIC_BASE_URL}
      - S3_ACCESS_KEY=${S3_ACCESS_KEY:-fasihadmin}
      - S3_SECRET_KEY=[REDACTED]
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
    dns:
      - 127.0.0.11
      - 172.16.2.2
      - 172.16.2.3
      - 8.8.8.8
    environment:
      - DATABASE_URL=${DATABASE_URL:-postgres://fasih:${POSTGRES_PASSWORD}@fasih-db:5432/fasih_dashboard}
      - VPN_HOST=akses.bps.go.id
      - VPN_TEST_URL=https://fasih-sm.bps.go.id
      - VPN_USER=${VPN_USER}
      - VPN_PASS=[REDACTED]
      - VPN_COOKIE=[REDACTED]
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
    labels:
      - "autoheal=true"
    environment:
      - DATABASE_URL=${DATABASE_URL:-postgres://fasih:${POSTGRES_PASSWORD}@fasih-db:5432/fasih_dashboard}
      - ENCRYPTION_KEY=[REDACTED]
      - PYTHONPATH=/app:/app/src
      - VPN_USER=${VPN_USER}
      - VPN_PASS=[REDACTED]
    depends_on:
      vpn:
        condition: service_started
    command: sh -c "echo '10.1.110.13 fasih-sm.bps.go.id' >> /etc/hosts && python -m uvicorn src.app:app --host 0.0.0.0 --port 8000"
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; \
        urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5); \
        urllib.request.urlopen('https://fasih-sm.bps.go.id', timeout=10)\""]
      interval: 45s
      timeout: 20s
      retries: 5
    restart: unless-stopped

  vpn-auth:
    image: fasih-nexus-rpa:latest
    container_name: fasih-nexus-vpn-auth
    network_mode: "service:vpn" # Also behind VPN for SSO reliability
    labels:
      - "autoheal=true"
    environment:
      - DATABASE_URL=${DATABASE_URL:-postgres://fasih:${POSTGRES_PASSWORD}@fasih-db:5432/fasih_dashboard}
      - ENCRYPTION_KEY=[REDACTED]
      - PYTHONPATH=/app:/app/src
      - VPN_USER=${VPN_USER}
      - VPN_PASS=[REDACTED]
    depends_on:
      vpn:
        condition: service_started
    command: sh -c "echo '10.1.110.13 fasih-sm.bps.go.id' >> /etc/hosts && python -m uvicorn src.app:app --host 0.0.0.0 --port 8001"
    restart: unless-stopped

  archiver:
    image: fasih-nexus-rpa:latest
    container_name: fasih-nexus-archiver
    network_mode: "service:vpn"
    labels:
      - "autoheal=true"
    environment:
      - DATABASE_URL=${DATABASE_URL:-postgres://fasih:${POSTGRES_PASSWORD}@fasih-db:5432/fasih_dashboard}
      - S3_ACCESS_KEY=${S3_ACCESS_KEY:-fasihadmin}
      - S3_SECRET_KEY=[REDACTED]
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
      - POSTGRES_PASSWORD=[REDACTED]
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
      - WEED_FILER_POSTGRES_PASSWORD=[REDACTED]
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
      - SEAWEEDFS_S3_SECRET_KEY=[REDACTED]
    depends_on:
      - filer
    restart: unless-stopped

  # --- Infrastructure Watchdog ---
  autoheal:
    image: willfarrell/autoheal:latest
    container_name: fasih-nexus-autoheal
    networks:
      - fasih_internal
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - AUTOHEAL_CONTAINER_LABEL=autoheal
      - AUTOHEAL_INTERVAL=30
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

# Function to sanitize sensitive data
sanitize_content() {
    sed -E 's/(VPN_PASS|POSTGRES_PASSWORD|ENCRYPTION_KEY|BETTER_AUTH_SECRET|S3_SECRET_KEY|VPN_COOKIE)=.*/\1=[REDACTED]/g'
}

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
    cat "$file" | sanitize_content
    echo '```'
    echo ""
  done

  echo "## 📜 Project Documentation"
  [ -f "GEMINI.md" ] && echo "### GEMINI.md" && echo '```markdown' && cat GEMINI.md && echo '```' && echo ""
  [ -f "README.md" ] && echo "### README.md" && echo '```markdown' && cat README.md && echo '```' && echo ""

  echo "## ⚙️ Configuration & Environment"
  # Include .env (raw as requested) and main package definitions
  [ -f ".env" ] && echo "### .env" && echo '```bash' && cat .env | sanitize_content && echo '```'
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
    "rpa/src/api_client.py"
    "rpa/src/worker/job_runner.py"
    "rpa/src/db/repository.py"
    "rpa/src/connectivity.py"
    "rpa/src/state.py"
    "rpa/src/pages/detail_page.py"
    "rpa/src/routes/sync.py"
    "rpa/src/worker/scheduler.py"
    "rpa/src/worker/queue.py"
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
      cat "$file" | sanitize_content
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

### ./benchmark_ux_lookup.sh
```yaml
#!/bin/bash

# RPA berbagi network dengan container VPN (network_mode: service:vpn)
# Port 8000 tidak di-expose ke host — akses lewat IP VPN container di Docker bridge network
API_URL="http://172.18.0.8:8000/lookup/metadata"
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
POSTGRES_PASSWORD=[REDACTED]
POSTGRES_DB=fasih_dashboard
DATABASE_URL=postgresql://fasih:changeme_generate_random@fasih-db:5432/fasih_dashboard

# RPA - encryption key for SSO passwords
ENCRYPTION_KEY=[REDACTED]

# VPN BPS
VPN_HOST=akses.bps.go.id
VPN_USER=arinif@bps.go.id
VPN_PASS=[REDACTED]
VPN_TRUSTED_CERT=de74481c56635274320d58e3267de977acbd6ea8cdbc5450042010d7e9544659
VPN_COOKIE=[REDACTED]
SKIP_DETAIL_FETCH=false

# SeaweedFS Image Vault
S3_ACCESS_KEY=cdcadmin
S3_SECRET_KEY=[REDACTED]
S3_BUCKET=survey-images
S3_ENDPOINT=http://s3:8333
STORAGE_LOCAL_DOMAIN=http://127.0.0.1:3000
PUBLIC_BASE_URL=http://127.0.0.1:9000

# Better Auth
BETTER_AUTH_SECRET=[REDACTED]
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
    "build": "cd client && bunx quasar build",
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
  id: uuid("id").primaryKey(),
  surveyConfigId: uuid("survey_config_id").references(() => surveyConfigs.id, { onDelete: "cascade" }),
  codeIdentity: text("code_identity"),
  surveyPeriodId: uuid("survey_period_id"),
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
            from auth import fetch_vpn_cookie, sync_cookie_to_db, get_current_cookie, FETCH_LOCK
            async def bootstrap_vpn():
                # Delay slightly to let the infrastructure stabilize (DB, VPN container, etc)
                await asyncio.sleep(10)
                
                async with FETCH_LOCK:
                    # CHECK DB FIRST: Don't fetch if we already have a cookie
                    # This prevents redundant Playwright sessions on every RPA restart
                    existing = await get_current_cookie()
                    if existing:
                        print("ℹ️ [Startup] VPN Cookie already exists in DB. Skipping auto-bootstrap.")
                        return

                    print(f"🌐 [Startup] No cookie found. Auto-bootstrapping VPN for {vpn_user}...")
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
    
    # On shutdown
    from state import sync_state
    sync_state.is_shutting_down = True
    print("🛑 Shutdown: Signal received. Setting is_shutting_down = True for all workers.")

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

# Global lock to prevent multiple simultaneous Playwright sessions for cookie fetching
FETCH_LOCK = asyncio.Lock()

async def get_current_cookie():
    """Retrieve the current vpn_cookie from the database."""
    try:
        db_url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute("SELECT value FROM system_settings WHERE key = 'vpn_cookie'")
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None

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
        
        # 5. Fill Credentials using direct JS injection (Bypass UI stalling)
        print(f"🚀 [Auth] Injecting credentials via JS...")
        await page.evaluate(f"""() => {{
            const userField = document.querySelector('#username');
            const passField = document.querySelector('#password');
            if (userField) userField.value = '{username}';
            if (passField) passField.value = '{password}';
        }}""")
        
        # Fast submit
        await page.click("#kc-login", force=True)
        
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

### rpa/src/api_client.py
```python
import os
import aiohttp
import ssl
import re
from typing import List, Dict, Tuple, Optional

import asyncio
from functools import wraps

TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")

class FasihAuthError(Exception):
    """Exception raised when SSO session is expired or redirected to login page."""
    pass

def with_retry(retries=3, delay=5):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_err = None
            for attempt in range(1, retries + 1):
                try:
                    return await func(*args, **kwargs)
                except FasihAuthError:
                    raise
                except Exception as e:
                    last_err = e
                    print(f"   ⚠️ [API] Attempt {attempt}/{retries} failed: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
            print(f"   ❌ [API] Failed after {retries} attempts.")
            raise last_err
        return wrapper
    return decorator

class FasihApiClient:
    def __init__(self, cookies: Dict[str, str]):
        self.cookies = cookies
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE
        
        # Use a persistent cookie jar and session
        self.jar = aiohttp.CookieJar(unsafe=True)
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Pre-populate jar with initial cookies from Playwright
        from yarl import URL
        target_url = URL(TARGET_URL)
        for name, value in self.cookies.items():
            self.jar.update_cookies({name: value}, target_url)

    async def __aenter__(self):
        """Open a single persistent ClientSession for the entire sync cycle."""
        # Initial headers bootstrap
        headers = self._get_headers()

        self._session = aiohttp.ClientSession(
            cookie_jar=self.jar,
            headers=headers,
            connector=aiohttp.TCPConnector(ssl=self.ssl_ctx, limit=100, limit_per_host=30),
            timeout=aiohttp.ClientTimeout(total=45, connect=15)
        )
        
        # Optional: Bootstrap hit to ensure session and F5 cookies are active
        try:
            async with self._session.get(f"{TARGET_URL}/") as resp:
                if resp.status == 200:
                    print(f"   🌐 [API] Session bootstrapped successfully (HTTP 200)")
                else:
                    print(f"   ⚠️ [API] Session bootstrap returned status {resp.status}")
        except Exception as e:
            print(f"   ⚠️ [API] Session bootstrap failed: {e}")
        
        # Log active cookies sample for debugging (masked for security)
        try:
            sample = []
            for c in self.jar:
                val = c.value[:4] + "..." if len(c.value) > 4 else "***"
                sample.append(f"{c.key}={val}")
            print(f"   🐛 [API] Active Cookies: {', '.join(sample)}")
        except:
            pass

        return self

    def _get_headers(self) -> Dict[str, str]:
        """Dynamically build headers with latest XSRF-TOKEN from cookie jar."""
        headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Mobile Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Requested-With": "XMLHttpRequest",
        }
        
        # Try to find XSRF-TOKEN in the cookie jar
        xsrf_token = None
        for cookie in self.jar:
            if cookie.key == "XSRF-TOKEN":
                from urllib.parse import unquote
                raw_token = cookie.value
                xsrf_token = unquote(raw_token)
                if raw_token != xsrf_token:
                    print(f"   🐛 [API] Header XSRF-TOKEN unquoted: {raw_token[:5]}... -> {xsrf_token[:5]}...")
                break
        
        if xsrf_token:
            headers["X-XSRF-TOKEN"] = xsrf_token
            
        return headers

    async def close(self):
        await self.__aexit__()

    async def __aexit__(self, *args):
        if self._session:
            await self._session.close()
            self._session = None

    @property
    def session(self) -> aiohttp.ClientSession:
        if not self._session:
            self._session = aiohttp.ClientSession(
                cookie_jar=self.jar,
                headers=self._get_headers(),
                connector=aiohttp.TCPConnector(ssl=self.ssl_ctx, limit=100, limit_per_host=30),
                timeout=aiohttp.ClientTimeout(total=45, connect=15)
            )
        return self._session

    # Keep backward-compat for old code that calls create_session()
    async def create_session(self) -> aiohttp.ClientSession:
        """Deprecated: returns self._session if open, otherwise creates a temp one."""
        if self._session and not self._session.closed:
            class _Noop:
                """Fake async context manager wrapping existing session."""
                def __init__(self, s): self._s = s
                async def __aenter__(self): return self._s
                async def __aexit__(self, *a): pass
            return _Noop(self._session)  # type: ignore
        # Fallback for any call outside context manager
        return aiohttp.ClientSession(
            cookie_jar=self.jar,
            headers=self._get_headers(),
            connector=aiohttp.TCPConnector(ssl=self.ssl_ctx, limit=100),
            timeout=aiohttp.ClientTimeout(total=45, connect=15)
        )

    @with_retry()
    async def get_survey_id(self, survey_name: str) -> Optional[str]:
        """Cari Survey ID berdasarkan nama survey"""
        print(f"📋 [API] Mencari survey: '{survey_name}'...")
        
        path = "survey/api/v1/surveys/datatable?surveyType=Pencacahan"
        target_clean = re.sub(r'[^a-z0-9]', '', survey_name.lower())
        
        page = 0
        while True:
            payload = {
                "pageNumber": page,
                "pageSize": 100,
                "sortBy": "CREATED_AT",
                "sortDirection": "DESC",
                "keywordSearch": ""
            }
            
            body = await self._request("POST", path, json=payload)
            if not body or not body.get("success"):
                return None
                
            data = body.get("data", {}).get("content", [])
            if not data:
                break
                
            for survey in data:
                s_name = survey.get("name", "")
                s_clean = re.sub(r'[^a-z0-9]', '', s_name.lower())
                if target_clean and (target_clean in s_clean or s_clean in target_clean):
                    s_id = survey.get("id")
                    print(f"   ✅ [API] Ditemukan: '{s_name}' → ID: {s_id}")
                    return s_id
                    
            total_pages = body.get("data", {}).get("totalPage", 1)
            if page >= total_pages - 1:
                break
            
            page += 1
                    
        print(f"   ❌ [API] Survey '{survey_name}' tidak ditemukan dari seluruh halaman.")
        return None

    @with_retry()
    async def get_survey_period_and_roles(self, survey_id: str) -> Tuple[Optional[str], List[str], Optional[str]]:
        """Mendapatkan Active Period ID, semua Role ID, dan surveyRoleGroupId untuk suatu survey."""
        print(f"   📋 [API] Mencari periode survey dan role untuk ID: {survey_id}...")
        
        path = f"survey/api/v1/survey-periods?surveyId={survey_id}"
        body = await self._request("GET", path)
        if not body:
            return None, [], None
            
        periods = body.get("data", [])
        if not periods:
            print(f"   ❌ [API] Tidak ada periode ditemukan.")
            return None, [], None
            
        period_id = periods[0].get("id")
        
        # Also check /my endpoint
        my_body = await self._request("GET", f"survey/api/v1/survey-periods/my?surveyId={survey_id}")
        if my_body and my_body.get("data"):
            period_id = my_body["data"][0].get("id")
            print(f"   📅 [API] Menggunakan period dari /my: {period_id}")
        
        # Fetch role ID + role group ID
        role_body = await self._request("GET", f"survey/api/v1/survey-roles?surveyId={survey_id}")
        if not role_body:
            return period_id, [], None

        roles = role_body.get("data", [])
        role_ids = [r.get("id") for r in roles] if roles else []
        role_group_id = roles[0].get("surveyRoleGroupId") if roles else None
            
        print(f"   ✅ [API] Period: {period_id}, {len(role_ids)} roles, group: {role_group_id}")
        return period_id, role_ids, role_group_id
        return None, [], None

    @with_retry()
    async def get_region_metadata(self, provinsi_name: Optional[str], kabupaten_name: Optional[str], survey_id: str) -> Tuple[Optional[str], Optional[str], Optional[str], str]:
        """Mencari UUID region berdasarkan teks filter UI."""
        print("   🔍 [API] Menarik struktur metadata region...")
        
        # Get Region Group ID
        group_id = "82af087a-d063-48b9-8633-71c84c4e7422"  # Standard fallback
        s_data = await self._request("GET", f"survey/api/v1/surveys/{survey_id}")
        if s_data and s_data.get("data"):
            fetched_group = s_data["data"].get("regionGroupId")
            if fetched_group:
                group_id = fetched_group
                print(f"   ✅ [API] Extracted dynamic regionGroupId: {group_id}")

        # Get Provincial Region Code
        prov_uuid, prov_full_code = None, None
        if provinsi_name:
            data = await self._request("GET", f"region/api/v1/region/level1?groupId={group_id}")
            if data:
                regions = data.get("data", [])
                clean_prov_name = re.sub(r'\[\d+\]', '', provinsi_name).lower().strip()
                search_words = [w for w in clean_prov_name.split(' ') if len(w) > 2]
                for r in regions:
                    label = r.get("name", "").lower()
                    if all(word in label for word in search_words):
                        prov_uuid = r.get("id")
                        prov_full_code = r.get("fullCode")
                        break
                            
        # Get Kabupaten Region UUID
        kab_uuid, kab_full_code = None, None
        if kabupaten_name and prov_full_code:
            data = await self._request("GET", f"region/api/v1/region/level2?groupId={group_id}&level1FullCode={prov_full_code}")
            if data:
                regions = data.get("data", [])
                clean_kab_name = re.sub(r'\[\d+\]', '', kabupaten_name).lower().strip()
                search_words = [w for w in clean_kab_name.split(' ') if len(w) > 2]
                for r in regions:
                    label = r.get("name", "").lower()
                    if all(word in label for word in search_words):
                        kab_uuid = r.get("id")
                        kab_full_code = r.get("fullCode")
                        break
            
        region_uuid_for_filter = kab_uuid if kab_uuid else prov_uuid
        region_full_code = kab_full_code if kab_full_code else prov_full_code
        return prov_uuid, region_uuid_for_filter, region_full_code, group_id

    @with_retry()
    async def get_users_by_region(
        self, period_id: str, role_ids: List[str],
        region_code: str, role_group_id: Optional[str] = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """Mendapatkan pengawas & pencacah."""
        pengawas_list = []
        pencacah_list = []
        seen_ids: set = set()

        def _add_user(user: dict, is_pencacah: bool):
            uid = user.get('userId') or user.get('id')
            if not uid or uid in seen_ids:
                return
            seen_ids.add(uid)
            entry = {
                'fullname': user.get('fullname', '') or user.get('user', {}).get('fullname', ''),
                'username': user.get('username', '') or user.get('user', {}).get('username', ''),
                'userId': uid,
                'isPencacah': is_pencacah,
                'description': user.get('description', ''),
            }
            if is_pencacah: pencacah_list.append(entry)
            else: pengawas_list.append(entry)

        for role_id in role_ids:
            path = f"survey/api/v1/survey-period-role-users/region?surveyPeriodId={period_id}&surveyRoleId={role_id}&regionCode={region_code}"
            body = await self._request("GET", path)
            if body and body.get("data"):
                for user in body["data"]:
                    _add_user(user, user.get('isPencacah', False))

        if role_group_id:
            for role_id in role_ids:
                dt_url = f"analytic/api/v2/survey-period-role-user/datatable?surveyPeriodId={period_id}&surveyRoleGroupId={role_group_id}&surveyRoleId={role_id}"
                payload = {"pageNumber": 0, "pageSize": 200, "sortBy": "ID", "sortDirection": "ASC", "keywordSearch": ""}
                body = await self._request("POST", dt_url, json=payload)
                if body and body.get("data"):
                    for user in body["data"].get("searchData", []):
                        role_info = user.get("surveyRole", {})
                        is_pencacah = role_info.get("isPencacah", False)
                        flat = {
                            'userId': user.get("userId"),
                            'fullname': user.get("user", {}).get("fullname", ""),
                            'username': user.get("user", {}).get("username", ""),
                            'description': role_info.get("description", ""),
                            'isPencacah': is_pencacah,
                        }
                        _add_user(flat, is_pencacah)

        return pengawas_list, pencacah_list

    @with_retry()
    async def get_assignments_metadata(self, period_id: str, prov_uuid: Optional[str] = None, kab_uuid: Optional[str] = None, 
                                       kec_uuid: Optional[str] = None, desa_uuid: Optional[str] = None,
                                       pengawas_id: Optional[str] = None, pencacah_id: Optional[str] = None, region_group_id: Optional[str] = None) -> List[Dict]:
        """Tarik Assignment Datatable hingga habis."""
        path = "analytic/api/v2/assignment/datatable-all-user-survey-periode"
        all_metadata = []
        page_start = 0
        page_size = 1000
        while True:
            payload = {
                "draw": (page_start // page_size) + 1,
                "columns": [{"data": "id", "name": "", "searchable": True, "orderable": False, "search": {"value": "", "regex": False}}],
                "order": [{"column": 0, "dir": "asc"}],
                "start": page_start,
                "length": page_size,
                "search": {"value": "", "regex": False},
                "assignmentExtraParam": {
                    "region1Id": prov_uuid, "region2Id": kab_uuid, "region3Id": kec_uuid, "region4Id": desa_uuid,
                    "surveyPeriodId": period_id, "assignmentErrorStatusType": -1,
                    "filterTargetType": "ALL" if not (pencacah_id or pengawas_id) else "TARGET_ONLY",
                    "regionGroupId": region_group_id
                }
            }
            if pencacah_id or pengawas_id:
                payload["assignmentExtraParam"]["currentUserId"] = pencacah_id or pengawas_id
            
            body = await self._request("POST", path, json=payload)
            if not body: break
            
            search_data = body.get("data", body.get("searchData", []))
            if not search_data: break

            for item in search_data:
                rec_id = item.get("id") or item.get("_id") or item.get("assignmentId")
                remote_date_raw = (item.get("dateModified") or item.get("updatedAt") or item.get("dateModifiedRemote") or item.get("date_modified"))
                
                def _norm_date(d_raw):
                    if not d_raw: return ""
                    s = str(d_raw).strip()
                    if s.isdigit() and len(s) == 14: return s
                    from datetime import datetime, timedelta
                    try:
                        dt = datetime.strptime(s, "%b %d, %Y, %I:%M:%S %p")
                        return (dt - timedelta(hours=7)).strftime("%Y%m%d%H%M%S")
                    except: return re.sub(r'\D', '', s)[:14]

                if rec_id:
                    all_metadata.append({"id": rec_id, "dateModifiedRemote": _norm_date(remote_date_raw)})

            if len(search_data) < page_size: break
            page_start += page_size
        
        return all_metadata

    @with_retry(retries=3, delay=2)
    async def get_assignment_detail(self, assignment_id: str) -> Optional[Dict]:
        """Fetch the latest assignment detail JSON (includes fresh S3 links)."""
        url = f"{TARGET_URL}/assignment-general/api/assignment/get-by-id-with-data-for-scm?id={assignment_id}"
        print(f"   🔄 [API] Refreshing detail for assignment: {assignment_id}...")
        
        async with await self.create_session() as session:
            async with session.get(url, headers=self._get_headers()) as resp:

                if resp.status != 200:
                    text = await resp.text()
                    print(f"   ❌ [API] Failed to fetch detail (HTTP {resp.status}): {text[:200]}")
                    return None
                    
                body = await resp.json()
                if body and body.get("success"):
                    data = body.get("data")
                    if data:
                        # Log data keys to trace structure
                        keys = list(data.keys()) if isinstance(data, dict) else "list"
                        print(f"   ✨ [API] Detail fetch success. Top-level keys: {keys}")
                    return data
                
                print(f"   ❌ [API] Detail fetch failed success=False. Body: {body}")
                return None

    @with_retry(retries=3, delay=2)
    async def get_fresh_image_urls(self, survey_period_id: str, assignments_payload: list[dict]) -> dict:
        """
        Request new S3 presigned URLs for expired images.
        Payload structure matching BPS backend:
        [{"assignmentId": "...", "fileNames": ["filename.jpg", ...]}]
        """
        try:
            url = f"{TARGET_URL}/assignment-general/api/image/presigned-url-get?surveyPeriodId={survey_period_id}"
            
            # Sanitize payload: Ensure fileNames only contain the simplified identifier (basename),
            # stripping any surveyPeriodId/ or other path prefixes to avoid 400 Bad Request errors.
            sanitized_payload = []
            for item in assignments_payload:
                clean_filenames = []
                for fn in item.get("fileNames", []):
                    clean_fn = fn.split("/")[-1].split("?")[0]
                    clean_filenames.append(clean_fn)
                sanitized_payload.append({
                    "assignmentId": item.get("assignmentId"),
                    "fileNames": clean_filenames
                })
            
            print(f"   🔄 [API] Requesting {sum(len(a.get('fileNames', [])) for a in sanitized_payload)} fresh presigned URLs...", flush=True)
            
            headers = self._get_headers()
            print(f"   🐛 [API] X-XSRF-TOKEN in header: {headers.get('X-XSRF-TOKEN', 'MISSING')[:10]}...", flush=True)

            async with await self.create_session() as session:
                async with session.post(url, json=sanitized_payload, headers=headers, timeout=45) as resp:
                    status = resp.status
                    print(f"   🐛 [API] POST /presigned-url-get returned status {status}", flush=True)
                    
                    if status != 200:
                        text = await resp.text()
                        print(f"   ❌ [API] Failed to fetch fresh presigned URLs (HTTP {status})", flush=True)
                        print(f"   🐛 [API] Request URL: {url}", flush=True)
                        print(f"   🐛 [API] Error Body: {text[:500]}", flush=True)
                        return None
                    
                    raw_data = await resp.json()
                    print(f"   🐛 [API] raw_data received: {str(raw_data)[:100]}...", flush=True)
                    
                    # Unwrap BPS API standard response { "success": true, "data": ... }
                    if isinstance(raw_data, dict) and "success" in raw_data and "data" in raw_data:
                        actual_data = raw_data.get("data", [])
                    else:
                        actual_data = raw_data
                        
                    result_map = {}
                    if isinstance(actual_data, list):
                        for item in actual_data:
                            if isinstance(item, dict):
                                urls_list = item.get("presignedUrls", [])
                                for url_obj in urls_list:
                                    if isinstance(url_obj, dict) and "fileName" in url_obj and "presignedUrl" in url_obj:
                                        result_map[url_obj["fileName"]] = url_obj["presignedUrl"]
                    elif isinstance(actual_data, dict):
                        result_map = actual_data
                    
                    print(f"   🐛 [API] Found {len(result_map)} urls in result_map", flush=True)
                    return result_map
        except Exception as e:
            print(f"   ❌ [API] Error fetching presigned URLs: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return None

    @with_retry(retries=3, delay=2)
    async def download_content(self, url: str) -> Optional[bytes]:
        """Download raw content from a URL using the authenticated session, forcing cookies for cross-domain S3."""
        if not self._session:
            return None
            
        # Manually extract cookies from jar to bypass domain restrictions in aiohttp
        cookie_header = ""
        try:
            cookies = []
            for cookie in self.jar:
                cookies.append(f"{cookie.key}={cookie.value}")
            cookie_header = "; ".join(cookies)
        except:
            pass

        headers = self._get_headers()
        if cookie_header:
            headers["Cookie"] = cookie_header
            
        async with self._session.get(url, headers=headers, timeout=60) as resp:
            if resp.status == 200:
                return await resp.read()
            
            print(f"   ❌ [API] Content download failed (HTTP {resp.status}): {url[:100]}...")
            return None
```

### rpa/src/worker/job_runner.py
```python
import os
import asyncio
from datetime import datetime, timezone
from playwright.async_api import async_playwright

from db.connection import init_db, get_session, reset_engine
from db.models import SyncLog, SystemSettings, Assignment
from db.repository import SyncStats

from state import sync_state
from schemas import SyncRequest
from auth import auto_login, launch_stealth_browser, new_stealth_context
from api_client import FasihApiClient
from pages.survey_navigator import find_survey_id, navigate_to_data_tab
from pages.filter_rotator import iterate_filters, get_total_entries
from pages.assignment_page import get_all_assignments_metadata

from worker.fast_mode import run_fast_sync
from worker.full_mode import run_full_sync
from connectivity import ensure_connected, FasihConnectionError
from api_client import FasihAuthError


def _progress(phase: str, label: str, **kwargs):
    """Update sync_state.progress with current phase info."""
    sync_state.progress.phase = phase
    sync_state.progress.phase_label = label
    for k, v in kwargs.items():
        if hasattr(sync_state.progress, k):
            setattr(sync_state.progress, k, v)
    print(f"📊 [PROGRESS] [{phase}] {label}")

async def _run_single_job(sync_log: SyncLog, req: SyncRequest):
    """Run the actual sync cycle for one job."""
    
    # Check and self-heal connectivity (VPN/Cookie)
    await ensure_connected()
    
    SKIP_DETAIL_FETCH = os.getenv("SKIP_DETAIL_FETCH", "false").lower() == "true"

    reset_engine()
    init_db()
    session = get_session()

    # Update log to running
    log = session.query(SyncLog).get(sync_log.id)
    log.status = "running"
    log.started_at = datetime.now(timezone.utc)
    session.commit()

    sync_state.is_running = True
    sync_state.current_survey = req.survey_name
    sync_state.current_survey_config_id = req.survey_config_id
    sync_state.current_job_id = log.id
    sync_state.started_at = datetime.now(timezone.utc)
    sync_state.progress.reset()

    stats = SyncStats()

    try:
        # Global timeout to prevent infinite hang (e.g. DNS or asyncio deadlock)
        async with asyncio.timeout(1200): # 20 minutes
            async with async_playwright() as p:
                browser = await launch_stealth_browser(p)
                context = await new_stealth_context(
                    browser,
                    viewport={"width": 1280, "height": 800}
                )

                try:
                    page = await context.new_page()

                    # Login
                    _progress("login", "🔐 Login SSO BPS via Playwright...")
                    login_ok, cookie_dict, err_msg = await auto_login(page, req.sso_username, req.sso_password)
                    if not login_ok:
                        raise Exception(f"Login gagal: {err_msg}")

                    # Close browser right after login!
                    await browser.close()
                    browser = None  # To avoid closing twice in finally
                    
                    # Save cookies to DB for self-healing archiver (Multi-survey support)
                    try:
                        import json
                        db_session = get_session()
                        setting = db_session.query(SystemSettings).filter_by(key="sso_cookies").first()
                        if setting:
                            setting.value = json.dumps(cookie_dict)
                            setting.updated_at = datetime.now(timezone.utc)
                        else:
                            setting = SystemSettings(key="sso_cookies", value=json.dumps(cookie_dict))
                            db_session.add(setting)
                        db_session.commit()
                        db_session.close()
                        print("   💾 SSO cookies saved to DB (Ready for multi-survey self-healing).")
                    except Exception as db_e:
                        print(f"   ⚠️ Warning: Failed to save SSO cookies to DB: {db_e}")

                    async with FasihApiClient(cookie_dict) as api:

                        print("\n--- FASE 2: Resolving API Metadata ---")
                        _progress("resolve_survey", f"🔍 Mencari survey: {req.survey_name}...")
                        survey_id = await api.get_survey_id(req.survey_name)
                        if not survey_id:
                            raise Exception(f"Survey '{req.survey_name}' tidak ditemukan")

                        _progress("resolve_survey", "📅 Mengambil periode dan role...")
                        period_id, role_ids, survey_role_group_id = await api.get_survey_period_and_roles(survey_id)
                        if not period_id or not role_ids:
                            raise Exception(f"Period/Role tidak ditemukan untuk survey {survey_id}")

                        _progress("resolve_survey", "🗺️ Mengambil metadata region...")
                        prov_uuid, region_filter, kab_full_code, region_group_id = await api.get_region_metadata(req.filter_provinsi, req.filter_kabupaten, survey_id)

                        # Safety Gate: Jika provinsi diisi tapi tidak ketemu di API, jangan lanjut.
                        # Ini mencegah robot menarik data se-Indonesia/se-Provinsi secara tidak sengaja yang memicu timeout.
                        if req.filter_provinsi and not prov_uuid:
                            raise Exception(f"Gagal memetakan wilayah: '{req.filter_provinsi}' tidak ditemukan di API FASIH")
                        
                        if req.filter_kabupaten and not kab_full_code:
                            print(f"   ⚠️ Warning: Kabupaten '{req.filter_kabupaten}' tidak ter-resolve, fallback ke Provinsi")

                        # --- MODE: USER SLICING (DIRECT) ---
                        # Looping langsung per Petugas (Pencacah/Pengawas).
                        # Strategi ini lebih cepat karena jumlah switch filter lebih sedikit.
                        
                        filters_to_run = []

                        _progress("fetch_users", "👥 Mengambil daftar petugas...")
                        pengawas_list, pencacah_list = await api.get_users_by_region(period_id, role_ids, kab_full_code, survey_role_group_id)

                        if req.filter_rotation == "pencacah" and pencacah_list:
                            for idx, user in enumerate(pencacah_list):
                                filters_to_run.append({
                                    "label": f"[{idx+1}/{len(pencacah_list)}] Pencacah: {user['fullname']}",
                                    "pengawas_id": None,
                                    "pencacah_id": user['userId']
                                })
                            for idx, user in enumerate(pengawas_list):
                                filters_to_run.append({
                                    "label": f"[{len(pencacah_list)+idx+1}/{len(pencacah_list)+len(pengawas_list)}] Pengawas: {user['fullname']}",
                                    "pencacah_id": None
                                })
                        else:
                            for idx, user in enumerate(pengawas_list):
                                filters_to_run.append({
                                    "label": f"[{idx+1}/{len(pengawas_list)}] Pengawas: {user['fullname']}",
                                    "pengawas_id": user['userId'],
                                    "pencacah_id": None
                                })
                        
                        # Fallback if no users found: fetch region-wide
                        if not filters_to_run:
                            filters_to_run.append({
                                "label": "[1/1] Wilayah Saja (Tanpa Pengawas/Pencacah)",
                                "pengawas_id": None,
                                "pencacah_id": None
                            })

                        users_count = len(filters_to_run)
                        _progress("fetch_assignments", f"⚡ Memulai fetch {users_count} petugas secara concurrent...", users_total=users_count, users_done=0)

                        if SKIP_DETAIL_FETCH:
                            # Fast sync stats
                            run_stats = await run_fast_sync(
                                session=session,
                                api_client=api,
                                survey_id=survey_id,
                                period_id=period_id,
                                survey_config_id=req.survey_config_id,
                                prov_code=prov_uuid,
                                region_filter=region_filter,
                                region_full_code=kab_full_code,
                                region_group_id=region_group_id,
                                filters_to_run=filters_to_run,
                                sync_log_id=sync_log.id
                            )
                        else:
                            # Full sync stats (Full results are in run_stats.total_fetched)
                            run_stats = await run_full_sync(
                                session=session,
                                api_client=api,
                                cookie_dict=cookie_dict,
                                survey_id=survey_id,
                                period_id=period_id,
                                survey_config_id=req.survey_config_id,
                                prov_code=prov_uuid,
                                region_filter=region_filter,
                                region_full_code=kab_full_code,
                                region_group_id=region_group_id,
                                filters_to_run=filters_to_run,
                                sync_log_id=sync_log.id
                            )
                        
                        stats = run_stats

                finally:
                    if 'browser' in locals() and browser:
                        await browser.close()

        # Calculate total images found in this run
        total_images_in_run = 0
        from extractors.json_logic import extract_variables_from_json
        import json
        
        # We find assignments updated in this survey_config during this specific sync
        # Since we don't have the full list of objects easily from BulkUpserter,
        # we query the DB for the survey_config_id and date_synced (approximate)
        # OR better: we query all assignments for this survey_config that are NOT mirrored yet
        # but belong to this sync window.
        
        # Simplified: Just count all un-mirrored images for this survey_config 
        # to give a realistic "Remaining Work" for the archiver.
        upserted_assignments = session.query(Assignment).filter(
            Assignment.survey_config_id == req.survey_config_id,
            Assignment.local_image_mirrored == False
        ).all()
        
        for a in upserted_assignments:
            data = json.loads(a.data_json)
            vars_map = extract_variables_from_json(data)
            for k, v in vars_map.items():
                if isinstance(v, str) and v.startswith("http"):
                    is_image = any(ext in v.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']) or \
                               any(kw in k.lower() or kw in v.lower() for kw in ['foto', 'image', 'media'])
                    if is_image:
                        total_images_in_run += 1

        # Update sync log → success
        log = session.query(SyncLog).get(sync_log.id)
        log.finished_at = datetime.now(timezone.utc)
        log.total_fetched = stats.total_fetched
        log.total_new = stats.total_new
        log.total_updated = stats.total_updated
        log.total_skipped = stats.total_skipped
        log.total_failed = stats.total_failed
        log.total_images = total_images_in_run
        log.images_mirrored = 0 # Will be updated by archiver in background
        log.status = "success"
        session.commit()

        sync_state.last_result = {
            "status": "success",
            "survey": req.survey_name,
            "job_id": sync_log.id,
            "fetched": stats.total_fetched,
            "new": stats.total_new,
            "updated": stats.total_updated,
            "skipped": stats.total_skipped,
            "failed": stats.total_failed,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }

    except (FasihConnectionError, FasihAuthError) as e:
        print(f"❌ Connection/Auth Failure: {e}")
        log = session.query(SyncLog).get(sync_log.id)
        log.finished_at = datetime.now(timezone.utc)
        log.status = "failed"
        log.notes = f"Infrastructure Failure: {str(e)}"
        session.commit()

        sync_state.last_result = {
            "status": "failed",
            "survey": req.survey_name,
            "job_id": sync_log.id,
            "error": str(e),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
    except TimeoutError:
        print(f"❌ Job Timeout: Sync for {req.survey_name} took longer than 20 minutes.")
        log = session.query(SyncLog).get(sync_log.id)
        log.finished_at = datetime.now(timezone.utc)
        log.status = "failed"
        log.notes = "Killed by global timeout (20 mins)"
        session.commit()

        sync_state.last_result = {
            "status": "failed",
            "survey": req.survey_name,
            "job_id": sync_log.id,
            "error": "Global timeout exceeded (20 mins)",
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
    except asyncio.CancelledError:
        print(f"🛑 Job Cancelled: Sync for {req.survey_name} was interrupted by system shutdown.")
        log = session.query(SyncLog).get(sync_log.id)
        log.finished_at = datetime.now(timezone.utc)
        log.status = "failed"
        log.notes = "Interrupted by system shutdown (SIGTERM/Restart)"
        session.commit()
        
        sync_state.last_result = {
            "status": "failed",
            "survey": req.survey_name,
            "job_id": sync_log.id,
            "error": "Interrupted by system shutdown",
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
        # Re-raise to allow final cleanup
        raise
    except Exception as e:
        log = session.query(SyncLog).get(sync_log.id)
        log.finished_at = datetime.now(timezone.utc)
        log.status = "failed"
        log.notes = str(e)
        session.commit()

        sync_state.last_result = {
            "status": "failed",
            "survey": req.survey_name,
            "job_id": sync_log.id,
            "error": str(e),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }

    finally:
        sync_state.is_running = False
        sync_state.current_survey = None
        sync_state.current_survey_config_id = None
        sync_state.current_job_id = None
        sync_state.started_at = None
        sync_state.progress.reset()
        session.close()
```

### rpa/src/db/repository.py
```python
"""
Repository — operasi CRUD dan upsert untuk Assignment
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from .models import Assignment, SyncLog


class SyncStats:
    """Counter statistik per-cycle"""
    def __init__(self):
        self.total_fetched = 0
        self.total_new = 0
        self.total_updated = 0
        self.total_skipped = 0
        self.total_failed = 0
        self.total_images = 0
        self.images_mirrored = 0

    def __repr__(self):
        return (
            f"Fetched={self.total_fetched} | "
            f"New={self.total_new} | "
            f"Updated={self.total_updated} | "
            f"Skipped={self.total_skipped} | "
            f"Failed={self.total_failed} | "
            f"Images={self.images_mirrored}/{self.total_images}"
        )


def extract_flat_data(data: dict) -> dict:
    flat = {}
    for k, v in data.items():
        if not isinstance(v, (dict, list)):
            if isinstance(v, str) and (v.startswith('{') or v.startswith('[')):
                continue
            flat[k] = v
            
    pre_str = data.get("pre_defined_data")
    if pre_str and isinstance(pre_str, str) and pre_str.startswith('{'):
        try:
            for item in json.loads(pre_str).get("predata", []):
                if isinstance(item, dict) and "dataKey" in item:
                    flat[item["dataKey"]] = item.get("answer")
        except:
            pass
            
    content = data.get("content")
    if content:
        if isinstance(content, str) and content.startswith('{'):
            try: content = json.loads(content)
            except: content = {}
        if isinstance(content, dict):
            for item in content.get("data", []):
                if isinstance(item, dict) and "dataKey" in item:
                    flat[item["dataKey"]] = item.get("answer")
                    
    region = data.get("region_metadata")
    if isinstance(region, dict):
        for k, v in region.items():
            if not isinstance(v, (dict, list)):
                flat[f"region_{k}"] = v
            elif k == "level" and isinstance(v, list):
                for lvl in v:
                    if isinstance(lvl, dict):
                        flat[f"region_level_{lvl.get('id')}"] = lvl.get("name")
    return flat


def normalize_bps_date(date_str: any) -> str:
    if not date_str:
        return ""
    s = str(date_str).strip()
    if s.isdigit() and len(s) == 14:
        return s
    from datetime import datetime, timedelta
    try:
        # Format: 'Dec 9, 2025, 11:07:12 AM'
        dt = datetime.strptime(s, "%b %d, %Y, %I:%M:%S %p")
        # Convert WIB to UTC (Assuming BPS local is WIB/UTC+7)
        dt_utc = dt - timedelta(hours=7)
        return dt_utc.strftime("%Y%m%d%H%M%S")
    except:
        import re
        return re.sub(r'\D', '', s)[:14]


def upsert_assignment(session: Session, data: dict, stats: Optional[SyncStats] = None, sync_log_id: int = None) -> str:
    """
    Upsert satu assignment ke database.
    
    Returns:
        "new" | "updated" | "skipped"
    """
    # Hubungi ID dari berbagai kemungkinan (API detail vs API datatable)
    record_id = data.get("_id") or data.get("id") or data.get("assignment", {}).get("id")
    if not record_id:
        if stats:
            stats.total_failed += 1
        return "failed"

    # Ensure UUID object for PostgreSQL
    try:
        db_uuid = uuid.UUID(str(record_id))
    except (ValueError, TypeError):
        if stats: stats.total_failed += 1
        return "failed"

    # Hubungi Date Modified dari berbagai kemungkinan
    date_modified_raw = (
        data.get("date_modified") or 
        data.get("dateModifiedRemote") or 
        data.get("assignment", {}).get("dateModifiedRemote") or
        ""
    )
    date_modified = normalize_bps_date(date_modified_raw)
    data_json_str = json.dumps(data, ensure_ascii=False)
    flat_data = extract_flat_data(data)

    existing = session.get(Assignment, db_uuid)

    if existing is None:
        # INSERT baru
        
        # Helper to safely parse UUID or return None
        def safe_uuid(val):
            if not val: return None
            try: return uuid.UUID(str(val))
            except: return None

        assignment = Assignment(
            id=db_uuid,
            survey_config_id=safe_uuid(data.get("_survey_config_id")),
            code_identity=(
                data.get("code_identity") or 
                data.get("assignment", {}).get("codeIdentity") or 
                ""
            ),
            survey_period_id=safe_uuid(
                data.get("survey_period_id") or 
                data.get("assignment", {}).get("surveyPeriodId")
            ),
            assignment_status_alias=(
                data.get("assignment_status_alias") or 
                data.get("assignment", {}).get("assignmentStatusAlias") or 
                ""
            ),
            current_user_username=(
                data.get("current_user_username") or 
                data.get("assignment", {}).get("currentUserUsername") or 
                ""
            ),
            data_json=data_json_str,
            flat_data=flat_data,
            date_modified_remote=date_modified,
            synced_to_api=False,
            sync_log_id=sync_log_id,
        )
        session.add(assignment)
        if stats:
            stats.total_new += 1
        return "new"

    elif existing.date_modified_remote != date_modified:
        # UPDATE — data berubah dari remote (status/tanggal berubah)
        existing.code_identity = (
            data.get("code_identity") or 
            data.get("assignment", {}).get("codeIdentity") or 
            existing.code_identity
        )
        existing.survey_period_id = (
            data.get("survey_period_id") or 
            data.get("assignment", {}).get("surveyPeriodId") or 
            existing.survey_period_id
        )
        existing.assignment_status_alias = (
            data.get("assignment_status_alias") or 
            data.get("assignment", {}).get("assignmentStatusAlias") or 
            existing.assignment_status_alias
        )
        existing.current_user_username = (
            data.get("current_user_username") or 
            data.get("assignment", {}).get("currentUserUsername") or 
            existing.current_user_username
        )
        existing.sync_log_id = sync_log_id
        existing.data_json = data_json_str
        existing.flat_data = flat_data
        existing.date_modified_remote = date_modified
        existing.date_synced = datetime.now(timezone.utc)
        existing.synced_to_api = False
        # Reset mirrored flag so archiver re-processes with fresh presigned URLs
        existing.local_image_mirrored = False
        existing.local_image_paths = {}
        if stats:
            stats.total_updated += 1
        return "updated"

    else:
        # SKIP — data identik
        if stats:
            stats.total_skipped += 1
        return "skipped"


def get_unsynced(session: Session, limit: int = 1000) -> list[Assignment]:
    """Ambil assignment yang belum dikirim ke API downstream."""
    return (
        session.query(Assignment)
        .filter(Assignment.synced_to_api == False)
        .limit(limit)
        .all()
    )


def mark_synced(session: Session, ids: list[str]):
    """Tandai assignment sebagai sudah dikirim."""
    if not ids:
        return
    # Convert string IDs to UUID objects for PostgreSQL compatibility
    uuid_ids = [uuid.UUID(str(i)) for i in ids]
    session.query(Assignment).filter(Assignment.id.in_(uuid_ids)).update(
        {Assignment.synced_to_api: True}, synchronize_session="fetch"
    )
    session.commit()


def get_existing_modifications_by_ids(session: Session, ids: list[str]) -> dict[str, str]:
    """
    Ambil mapping {id: date_modified_remote} untuk list ID tertentu.
    Digunakan untuk delta check sebelum fetching detail dari API.

    Untuk dataset besar (>10k IDs), gunakan get_existing_modifications_by_ids_batched.
    """
    if not ids:
        return {}

    # Convert string IDs to UUID objects
    uuid_ids = []
    for i in ids:
        try:
            uuid_ids.append(uuid.UUID(str(i)))
        except:
            continue

    if not uuid_ids:
        return {}

    results = (
        session.query(Assignment.id, Assignment.date_modified_remote)
        .filter(Assignment.id.in_(uuid_ids))
        .all()
    )
    return {str(r.id): r.date_modified_remote for r in results}


def get_existing_modifications_by_ids_batched(
    session: Session, ids: list[str], chunk_size: int = 10_000
) -> dict[str, str]:
    """
    Versi chunked dari get_existing_modifications_by_ids untuk dataset besar (300k+).

    Memecah list ID menjadi chunk maksimal chunk_size agar tidak membuat
    satu IN clause raksasa yang bisa timeout atau OOM di PostgreSQL.

    Returns:
        dict {assignment_id (str): date_modified_remote (str | None)}
    """
    if not ids:
        return {}

    result: dict[str, str] = {}
    for i in range(0, len(ids), chunk_size):
        chunk = ids[i : i + chunk_size]
        # Convert chunk to UUIDs
        uuid_chunk = []
        for cid in chunk:
            try:
                uuid_chunk.append(uuid.UUID(str(cid)))
            except:
                continue
        
        if not uuid_chunk:
            continue

        rows = (
            session.query(Assignment.id, Assignment.date_modified_remote)
            .filter(Assignment.id.in_(uuid_chunk))
            .all()
        )
        result.update({str(r.id): r.date_modified_remote for r in rows})

    return result



def log_sync_run(
    session: Session,
    started_at: datetime,
    stats: SyncStats,
    notes: str = "",
    survey_config_id: str = "",
    timings: dict = None,
) -> SyncLog:
    """Catat log satu cycle sinkronisasi."""
    log = SyncLog(
        survey_config_id=survey_config_id,
        started_at=started_at,
        finished_at=datetime.now(timezone.utc),
        total_fetched=stats.total_fetched,
        total_new=stats.total_new,
        total_updated=stats.total_updated,
        total_skipped=stats.total_skipped,
        total_failed=stats.total_failed,
        total_images=stats.total_images,
        images_mirrored=stats.images_mirrored,
        notes=notes,
        timings=timings
    )
    session.add(log)
    session.commit()
    return log


def patch_sync_log(session: Session, log_id: int, **kwargs):
    """Update fields in an existing SyncLog entry (status, counts, etc)."""
    session.query(SyncLog).filter(SyncLog.id == log_id).update(kwargs)
    session.commit()


class BatchUpserter:
    """
    Batch upsert for assignments — collects records and flushes in bulk.
    Uses ORM-level upsert (per-row) — kept for compatibility.
    For new code, prefer BatchUpserterBulk which uses SQL-level batch insert.
    """

    def __init__(self, session: Session, batch_size: int = 500):
        self.session = session
        self.batch_size = batch_size
        self._buffer: list[dict] = []
        self.stats = SyncStats()

    def add(self, data: dict):
        """Add a record to the buffer. Auto-flushes when batch_size is reached."""
        self.stats.total_fetched += 1
        record_id = data.get("_id")
        if not record_id:
            self.stats.total_failed += 1
            return

        self._buffer.append(data)
        if len(self._buffer) >= self.batch_size:
            self.flush()

    def flush(self):
        """Flush buffered records to database using batch upsert."""
        if not self._buffer:
            return

        for data in self._buffer:
            upsert_assignment(self.session, data, self.stats)

        self.session.commit()
        self._buffer.clear()

    def finish(self) -> SyncStats:
        """Flush remaining records and return final stats."""
        self.flush()
        return self.stats


class BatchUpserterBulk:
    """
    High-performance bulk upsert using PostgreSQL INSERT ... ON CONFLICT DO UPDATE.
    Sends ONE SQL statement per batch instead of N ORM calls.
    Benchmark: ~50-200x faster than per-row ORM for large datasets.
    """

    def __init__(self, session: Session, batch_size: int = 2000, sync_log_id: int = None):
        self.session = session
        self.batch_size = batch_size
        self.sync_log_id = sync_log_id
        self._buffer: list[dict] = []
        self.stats = SyncStats()

    def add(self, row: dict):
        # Transform row data for column naming to match DB
        # This part handles the mapping from API-style keys to DB-style keys
        # as pg_insert expects exact DB column names

        self.stats.total_fetched += 1
        date_modified_raw = (
            row.get("date_modified") or 
            row.get("dateModifiedRemote") or 
            row.get("assignment", {}).get("dateModifiedRemote") or
            ""
        )
        date_modified = normalize_bps_date(date_modified_raw)
        
        db_row = {
            "id": row.get("_id") or row.get("id") or row.get("assignment", {}).get("id"),
            "survey_config_id": row.get("_survey_config_id", ""),
            "code_identity": row.get("code_identity") or row.get("assignment", {}).get("codeIdentity") or "",
            "survey_period_id": row.get("survey_period_id") or row.get("assignment", {}).get("surveyPeriodId") or "",
            "assignment_status_alias": row.get("assignment_status_alias") or row.get("assignment", {}).get("assignmentStatusAlias") or "",
            "current_user_username": row.get("current_user_username") or row.get("assignment", {}).get("currentUserUsername") or "",
            "data_json": json.dumps(row, ensure_ascii=False),
            "flat_data": extract_flat_data(row),
            "date_modified_remote": date_modified,
            "date_synced": datetime.now(timezone.utc),
            "synced_to_api": False,
            "sync_log_id": self.sync_log_id,
            "local_image_mirrored": False,
            "local_image_paths": {}
        }
        
        # PostgreSQL requires explicit UUID objects for bulk insert
        try:
            db_row["id"] = uuid.UUID(str(db_row["id"]))
            if db_row.get("survey_config_id"):
                db_row["survey_config_id"] = uuid.UUID(str(db_row["survey_config_id"]))
            if db_row.get("survey_period_id"):
                db_row["survey_period_id"] = uuid.UUID(str(db_row["survey_period_id"]))
        except (ValueError, TypeError) as e:
            print(f"   ⚠️ Skipping record with invalid UUID: {db_row['id']} ({e})")
            self.stats.total_failed += 1
            return

        self._buffer.append(db_row)
        if len(self._buffer) >= self.batch_size:
            self.flush()

    def flush(self, is_emergency: bool = False):
        """Execute a single INSERT ... ON CONFLICT DO UPDATE for the entire batch."""
        if not self._buffer:
            return

        from sqlalchemy.dialects.postgresql import insert as pg_insert
        prefix = "🚨 [EMERGENCY FLUSH]" if is_emergency else "💾 [BULK FLUSH]"

        try:
            stmt = pg_insert(Assignment).values(self._buffer)

            update_cols = {
                col: stmt.excluded[col]
                for col in [
                    "code_identity", "survey_period_id", "assignment_status_alias",
                    "current_user_username", "data_json", "flat_data",
                    "date_modified_remote", "date_synced", "synced_to_api", "sync_log_id",
                    "local_image_mirrored", "local_image_paths",
                ]
            }

            upsert_stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_=update_cols,
                where=(
                    # Always update if it's an emergency flush to ensure latest state is captured,
                    # otherwise only update if remote date changed.
                    (Assignment.date_modified_remote != stmt.excluded.date_modified_remote) or is_emergency
                )
            )

            result = self.session.execute(upsert_stmt)
            self.session.commit()

            inserted_or_updated = result.rowcount if result.rowcount >= 0 else len(self._buffer)
            skipped = len(self._buffer) - inserted_or_updated
            self.stats.total_new += inserted_or_updated
            self.stats.total_skipped += max(0, skipped)

            print(f"   {prefix} {len(self._buffer)} rows → {inserted_or_updated} upserted, {skipped} skipped")

        except Exception as e:
            print(f"   ⚠️ {prefix} failed ({e}), falling back to per-row ORM...")
            self.session.rollback()
            for row_data in self._buffer:
                try:
                    upsert_assignment(self.session, row_data, stats=self.stats, sync_log_id=self.sync_log_id)
                except Exception as row_err:
                    print(f"      ❌ Fatal error on single row fallback: {row_err}")
            self.session.commit()

        self._buffer.clear()

    def emergency_flush(self):
        """Called by signal handlers to save data before shutdown."""
        self.flush(is_emergency=True)

    def finish(self) -> SyncStats:
        """Flush remaining and return stats."""
        self.flush()
        return self.stats



def get_system_setting(session: Session, key: str) -> Optional[str]:
    """Ambil nilai dari system_settings."""
    from .models import SystemSettings
    setting = session.get(SystemSettings, key)
    return setting.value if setting else None


def set_system_setting(session: Session, key: str, value: str):
    """Simpan atau update nilai di system_settings."""
    from .models import SystemSettings
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    stmt = pg_insert(SystemSettings).values(key=key, value=value)
    upsert_stmt = stmt.on_conflict_do_update(
        index_elements=["key"],
        set_={"value": value, "updated_at": datetime.now(timezone.utc)}
    )
    session.execute(upsert_stmt)
    session.commit()
```

### rpa/src/connectivity.py
```python
import os
import aiohttp
import asyncio
from typing import Optional
from datetime import datetime, timezone

from db.connection import get_session, init_db, reset_engine
from db.models import SurveyConfig, SystemSettings
from crypto import decrypt_password
from auth import fetch_vpn_cookie

class FasihConnectionError(Exception):
    """Raised when VPN or BPS network is fundamentally unreachable."""
    pass

TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")

async def check_fasih_reachable() -> tuple[bool, str]:
    """
    Check if FASIH-SM is reachable via the VPN tunnel.
    Uses two signals:
    1. HTTP probe to /oauth_login.html (with SSL bypass for internal cert)
    2. Fallback: check if ppp0 exists and has an IP (tunnel-level check)
    Returns: (is_reachable, reason)
    """
    import ssl
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    try:
        connector = aiohttp.TCPConnector(ssl=ssl_ctx)
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=8, connect=5)
        ) as session:
            async with session.get(
                f"{TARGET_URL}/oauth_login.html",
                allow_redirects=True
            ) as resp:
                if resp.status in [200, 302, 401, 403]:
                    return True, "Reachable"
                return False, f"Unexpected status: {resp.status}"
    except asyncio.TimeoutError:
        # HTTP timeout — but tunnel might still be fine
        # Check tun0 or ppp0 as secondary signal
        has_vpn = os.path.exists("/sys/class/net/tun0") or os.path.exists("/sys/class/net/ppp0")
        if has_vpn:
            # Interface exists — tunnel is up, just slow
            return True, "Reachable (VPN UP, HTTP slow)"
        return False, "Connection timeout"
    except Exception as e:
        has_vpn = os.path.exists("/sys/class/net/tun0") or os.path.exists("/sys/class/net/ppp0")
        err_type = type(e).__name__
        err_msg = str(e)
        if has_vpn:
            return True, f"Reachable (VPN UP, probe error: {err_type})"
        return False, f"Connection error: {err_type} {err_msg}".strip()


async def is_session_stale() -> bool:
    """
    Perform a more thorough check: try to reach an API endpoint.
    If it redirects to login, the session (VPN cookie) is stale.
    """
    try:
        # We check a known protected API endpoint
        test_url = f"{TARGET_URL}/survey/api/v1/surveys/datatable?pageSize=1"
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(test_url, allow_redirects=True) as resp:
                # If the final URL contains oauth_login, it's stale
                if "oauth_login.html" in str(resp.url):
                    return True
                return False
    except Exception:
        # If we can't even connect, it's not 'stale', it's 'disconnected'
        return False

async def ensure_connected():
    """
    Proactive Self-Healing:
    1. Check if FASIH is reachable.
    2. If not, auto-fetch new VPN cookie via Playwright SSO login.
    3. Update DB — VPN watcher (entrypoint.sh) picks it up every 10s.
    4. Poll for reconnect, up to 60s.
    """
    reachable, reason = await check_fasih_reachable()
    
    if reachable:
        return True

    print(f"⚠️ FASIH unreachable: {reason}")
    print("🔄 Self-healing: auto-fetching new VPN cookie via Playwright...")

    reset_engine()
    init_db()
    session = get_session()
    try:
        # 1. Borrow SSO credentials dari survey aktif
        survey = session.query(SurveyConfig).filter(SurveyConfig.is_active == True).first()
        if not survey:
            raise FasihConnectionError("No active survey found to provide credentials for VPN self-healing.")

        username = survey.sso_username
        password = decrypt_password(survey.sso_password_encrypted)
        print(f"   🔑 Menggunakan kredensial: {username[:3]}*** dari survey '{survey.survey_name}'")

        # 2. Fetch cookie baru via Playwright (VPN portal)
        cookie = await fetch_vpn_cookie(username, password)
        if not cookie:
            print("   ❌ Gagal mendapatkan VPN cookie via Playwright.")
            print("   ⚠️  Melanjutkan sync — mungkin VPN masih bisa terhubung...")
            return False

        # 3. Simpan ke DB — VPN entrypoint.sh akan pick up dalam ~10s
        setting = session.query(SystemSettings).filter_by(key="vpn_cookie").first()
        if setting:
            setting.value = cookie
            setting.updated_at = datetime.now(timezone.utc)
        else:
            setting = SystemSettings(key="vpn_cookie", value=cookie)
            session.add(setting)
        session.commit()
        print("   ✅ Cookie baru tersimpan di DB. Menunggu VPN tunnel reconnect...")

        # 4. Poll hingga terhubung (maks 60s)
        # VPN watcher: polling setiap 10s → konek: ~15-20s → total maks ~30-40s
        for attempt in range(12):  # 12 × 5s = 60s
            await asyncio.sleep(5)
            r, info = await check_fasih_reachable()
            if r:
                print(f"   ✨ VPN reconnected setelah {(attempt+1)*5}s! ({info})")
                return True
            print(f"   ⏳ Menunggu reconnect... [{attempt+1}/12] — {info}")

        print("   ❌ Cookie diperbarui tapi FASIH masih unreachable setelah 60s.")
        raise FasihConnectionError(f"VPN self-healing failed: BPS Network unreachable ({info})")

    except FasihConnectionError:
        raise
    except Exception as e:
        import traceback
        print(f"   ❌ Self-healing error: {e}")
        traceback.print_exc()
        raise FasihConnectionError(f"VPN self-healing exception: {str(e)}")
    finally:
        session.close()
```

### rpa/src/state.py
```python
from typing import Optional
from datetime import datetime, timezone

class SyncProgress:
    """Live progress state untuk satu sync job yang sedang berjalan."""
    phase: str = ""          # "login", "resolve", "fetch_users", "fetch_assignments", "upsert", "done"
    phase_label: str = ""    # Human-readable label yang tampil di UI
    users_total: int = 0     # Jumlah user (pencacah/pengawas) yang perlu diiterasi
    users_done: int = 0      # Berapa user yang sudah selesai diiterasi
    assignments_total: int = 0
    assignments_fetched: int = 0
    assignments_new: int = 0
    assignments_updated: int = 0
    assignments_skipped: int = 0

    def reset(self):
        self.phase = ""
        self.phase_label = ""
        self.users_total = 0
        self.users_done = 0
        self.assignments_total = 0
        self.assignments_fetched = 0
        self.assignments_new = 0
        self.assignments_updated = 0
        self.assignments_skipped = 0

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "phase_label": self.phase_label,
            "users_total": self.users_total,
            "users_done": self.users_done,
            "assignments_total": self.assignments_total,
            "assignments_fetched": self.assignments_fetched,
            "assignments_new": self.assignments_new,
            "assignments_updated": self.assignments_updated,
            "assignments_skipped": self.assignments_skipped,
        }


class SyncState:
    is_running: bool = False
    is_shutting_down: bool = False
    is_vpn_fetching: bool = False
    current_survey: Optional[str] = None
    current_survey_config_id: Optional[str] = None
    current_job_id: Optional[int] = None
    last_result: Optional[dict] = None
    started_at: Optional[datetime] = None
    queue_count: int = 0
    progress: SyncProgress = SyncProgress()

sync_state = SyncState()
```

### rpa/src/pages/detail_page.py
```python
"""
Detail Page — Concurrent API Fetch untuk data assignment

Supports both serial (via Playwright page.evaluate) and concurrent (via aiohttp)
fetching strategies. Concurrent mode uses cookies from the Playwright session
to make parallel HTTP requests with asyncio.Semaphore for rate-limiting.
"""
import os
import re
import json
import asyncio
import ssl
from typing import Optional
from api_client import FasihAuthError

TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")
API_BASE = f"{TARGET_URL}/assignment-general/api/assignment/get-by-id-with-data-for-scm"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def extract_assignment_id(detail_url: str) -> str | None:
    """
    Ekstrak Assignment ID dari URL detail.
    Contoh: /survey-collection/assignment-detail/{ASSIGNMENT_ID}/{SURVEY_ID}
    """
    match = re.search(r'/assignment-detail/([a-f0-9\-]+)/', detail_url)
    if match:
        return match.group(1)
    return None


async def fetch_assignment_data(page, detail_url: str) -> dict | None:
    """
    Panggil API JSON langsung dari browser context via fetch().
    Memanfaatkan cookies session yang sudah aktif.
    
    Dengan retry logic: coba hingga MAX_RETRIES kali jika gagal.
    
    Returns:
        dict data assignment, atau None jika gagal
    """
    assignment_id = extract_assignment_id(detail_url)
    if not assignment_id:
        print(f"   ⚠️ Gagal parse Assignment ID dari: {detail_url}")
        return None

    api_url = f"{API_BASE}?id={assignment_id}"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = await page.evaluate('''async (apiUrl) => {
                try {
                    const response = await fetch(apiUrl, {
                        method: 'GET',
                        credentials: 'include',
                        headers: { 'Accept': 'application/json' }
                    });
                    if (!response.ok) {
                        return { error: true, status: response.status, message: response.statusText };
                    }
                    const json = await response.json();
                    return json;
                } catch (e) {
                    return { error: true, message: e.toString() };
                }
            }''', api_url)

            if result and result.get("success"):
                return result.get("data", {})

            error_msg = result.get("message", "Unknown") if result else "No response"
            
            if attempt < MAX_RETRIES:
                print(f"   ⚠️ Attempt {attempt}/{MAX_RETRIES} gagal ({error_msg}), retry in {RETRY_DELAY}s...")
                await asyncio.sleep(RETRY_DELAY)
            else:
                print(f"   ❌ Gagal setelah {MAX_RETRIES}x: {assignment_id[:8]}... ({error_msg})")
                return None

        except Exception as e:
            if attempt < MAX_RETRIES:
                print(f"   ⚠️ Attempt {attempt}/{MAX_RETRIES} exception: {e}, retry...")
                await asyncio.sleep(RETRY_DELAY)
            else:
                print(f"   ❌ Exception setelah {MAX_RETRIES}x: {e}")
                return None

    return None


# =====================================================================
# Concurrent Fetcher — uses aiohttp with cookies from Playwright
# =====================================================================

async def extract_cookies_from_context(context) -> dict:
    """Extract cookies from Playwright browser context as a dict for aiohttp."""
    cookies = await context.cookies()
    return {c["name"]: c["value"] for c in cookies}


async def _fetch_one(
    session,
    assignment_id: str,
    semaphore: asyncio.Semaphore,
    retries: int = MAX_RETRIES,
) -> Optional[dict]:
    """Fetch a single assignment detail via aiohttp with retry and semaphore."""
    import aiohttp
    api_url = f"{API_BASE}?id={assignment_id}"

    async with semaphore:
        for attempt in range(1, retries + 1):
            try:
                async with session.get(
                    api_url,
                    headers={"Accept": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    # [Scenario 2 Fix] Explicitly detect BPS SSO Redirects
                    if "oauth_login" in str(resp.url) or "sso.bps.go.id" in str(resp.url):
                        raise FasihAuthError("Session expired: redirected to SSO login")

                    if resp.status != 200:
                        body_text = await resp.text()
                        print(f"   ❌ {assignment_id[:8]}... HTTP {resp.status}: {body_text[:100]}")
                        if attempt < retries:
                            await asyncio.sleep(RETRY_DELAY * attempt)
                            continue
                        return None

                    body = await resp.json()
                    if body and body.get("success"):
                        return body.get("data", {})
                    
                    print(f"   ❌ {assignment_id[:8]}... API returned success=False: {body}")

                    if attempt < retries:
                        await asyncio.sleep(RETRY_DELAY * attempt)
                        continue
                    else:
                        return None

            except Exception as e:
                print(f"   ❌ {assignment_id[:8]}... Exception: {e}")
                if attempt < retries:
                    await asyncio.sleep(RETRY_DELAY * attempt)
                else:
                    return None

    return None


async def fetch_assignments_concurrent(
    cookie_dict: dict,
    urls: list[str],
    concurrency: int = 5,
    on_progress=None,
) -> list[dict]:
    """
    Fetch multiple assignment details concurrently using aiohttp.

    Args:
        cookie_dict: Dictionary of session cookies
        urls: List of assignment detail URLs
        concurrency: Maximum number of concurrent requests
        on_progress: Optional callback(fetched_count, total_count, data_or_none)

    Returns:
        List of successfully fetched assignment data dicts
    """
    import aiohttp
    
    
    # Create SSL context that doesn't verify (VPN internal network)
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    # Parse assignment IDs from URLs
    id_map = []
    for url in urls:
        aid = extract_assignment_id(url)
        if aid:
            id_map.append(aid)

    if not id_map:
        return []

    print(f"   🚀 Fetching {len(id_map)} assignments with concurrency={concurrency}...")

    semaphore = asyncio.Semaphore(concurrency)
    results = []
    completed = 0
    total = len(id_map)
    
    # Use a cookie jar with the extracted cookies
    jar = aiohttp.CookieJar(unsafe=True)
    connector = aiohttp.TCPConnector(ssl=ssl_ctx, limit=concurrency + 20)

    async with aiohttp.ClientSession(
        cookies=cookie_dict,
        cookie_jar=jar,
        connector=connector,
    ) as session:
        tasks = []
        for aid in id_map:
            tasks.append(_fetch_one(session, aid, semaphore))

        for coro in asyncio.as_completed(tasks):
            data = await coro
            completed += 1

            # Memory optimization: if on_progress (callback) is provided, 
            # we don't need to store all results in memory here.
            # The caller handles the storage (e.g. BatchUpserterBulk).
            if not on_progress and data:
                results.append(data)

            if on_progress:
                on_progress(completed, total, data)
            elif completed % 100 == 0 or completed == total:
                # Fallback logging if no callback
                print(f"   📊 Progress: {completed}/{total}")

    print(f"   ✅ Done: {completed}/{total} processed")
    return results
```

### rpa/src/routes/sync.py
```python
from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import datetime, timezone
import json

from db.connection import get_session, init_db, reset_engine
from db.models import SyncLog, SystemSettings

from state import sync_state
from schemas import SyncRequest, SyncResponse, StatusResponse, VpnCookieRequest
from auth import fetch_vpn_cookie
from worker.queue import _get_queued_jobs, _get_queue_position, _queue_worker

router = APIRouter()

@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/status", response_model=StatusResponse)
def status():
    # Get queued jobs — use existing session without reset/init every call
    queue = []
    try:
        session = get_session()
        queued = _get_queued_jobs(session)
        import json
        for i, job in enumerate(queued):
            try:
                req_data = json.loads(job.notes or "{}")
                survey_name = req_data.get("survey_name", "Unknown")
            except:
                survey_name = "Unknown"
            queue.append({
                "job_id": job.id,
                "survey_name": survey_name,
                "position": i + 1,
                "status": "queued",
            })
        session.close()
    except:
        pass

    return StatusResponse(
        is_running=sync_state.is_running,
        is_vpn_fetching=sync_state.is_vpn_fetching,
        current_survey=sync_state.current_survey,
        current_survey_config_id=sync_state.current_survey_config_id,
        current_job_id=sync_state.current_job_id,
        started_at=sync_state.started_at.isoformat() if sync_state.started_at else None,
        last_result=sync_state.last_result,
        queue=queue,
        progress=sync_state.progress.to_dict() if sync_state.is_running else None,
    )


@router.post("/sync", response_model=SyncResponse)
async def trigger_sync(req: SyncRequest, background_tasks: BackgroundTasks):
    # Check if this survey already has a queued or running job
    reset_engine()
    init_db()
    session = get_session()

    existing = (
        session.query(SyncLog)
        .filter(
            SyncLog.survey_config_id == req.survey_config_id,
            SyncLog.status.in_(["queued", "running"]),
        )
        .first()
    )

    if existing:
        pos = _get_queue_position(session, existing.id) if existing.status == "queued" else 0
        session.close()
        return SyncResponse(
            status="already_queued",
            message=f"Survey '{req.survey_name}' sudah dalam antrian"
                    + (f" (posisi {pos})" if pos else " (sedang berjalan)"),
            job_id=existing.id,
            queue_position=pos,
        )

    # Create queued job — store request data in notes as JSON
    sync_log = SyncLog(
        survey_config_id=req.survey_config_id,
        started_at=datetime.now(timezone.utc),
        status="queued",
        notes=json.dumps(req.dict()),
    )
    session.add(sync_log)
    session.commit()
    job_id = sync_log.id

    queue_pos = _get_queue_position(session, job_id)
    session.close()

    # Start worker if not already running
    background_tasks.add_task(_queue_worker)

    return SyncResponse(
        status="queued",
        message=f"Sync untuk '{req.survey_name}' ditambahkan ke antrian (posisi {queue_pos})",
        job_id=job_id,
        queue_position=queue_pos,
    )


@router.delete("/sync/{job_id}")
async def cancel_job(job_id: int):
    """Cancel a queued job."""
    reset_engine()
    init_db()
    session = get_session()

    job = session.query(SyncLog).get(job_id)
    if not job:
        session.close()
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "queued":
        session.close()
        raise HTTPException(status_code=400, detail=f"Cannot cancel job with status '{job.status}'")

    job.status = "cancelled"
    job.finished_at = datetime.now(timezone.utc)
    job.notes = "Cancelled by user"
    session.commit()
    session.close()

    return {"status": "cancelled", "message": f"Job {job_id} cancelled"}


from connectivity import check_fasih_reachable, is_session_stale

@router.get("/vpn/check")
async def check_vpn():
    import os
    try:
        # 1. Check application-level reachability (can we reach the FASIH server?)
        reachable, reason = await check_fasih_reachable()
        
        # 2. Check physical interface (Informational only)
        has_tun = os.path.exists("/sys/class/net/tun0")
        has_ppp = os.path.exists("/sys/class/net/ppp0")
        has_vpn = has_tun or has_ppp
        
        if reachable:
            if has_tun:
                info = "VPN Connected (via tun0)"
            elif has_ppp:
                info = "VPN Connected (via ppp0)"
            else:
                info = "VPN Connected (Transparently via Host)"
            return {"connected": True, "info": info}
            
        return {
            "connected": False, 
            "reason": f"FASIH-SM unreachable: {reason} (Interface: {'tun0/ppp0 UP' if has_vpn else 'Missing'})"
        }
        
    except Exception as e:
        return {"connected": False, "reason": f"Status check error: {str(e)}"}



@router.post("/vpn/auto-fetch")
async def auto_fetch_vpn(req: VpnCookieRequest):
    """Otomasi ambil VPN cookie dan simpan ke database."""
    from auth import FETCH_LOCK, get_current_cookie, sync_cookie_to_db

    if FETCH_LOCK.locked():
        return {"status": "already_fetching", "message": "Proses auto-fetch VPN sedang berjalan..."}

    if not req.sso_username or not req.sso_password:
        print("   ❌ Gagal: Username atau Password SSO kosong!")
        raise HTTPException(status_code=400, detail="SSO Username and Password are required")

    async with FETCH_LOCK:
        # Check if cookie already exists (maybe another trigger finished just now)
        existing = await get_current_cookie()
        if existing:
            return {"status": "success", "message": "Cookie sudah ada di database, melewati fetch."}

        try:
            user_display = f"{req.sso_username[:3]}***" if req.sso_username else "None"
            print(f"🔄 Memulai auto-fetch VPN cookie untuk user {user_display}...")
            cookie = await fetch_vpn_cookie(req.sso_username, req.sso_password)
            
            if cookie:
                await sync_cookie_to_db(cookie)
                return {"status": "success", "message": "VPN cookie berhasil diperbarui"}
            else:
                raise HTTPException(status_code=400, detail="Gagal mendapatkan VPN cookie dari Keycloak SSO")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Fetch error: {e}")


@router.post("/sync/refresh-assignment/{assignment_id}")
async def refresh_assignment(assignment_id: str):
    """
    Refetch assignment detail from BPS and update the local database.
    Used by the archiver to heal expired 403 links.
    """
    from db.models import Assignment, SystemSettings
    from api_client import FasihApiClient
    
    reset_engine()
    init_db()
    session = get_session()
    
    try:
        # Get SSO cookies from SystemSettings
        cookie_setting = session.query(SystemSettings).filter_by(key="sso_cookies").first()
        if not cookie_setting:
            raise HTTPException(status_code=401, detail="No active SSO session. Please trigger a sync first.")
            
        cookies = json.loads(cookie_setting.value)
        
        async with FasihApiClient(cookies) as api:
            new_data = await api.get_assignment_detail(assignment_id)
            if not new_data:
                raise HTTPException(status_code=404, detail="Failed to fetch fresh data from BPS")
            
            # Update the assignment in DB
            assignment = session.query(Assignment).get(assignment_id)
            if assignment:
                assignment.data_json = new_data
                session.commit()
                print(f"   ✅ Successfully refreshed assignment {assignment_id} in DB")
                return {"status": "success", "message": f"Assignment {assignment_id} refreshed"}
            else:
                raise HTTPException(status_code=404, detail="Assignment not found in local DB")
                
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

from pydantic import BaseModel

class AssignmentFileNamesPayload(BaseModel):
    assignmentId: str
    fileNames: list[str]

class RefreshImageUrlsRequest(BaseModel):
    survey_period_id: str
    assignments_payload: list[AssignmentFileNamesPayload]

@router.post("/sync/refresh-image-urls")
async def refresh_image_urls(req: RefreshImageUrlsRequest):
    """
    Get fresh S3 Presigned URLs directly from BPS /presigned-url-get endpoint.
    Returns: { "s3_key_1": "https://fresh_url...", ... }
    """
    from db.models import SystemSettings
    from api_client import FasihApiClient
    
    reset_engine()
    init_db()
    session = get_session()
    
    try:
        cookie_setting = session.query(SystemSettings).filter_by(key="sso_cookies").first()
        if not cookie_setting:
            raise HTTPException(status_code=401, detail="No active SSO session. Please trigger a sync first.")
            
        cookies = json.loads(cookie_setting.value)
        
        async with FasihApiClient(cookies) as api:
            payload_dicts = [item.dict() for item in req.assignments_payload]
            fresh_urls = await api.get_fresh_image_urls(req.survey_period_id, payload_dicts)
            if fresh_urls is None:
                raise HTTPException(status_code=500, detail="Failed to fetch fresh presigned URLs from BPS")
            
            return {"status": "success", "data": fresh_urls}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()
```

### rpa/src/worker/scheduler.py
```python
import asyncio
import logging
import json
from datetime import datetime, timezone
from db.connection import get_session, init_db
from db.models import SurveyConfig, SyncLog
from connectivity import check_fasih_reachable
from worker.queue import trigger_worker
from crypto import decrypt_password

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scheduler")

async def routine_sync_loop():
    """
    Background loop that checks for surveys due for synchronization.
    Runs every 60 seconds.
    """
    print("🕒 Routine Sync Scheduler started.", flush=True)
    
    # Wait 30 seconds on startup to let VPN and system stabilize
    await asyncio.sleep(30)
    
    while True:
        try:
            print("🔍 Scheduler: Checking for surveys to sync...", flush=True)
            session = get_session()

            # --- STALE JOB CLEANUP ---
            # If a job is 'running' for more than 45 minutes, it's likely stuck/zombie.
            from datetime import timedelta
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=45)
            
            stale_jobs = session.query(SyncLog).filter(
                SyncLog.status == "running", 
                SyncLog.started_at < cutoff
            ).all()
            
            if stale_jobs:
                print(f"🧹 Scheduler: Found {len(stale_jobs)} stale job(s). Cleaning up...", flush=True)
                for job in stale_jobs:
                    job.status = "failed"
                    job.notes = f"Marked as failed by auto-cleanup (stuck since {job.started_at})"
                    job.finished_at = datetime.now(timezone.utc)
                session.commit()
            
            # Fetch all active surveys with a valid interval
            active_surveys = (
                session.query(SurveyConfig)
                .filter(SurveyConfig.is_active == True)
                .filter(SurveyConfig.interval_minutes > 0)
                .all()
            )
            
            print(f"📊 Scheduler: Found {len(active_surveys)} active surveys with routine intervals.", flush=True)
            
            if not active_surveys:
                session.close()
                await asyncio.sleep(60)
                continue
            
            # Proactive Connectivity Check & Self-Healing
            from connectivity import ensure_connected
            print("📡 Scheduler: Checking connectivity...", flush=True)
            is_connected = await ensure_connected()
            if not is_connected:
                print("⚠️ Scheduler: VPN/FASIH unreachable even after self-healing attempt. Skipping this cycle.", flush=True)
                session.close()
                await asyncio.sleep(60)
                continue

            jobs_added = 0
            
            for survey in active_surveys:
                interval = survey.interval_minutes
                
                # Step 1: Skip if there's already an active job for this survey
                active_job = session.query(SyncLog).filter(
                    SyncLog.survey_config_id == survey.id,
                    SyncLog.status.in_(["queued", "running"])
                ).first()
                
                if active_job:
                    print(f"   ⏩ Skipping {survey.survey_name}: Job already {active_job.status}", flush=True)
                    continue
                
                # Step 2: Check time elapsed since last sync
                last_job = (
                    session.query(SyncLog)
                    .filter(SyncLog.survey_config_id == survey.id)
                ).order_by(SyncLog.started_at.desc()).first()
                
                should_sync = False
                if not last_job or not last_job.started_at:
                    should_sync = True
                else:
                    last_start = last_job.started_at.replace(tzinfo=timezone.utc)
                    delta = datetime.now(timezone.utc) - last_start
                    elapsed_mins = delta.total_seconds() / 60
                    if elapsed_mins >= interval:
                        should_sync = True
                    else:
                        print(f"   ⏳ {survey.survey_name}: Not due yet ({elapsed_mins:.1f}/{interval}m)", flush=True)
                
                if should_sync:
                    print(f"🚀 Scheduler: Enqueuing routine sync for: {survey.survey_name} (Interval: {interval}m)", flush=True)
                    
                    try:
                        raw_password = decrypt_password(survey.sso_password_encrypted)
                        
                        request_payload = {
                            "survey_config_id": str(survey.id),
                            "survey_name": survey.survey_name,
                            "sso_username": survey.sso_username,
                            "sso_password": raw_password,
                            "filter_provinsi": survey.filter_provinsi or "",
                            "filter_kabupaten": survey.filter_kabupaten or "",
                            "filter_rotation": survey.filter_rotation or "pengawas",
                            "source": "Automated routine sync"
                        }
                        
                        new_log = SyncLog(
                            survey_config_id=survey.id,
                            status="queued",
                            notes=json.dumps(request_payload),
                            total_fetched=0, total_new=0, total_updated=0, total_skipped=0, total_failed=0,
                            started_at=datetime.now(timezone.utc)
                        )
                        session.add(new_log)
                        jobs_added += 1
                    except Exception as e:
                        print(f"   ❌ Scheduler: Failed to prepare job for {survey.survey_name}: {e}", flush=True)
            
            session.commit()
            session.close()
            
            if jobs_added > 0:
                print(f"✅ Scheduler: Added {jobs_added} routine job(s) to queue.", flush=True)
                await trigger_worker()
                
        except Exception as e:
            print(f"❌ Error in routine sync loop: {e}", flush=True)
            import traceback
            traceback.print_exc()
            if 'session' in locals():
                session.close()
        
        # Check every 60 seconds
        await asyncio.sleep(60)
```

### rpa/src/worker/queue.py
```python
import asyncio
import json
from datetime import datetime, timezone

from db.connection import get_session, init_db, reset_engine
from db.models import SyncLog

from state import sync_state
from schemas import SyncRequest
from worker.job_runner import _run_single_job

def _get_queued_jobs(session) -> list:
    """Get all queued jobs ordered by creation time."""
    return (
        session.query(SyncLog)
        .filter(SyncLog.status == "queued")
        .order_by(SyncLog.started_at.asc())
        .all()
    )


def _get_queue_position(session, job_id: int) -> int:
    """Get position of a job in the queue (1-indexed)."""
    queued = _get_queued_jobs(session)
    for i, job in enumerate(queued):
        if job.id == job_id:
            return i + 1
    return 0


_worker_running = False

async def _queue_worker():
    """Background worker that processes queued jobs one by one."""
    global _worker_running
    if _worker_running:
        return
    _worker_running = True

    try:
        while True:
            # Check for next queued job
            reset_engine()
            init_db()
            session = get_session()

            queued = _get_queued_jobs(session)
            sync_state.queue_count = len(queued)

            if not queued:
                session.close()
                break

            job = queued[0]
            # Reconstruct request from the job's notes (stored as JSON)
            try:
                req_data = json.loads(job.notes or "{}")
                req = SyncRequest(**req_data)
            except Exception as e:
                job.status = "failed"
                job.notes = f"Invalid job data: {e}"
                job.finished_at = datetime.now(timezone.utc)
                session.commit()
                session.close()
                continue

            session.close()

            # Process the job
            await _run_single_job(job, req)

            # Small delay between jobs
            await asyncio.sleep(2)

    finally:
        _worker_running = False
        sync_state.queue_count = 0

async def trigger_worker():
    """Trigger the queue worker if it's not already running."""
    if not _worker_running:
        asyncio.create_task(_queue_worker())
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

# 🛡️ Disable IPv6 to prevent connection resets (ERR_CONNECTION_RESET)
sysctl -w net.ipv6.conf.all.disable_ipv6=1 >/dev/null 2>&1 || true
sysctl -w net.ipv6.conf.default.disable_ipv6=1 >/dev/null 2>&1 || true

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

# 📉 Restore eth0 MTU to default (1500) for stable inter-container comms
echo "📉 Ensuring eth0 MTU is 1500..."
ip link set eth0 mtu 1500 2>/dev/null || true

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

# 🛡️ MTU Watchdog: Permanently locks VPN MTU to prevent resets
mtu_watchdog() {
    echo "🛡️ MTU Watchdog started (Target: 500)"
    while true; do
        sleep 10
        VPN_IF=""
        if [ -d "/sys/class/net/tun0" ]; then VPN_IF="tun0"; fi
        if [ -z "$VPN_IF" ] && [ -d "/sys/class/net/ppp0" ]; then VPN_IF="ppp0"; fi
        
        if [ -n "$VPN_IF" ]; then
            CURRENT_MTU=$(cat "/sys/class/net/$VPN_IF/mtu" 2>/dev/null)
            if [ "$CURRENT_MTU" != "500" ]; then
                echo "🛡️ MTU Watchdog: Re-locking $VPN_IF MTU to 500 (was $CURRENT_MTU)..."
                ip link set dev "$VPN_IF" mtu 500 2>/dev/null || true
            fi
        fi
    done
}

mtu_watchdog &

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
            
            echo "📉 Setting $VPN_IF MTU to 500..."
            ip link set dev "$VPN_IF" mtu 500 || true
            
            # 🛡️ MSS Clamping: Force TCP to use small packets to prevent "silent hangs"
            iptables -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 460
            iptables -t mangle -A POSTROUTING -p tcp --tcp-flags SYN,RST SYN -o "$VPN_IF" -j TCPMSS --set-mss 460
            
            echo "✅ BPS Routing & MSS Clamping updated."
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
            # We use a retry loop because RPA might still be starting its web server.
            for attempt in $(seq 1 6); do
                RESP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "http://127.0.0.1:8000/vpn/auto-fetch" \
                    -H "Content-Type: application/json" \
                    -d "{\"sso_username\":\"$VPN_USER\", \"sso_password\":\"$VPN_PASS\"}")
                
                if [ "$RESP" = "200" ]; then
                    echo "   ✅ RPA auto-fetch triggered successfully."
                    break
                fi
                echo "   ⚠️ RPA not ready yet ($attempt/6, code: $RESP), retrying in 10s..."
                sleep 10
            done
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
echo "🩺 Running Universal Self-Healing Migration Check..."
# Blok PL/pgSQL yang lebih luas untuk menangani berbagai potensi konflik skema
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "
DO \$\$ 
DECLARE
    r RECORD;
BEGIN 
    SET statement_timeout = '60000'; -- 60 seconds
    RAISE NOTICE 'Starting universal database hardening...';

    -- A. Drop SEMUA foreign key constraints sementara (Akan dibuat ulang oleh Drizzle)
    -- Ini mencegah error 'cannot alter type because of dependency'
    FOR r IN (
        SELECT tc.table_name, tc.constraint_name
        FROM information_schema.table_constraints AS tc 
        JOIN information_schema.key_column_usage AS kcu ON tc.constraint_name = kcu.constraint_name
        WHERE constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
    ) LOOP
        EXECUTE format('ALTER TABLE %I DROP CONSTRAINT IF EXISTS %I', r.table_name, r.constraint_name);
    END LOOP;

    -- B. Konversi otomatis kolom ID yang tertinggal sebagai TEXT ke UUID
    FOR r IN (
        SELECT table_name, column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND (column_name = 'id' OR column_name LIKE '%_id')
          AND (data_type = 'text' OR data_type = 'character varying')
    ) LOOP
        RAISE NOTICE 'Auto-repairing %.% from text to uuid...', r.table_name, r.column_name;
        BEGIN
            EXECUTE format('ALTER TABLE %I ALTER COLUMN %I TYPE uuid USING %I::uuid', r.table_name, r.column_name, r.column_name);
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'Could not convert %.%, skipping...', r.table_name, r.column_name;
        END;
    END LOOP;

    -- C. Bersihkan semua sequence yatim piatu yang sering bikin error 42P07
    FOR r IN (
        SELECT relname as sequence_name
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind = 'S'
    ) LOOP
        RAISE NOTICE 'Cleaning up sequence %...', r.sequence_name;
        BEGIN EXECUTE format('DROP SEQUENCE IF EXISTS %I CASCADE', r.sequence_name); EXCEPTION WHEN OTHERS THEN NULL; END;
    END LOOP;
    
    RAISE NOTICE 'Database hardening completed.';
END \$\$;
" || echo "   ⚠️ Hardening check completed with some skip/warnings."

echo "📦 Generating & Syncing database schema..."
SYNC_SUCCESS=false
for i in {1..5}; do
  # Kita jalankan push --force agar tidak berhenti saat ada peringatan (misal data loss)
  # Gunakan --accept-all jika versi drizzle mendukung, atau biarkan default push
  if bunx drizzle-kit push; then
    SYNC_SUCCESS=true
    break
  fi
  echo "   ⏳ DB not ready or sync failed, retrying ($i/5)..."
  sleep 5
done

if [ "$SYNC_SUCCESS" = false ]; then
  echo "❌ Database schema sync failed. Trying one last time with generate pass..."
  # Fallback: jika push gagal, coba generate migration dulu baru push (force)
  bunx drizzle-kit generate || true
  bunx drizzle-kit push --force && SYNC_SUCCESS=true
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
297b3ac fix: implement permanent MTU locking for VPN resilience (Scenario 1 & Scenario 3)
89b4522 feat: complete resilience hardening for Scenario 2 (Silent Auth) and Scenario 3 (Atomic Shutdown)
f373415 chore: update dump_project.sh with critical RPA logic files and refresh snapshot
8dbdbca feat: infrastructure hardening & resiliency (Response Guardian, Atomic Shield, Signal Watchdog)
536e16e chore: upgrade entrypoint to universal self-healing migration
```

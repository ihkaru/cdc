# Project Snapshot: FasihNexus
Generated at: Fri May 15 09:54:18 PM WIB 2026

## 📂 Project Structure
```text
Listing files respecting .gitignore:
.env.example
.gitignore
.vscode/settings.json
README.md
analyze_repo.sh
api_exploration.log
benchmark_api.sh
benchmark_fasih.sh
benchmark_ux_lookup.sh
check-health.sh
check-stability.sh
dashboard/.gitignore
dashboard/Dockerfile
dashboard/README.md
dashboard/bun.lock
dashboard/client/.gitignore
dashboard/client/README.md
dashboard/client/bun.lock
dashboard/client/index.html
dashboard/client/index.ts
dashboard/client/package-lock.json
dashboard/client/package.json
dashboard/client/public/favicon.ico
dashboard/client/quasar.config.js
dashboard/client/quasar.config.js.temporary.compiled.1772827948483.mjs
dashboard/client/quasar.config.js.temporary.compiled.1772827984153.mjs
dashboard/client/quasar.config.js.temporary.compiled.1772828135725.mjs
dashboard/client/quasar.config.js.temporary.compiled.1772828136841.mjs
dashboard/client/src/App.vue
dashboard/client/src/boot/axios.ts
dashboard/client/src/boot/pinia.ts
dashboard/client/src/components/visualizations/VizAddEditDialog.vue
dashboard/client/src/components/visualizations/VizBulkImportDialog.vue
dashboard/client/src/components/visualizations/VizCard.vue
dashboard/client/src/components/visualizations/VizMapLibre.vue
dashboard/client/src/components/visualizations/VizPreviewCanvas.vue
dashboard/client/src/composables/useVpn.ts
dashboard/client/src/composables/visualizations/useBulkImport.ts
dashboard/client/src/composables/visualizations/useVisualizationData.ts
dashboard/client/src/composables/visualizations/useVizForm.ts
dashboard/client/src/css/app.scss
dashboard/client/src/layouts/MainLayout.vue
dashboard/client/src/pages/ErrorNotFound.vue
dashboard/client/src/pages/IndexPage.vue
dashboard/client/src/pages/LoginPage.vue
dashboard/client/src/pages/SurveyDetail.vue
dashboard/client/src/pages/SurveyForm.vue
dashboard/client/src/pages/SurveyList.vue
dashboard/client/src/pages/SurveyVisualizations.vue
dashboard/client/src/pages/SyncLogs.vue
dashboard/client/src/router/index.ts
dashboard/client/src/router/routes.ts
dashboard/client/src/stores/auth.ts
dashboard/client/src/utils/chartOptions.ts
dashboard/client/tsconfig.json
dashboard/drizzle.config.ts
dashboard/entrypoint.sh
dashboard/package.json
dashboard/server/auth.ts
dashboard/server/db/index.ts
dashboard/server/db/migrations/0000_damp_deadpool.sql
dashboard/server/db/migrations/add-indexes.sql
dashboard/server/db/migrations/meta/0000_snapshot.json
dashboard/server/db/migrations/meta/_journal.json
dashboard/server/db/schema.ts
dashboard/server/db/seed-pegawai.ts
dashboard/server/db/seed_data/data-pegawai.php
dashboard/server/index.ts
dashboard/server/middleware/auth.ts
dashboard/server/routes/assignments.ts
dashboard/server/routes/labels.ts
dashboard/server/routes/logs.ts
dashboard/server/routes/storage.ts
dashboard/server/routes/surveys.ts
dashboard/server/routes/sync-state.ts
dashboard/server/routes/sync.ts
dashboard/server/routes/visualizations.ts
dashboard/server/scripts/backfill.ts
dashboard/server/scripts/backfill_flat_data.ts
dashboard/server/tsconfig.json
dashboard/test_db.ts
dashboard/tsconfig.json
docker-compose.coolify.yml
docker-compose.override.yml
docker-compose.yml
docs/adr/0001-baseline-architecture-and-turbo-concurrency.md
docs/adr/0002-auth-and-rbac-system.md
docs/adr/0003-routine-sync-and-internal-scheduler.md
docs/adr/README.md
docs/adr/SKILL.md
docs/references/data-pegawai.php
dump_project.sh
full_payload_dump.log
grab_payload.py
n8n-workflows/fasih_sync.json
project_snapshot.md
rpa/Dockerfile
rpa/README.md
rpa/check_counts.py
rpa/check_counts_simple.py
rpa/config/.env copy.example
rpa/config/.env.example
rpa/config/settings.py
rpa/requirements.txt
rpa/scripts/backfill.py
rpa/src/__init__.py
rpa/src/api_client.py
rpa/src/app.py
rpa/src/archiver.py
rpa/src/auth.py
rpa/src/benchmark_api.py
rpa/src/browser/__init__.py
rpa/src/browser/manager.py
rpa/src/connectivity.py
rpa/src/crypto.py
rpa/src/db/__init__.py
rpa/src/db/connection.py
rpa/src/db/models.py
rpa/src/db/repository.py
rpa/src/extractors/__init__.py
rpa/src/extractors/json_logic.py
rpa/src/extractors/table_extractor.py
rpa/src/main.py
rpa/src/pages/__init__.py
rpa/src/pages/assignment_page.py
rpa/src/pages/base_page.py
rpa/src/pages/detail_page.py
rpa/src/pages/filter_rotator.py
rpa/src/pages/list_page.py
rpa/src/pages/login_page.py
rpa/src/pages/survey_navigator.py
rpa/src/routes/__init__.py
rpa/src/routes/lookup.py
rpa/src/routes/sync.py
rpa/src/schemas.py
rpa/src/state.py
rpa/src/storage.py
rpa/src/worker/__init__.py
rpa/src/worker/fast_mode.py
rpa/src/worker/full_mode.py
rpa/src/worker/job_runner.py
rpa/src/worker/queue.py
rpa/src/worker/scheduler.py
rpa/tmp_explore_api.py
rpa/tmp_test_datatable.py
rpa/tmp_test_survey.py
rpa/tmp_test_users.py
start-docker.sh
start-local.sh
stop-all.sh
test-routine-sync.sh
tmp/routes.txt
tmp_explore_api.py
update_cookie.py
update_cookie.sql
vpn/Dockerfile
vpn/entrypoint.sh
```

## 📖 Core Documentation
### File: `README.md`
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

## Troubleshooting & Best Practices

1. **DNS Failure di Archiver/RPA**: Pastikan service `vpn` memiliki `dns: 127.0.0.11`. Tanpa ini, service yang menggunakan `network_mode: service:vpn` tidak bisa memanggil `postgres` atau `s3`.
2. **VPN Cookie Expired**: Jika container VPN unhealthy, login ulang ke `akses.bps.go.id` dan update cookie via Dashboard.
3. **Traefik Non-Deterministic IP**: Gunakan label `traefik.docker.network=coolify` pada service `dashboard` (sudah ada di docker-compose.yml default).

## Lisensi

Internal BPS — tidak untuk distribusi publik.
```

### File: `GEMINI.md`
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
- **Fungsi**: Menyediakan tunnel VPN. Menggunakan **DNS Pinning** (`dns: 127.0.0.11`) agar service yang menumpang (`network_mode: service:vpn`) tetap bisa mengakses service internal Docker (postgres, s3) yang berada di network `fasih_internal`.
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

## Known Gotchas & Best Practices

1. **DNS Pinning**: Service `vpn` WAJIB memiliki `dns: 127.0.0.11`. Tanpa ini, RPA/Archiver akan mengalami `Connection Timeout` saat memanggil database atau S3.
2. **Coolify Network Settings**: Pada resource Docker Compose di Coolify, opsi **"Connect to Predefined Network"** harus **DIMATIKAN** (OFF) untuk menghindari error `mutually exclusive network_mode`.
3. **Traefik Determinism**: Service `dashboard` harus memiliki label `traefik.docker.network=coolify` agar Traefik memilih IP yang benar.
4. **VPN Restart**: Jika container VPN restart, session di Fortinet mungkin menggantung. User perlu update cookie via Dashboard.
5. **Path Patching di Python**: Skrip RPA (`main.py`, `archiver.py`) memiliki blok *self-healing* `sys.path.append` untuk memastikan modul `db` dan `pages` terbaca dengan benar terlepas dari working directory.
6. **Internal Scheduler Delay**: RPA scheduler sengaja menunggu 30 detik saat startup agar VPN tunnel stabil sebelum mulai query database.

---
**Status**: Production Hardened (Hybrid Network Bridge Model).
```

## 🐳 Docker Compose Configuration
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
      - "traefik.docker.network=coolify" # FORCE Traefik to use the public network IP
      - "coolify.managed=true"
      # Note: Route rules and SSL will be automatically handled by Coolify UI
    environment:
      - DATABASE_URL=postgres://fasih:${POSTGRES_PASSWORD}@postgres:5432/fasih_dashboard
      - RPA_URL=http://vpn:8000
      - VPN_AUTH_URL=http://vpn:8001
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      - BETTER_AUTH_SECRET=${BETTER_AUTH_SECRET}
      - BETTER_AUTH_URL=${BETTER_AUTH_URL}
      - PUBLIC_BASE_URL=${PUBLIC_BASE_URL}
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "bun -e \"fetch('http://localhost:3000/api/health').then(r => r.ok ? process.exit(0) : process.exit(1))\""]
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
      - 127.0.0.11 # CRITICAL: Ensures sharing containers can resolve Docker internal DNS (s3, postgres)
    networks:
      - fasih_internal
    labels:
      - "coolify.managed=false"
    environment:
      - DATABASE_URL=postgres://fasih:${POSTGRES_PASSWORD}@postgres:5432/fasih_dashboard
      - VPN_HOST=akses.bps.go.id
      - VPN_TEST_URL=https://fasih-sm.bps.go.id
      - VPN_TRUSTED_CERT=${VPN_TRUSTED_CERT}
      - VPN_USER=${VPN_USER}
      - VPN_PASS=${VPN_PASS}
      - VPN_COOKIE=${VPN_COOKIE}
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: [ "CMD-SHELL", "curl -fks --connect-timeout 5 https://fasih-sm.bps.go.id/oauth_login.html -o /dev/null && echo ok || exit 1" ]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    restart: unless-stopped
    stop_grace_period: 15s

  # --- RPA Engines (Behind VPN) ---
  rpa:
    build: ./rpa
    container_name: fasih-nexus-rpa
    network_mode: "service:vpn"
    labels:
      - "coolify.managed=false"
    environment:
      - DATABASE_URL=postgres://fasih:${POSTGRES_PASSWORD}@postgres:5432/fasih_dashboard
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      - PYTHONPATH=/app:/app/src
      - SKIP_DETAIL_FETCH=${SKIP_DETAIL_FETCH:-false}
      - FASIH_CONCURRENCY=${FASIH_CONCURRENCY:-3}
      - FETCH_CONCURRENCY=${FETCH_CONCURRENCY:-3}
      - TARGET_URL=${TARGET_URL:-https://fasih-sm.bps.go.id}
    depends_on:
      vpn:
        condition: service_started
    restart: unless-stopped

  vpn-auth:
    image: fasih-nexus-rpa:latest
    container_name: fasih-nexus-vpn-auth
    network_mode: "service:vpn"
    labels:
      - "coolify.managed=false"
    environment:
      - DATABASE_URL=postgres://fasih:${POSTGRES_PASSWORD}@postgres:5432/fasih_dashboard
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
    labels:
      - "coolify.managed=false"
    environment:
      - DATABASE_URL=postgres://fasih:${POSTGRES_PASSWORD}@postgres:5432/fasih_dashboard
      - S3_ACCESS_KEY=${S3_ACCESS_KEY:-fasihadmin}
      - S3_SECRET_KEY=${S3_SECRET_KEY:-fasihsecret}
      - S3_BUCKET=${S3_BUCKET:-survey-images}
      - S3_ENDPOINT=http://s3:8333
      - PYTHONPATH=/app:/app/src
    depends_on:
      vpn:
        condition: service_started
    command: python src/archiver.py
    restart: unless-stopped

  # --- Data Persistence ---
  postgres:
    image: postgres:16-alpine
    container_name: fasih-nexus-db
    networks:
      - fasih_internal
    labels:
      - "coolify.managed=false"
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
      - postgres
    environment:
      - WEED_FILER_POSTGRES_ENABLED=true
      - WEED_FILER_POSTGRES_HOSTNAME=postgres
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
  pg_data:
  seaweed_data:
```

## 🏗️ Dockerfiles
### File: `./rpa/Dockerfile`
```dockerfile
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:/app/src
WORKDIR /app

# System deps for Playwright Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libatk-bridge2.0-0 libdrm2 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libasound2 libpango-1.0-0 \
    libcairo2 libxkbcommon0 libgtk-3-0 libdbus-glib-1-2 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt && \
    playwright install chromium --with-deps

COPY . .

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### File: `./dashboard/Dockerfile`
```dockerfile
FROM oven/bun:1 AS build
WORKDIR /app
COPY package.json bun.lock* ./
RUN bun install --frozen-lockfile
COPY . .
RUN bun run build

FROM oven/bun:1-slim
WORKDIR /app
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*
COPY --from=build /app/client/dist/spa ./client/dist/spa
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/server ./server
COPY --from=build /app/package.json .
COPY --from=build /app/drizzle.config.ts .
COPY --from=build /app/entrypoint.sh .
RUN chmod +x entrypoint.sh
EXPOSE 3000
ENTRYPOINT ["./entrypoint.sh"]
```

### File: `./vpn/Dockerfile`
```dockerfile
FROM debian:12-slim AS builder

# Build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    automake \
    autoconf \
    pkg-config \
    libssl-dev \
    ca-certificates \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Build openfortivpn 1.22.1 from source (SAML cookie support added in 1.22.0)
RUN wget -q https://github.com/adrienverge/openfortivpn/archive/refs/tags/v1.22.1.tar.gz \
    && tar xzf v1.22.1.tar.gz \
    && cd openfortivpn-1.22.1 \
    && aclocal && autoconf && automake --add-missing \
    && ./configure --prefix=/usr --sysconfdir=/etc \
    && make -j$(nproc) \
    && make install DESTDIR=/install

FROM debian:12-slim

# Copy compiled openfortivpn
COPY --from=builder /install/usr /usr

# Runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 \
    ppp \
    curl \
    ca-certificates \
    libssl3 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Script untuk monitoring & reconnect
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
```

## 🔑 Environment Configuration (Examples)
### File: `./rpa/config/.env.example`
```text
# ===================================================
# FASIH-SM RPA Sync — Konfigurasi
# ===================================================
# Salin file ini menjadi .env dan isi nilainya

# Kredensial Login SSO BPS
SSO_USERNAME=your_username
SSO_PASSWORD=your_password

# Target Survey (nama persis seperti di tabel FASIH)
SURVEY_NAME=PEMUTAKHIRAN DTSEN PBI 2026

# Filter Wilayah (opsional, kosongkan jika tidak perlu filter)
FILTER_PROVINSI=KALIMANTAN BARAT
FILTER_KABUPATEN=KABUPATEN MEMPAWAH

# Rotasi filter: "pengawas" atau "pencacah"
# - pengawas: loop per pengawas, sub-loop pencacah jika >1000
# - pencacah: selalu loop per pencacah (lebih lambat tapi lebih aman)
FILTER_ROTATION=pengawas

# Scheduler: interval dalam menit (0 = jalankan sekali saja)
INTERVAL_MINUTES=30

# Database SQLite
DB_PATH=data/fasih_sync.db
```

### File: `./.env.example`
```text
# --- Database ---
POSTGRES_PASSWORD=your_secure_db_password

# --- Security ---
# Generate using: openssl rand -hex 32
ENCRYPTION_KEY=

# --- VPN Auth ---
VPN_USER=
VPN_PASS=
# Optional: Extraction dari cookie string browser (SVPNCOOKIE)
VPN_COOKIE=

# --- Coolify & Better-Auth ---
# Domain akses dashboard (cth: https://fasih.domain.com)
BETTER_AUTH_URL=
# Base URL publik (biasanya sama dengan BETTER_AUTH_URL)
PUBLIC_BASE_URL=
# Generate menggunakan: openssl rand -hex 32
BETTER_AUTH_SECRET=

# --- S3 Storage (SeaweedFS) ---
S3_ACCESS_KEY=fasihadmin
S3_SECRET_KEY=fasihsecret
S3_BUCKET=survey-images

# --- App Settings ---
FASIH_CONCURRENCY=3
SKIP_DETAIL_FETCH=false
# FASIH_URL default ke https://fasih-sm.bps.go.id
```

## 🚀 Core Entrypoints
### File: `rpa/src/app.py`
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
...
```

### File: `rpa/src/main.py`
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
3. Upsert ke SQLite
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
...
```

### File: `dashboard/server/index.ts`
```python
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
...
```


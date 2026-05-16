# Project Snapshot: FasihNexus
Generated at: Sat May 16 10:25:38 AM WIB 2026

## 📂 Project Structure
```text
Listing files respecting .gitignore:
rpa/test_cookie.py
scratch_benchmark.py
.env.example
.gitignore
.vscode/settings.json
GEMINI.md
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
      postgres:
        condition: service_healthy
    healthcheck:
      test: [ "CMD-SHELL", "curl -fks --connect-timeout 5 https://fasih-sm.bps.go.id/oauth_login.html -o /dev/null && echo ok || exit 1" ]
      interval: 30s
      timeout: 10s
      retries: 3
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
    volumes:
      - ./rpa:/app
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      - PYTHONPATH=/app:/app/src
      - SKIP_DETAIL_FETCH=${SKIP_DETAIL_FETCH:-false}
      - FASIH_CONCURRENCY=${FASIH_CONCURRENCY:-3}
      - FETCH_CONCURRENCY=${FETCH_CONCURRENCY:-3}
      - TARGET_URL=${TARGET_URL:-https://fasih-sm.bps.go.id}
    command: sh -c "echo '10.1.110.13 fasih-sm.bps.go.id' >> /etc/hosts && python -m uvicorn src.app:app --host 0.0.0.0 --port 8000"
    restart: unless-stopped

  vpn-auth:
    image: fasih-nexus-rpa:latest
    container_name: fasih-nexus-vpn-auth
    network_mode: "service:vpn"
    labels:
      - "coolify.managed=false"
    volumes:
      - ./rpa:/app
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    depends_on:
      vpn:
        condition: service_started
      rpa:
        condition: service_started
    command: sh -c "echo '10.1.110.13 fasih-sm.bps.go.id' >> /etc/hosts && python -m uvicorn src.app:app --host 0.0.0.0 --port 8001"
    restart: unless-stopped

  archiver:
    image: fasih-nexus-rpa:latest
    container_name: fasih-nexus-archiver
    network_mode: "service:vpn"
    labels:
      - "coolify.managed=false"
    volumes:
      - ./rpa:/app
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
  postgres:
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
  pg_data_v3:
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

## 🌐 Runtime Network Configuration
### Container: `fasih-nexus-vpn` (/etc/hosts)
```text
```

### Container: `fasih-nexus-rpa` (/etc/hosts)
```text
```

### Container: `fasih-nexus-vpn-auth` (/etc/hosts)
```text
```

## ⚙️ RPA Worker Modules
### File: `rpa/src/worker/__init__.py`
```python
```

### File: `rpa/src/worker/queue.py`
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

### File: `rpa/src/worker/fast_mode.py`
```python
import os
import asyncio
import random
from typing import List, Dict, Any, Optional

from db.repository import get_existing_modifications_by_ids, BatchUpserterBulk, SyncStats, normalize_bps_date
from state import sync_state

# Gunakan angka aman (5-8) agar sesi SSO tidak di-drop paksa oleh server BPS
FASIH_CONCURRENCY = int(os.getenv("FASIH_CONCURRENCY", "5"))

async def run_fast_sync(
    session,
    api_client: Any,
    survey_id: str,
    period_id: str,
    survey_config_id: str,
    prov_code: str,
    region_filter: Optional[str],
    region_full_code: Optional[str],
    region_group_id: str,
    filters_to_run: List[Dict[str, Any]],
    sync_log_id: int = None
) -> SyncStats:
    """
    Fast sync STEADY:
    - Safe concurrency to prevent session drop.
    - Targeted slicing for efficiency.
    - Robust error handling.
    """
    users_total = len(filters_to_run)
    sync_state.progress.users_total = users_total
    sync_state.progress.users_done = 0
    
    all_metadata_map = {}
    done_count = 0
    parent_full_code = region_full_code or region_filter
    
    sem = asyncio.Semaphore(FASIH_CONCURRENCY)
    
    async def _fetch_meta(f_user, page=1):
        payload = {
            "period_id": period_id,
            "prov_uuid": prov_code,
            "kab_uuid": region_filter if region_filter != prov_code else None,
            "kec_uuid": f_user.get("kec_uuid"),
            "desa_uuid": f_user.get("desa_uuid"),
            "pengawas_id": f_user.get("pengawas_id"),
            "pencacah_id": f_user.get("pencacah_id"),
            "region_group_id": region_group_id,
            "page_size": 1000,
            "page_number": page
        }
        async with sem:
            # Berikan jeda antar request agar tidak dianggap serangan/spike
            await asyncio.sleep(random.uniform(0.5, 1.5))
            res = await api_client.get_assignments_metadata(**payload)
            
            if res:
                total_current = len(all_metadata_map) + len(res)
                sync_state.progress.phase_label = f"🌏 Fetching: {total_current} records... (User: {f_user.get('label')})"
            return res

    async def _process_user(f_user):
        nonlocal done_count
        try:
            results = await _fetch_meta(f_user)
            if not results:
                return

            user_data = {m["id"]: m for m in results if m.get("id")}
            
            # --- TARGETED SLICING ---
            if len(results) >= 1000 and parent_full_code:
                print(f"   🔬 [CAP] {f_user.get('label')} hit 1000. Slicing...")
                
                # Coba ambil info wilayah dari data nyata
                sample = results[0]
                reg_meta = sample.get("regionMetadata") or sample.get("region", {})
                target_kec = reg_meta.get("kecId") or f_user.get("kec_uuid")
                
                if target_kec and target_kec != parent_full_code:
                    l3_list = [{"id": target_kec, "name": "Targeted Kecamatan"}]
                else:
                    l3_list = await api_client.get_sub_regions(3, region_group_id, parent_full_code)
                
                if l3_list:
                    async def _slice_l3(l3):
                        sub_f = f_user.copy()
                        sub_f["kec_uuid"] = l3.get("id")
                        sub_res = await _fetch_meta(sub_f)
                        local_map = {m["id"]: m for m in sub_res if m.get("id")}
                        
                        if len(sub_res) >= 1000:
                            # Slicing level 4 (Desa)
                            l4_list = await api_client.get_sub_regions(4, region_group_id, l3.get("fullCode"))
                            if l4_list:
                                async def _slice_l4(l4):
                                    sub_f4 = sub_f.copy()
                                    sub_f4["desa_uuid"] = l4.get("id")
                                    res4 = await _fetch_meta(sub_f4)
                                    return {m["id"]: m for m in res4 if m.get("id")}
                                
                                # Batasi concurrency level 4 agar tidak meledak
                                l4_results = []
                                for l4 in l4_list:
                                    l4_results.append(await _slice_l4(l4))
                                for r in l4_results: local_map.update(r)
                        return local_map

                    # Gunakan sequential untuk L3 di dalam user agar sesi stabil
                    for l3 in l3_list:
                        res_l3 = await _slice_l3(l3)
                        user_data.update(res_l3)
            
            all_metadata_map.update(user_data)
            
        except Exception as e:
            print(f"   ⚠️ Error processing user {f_user.get('label')}: {e}")
        finally:
            done_count += 1
            sync_state.progress.users_done = done_count

    print(f"🚀 Launching Steady Sync (Concurrency: {FASIH_CONCURRENCY}) for {users_total} users...")
    
    # Jalankan user dalam batch kecil (misal 10 user sekaligus) agar tidak memukul server di detik yang sama
    BATCH_SIZE = 10
    for i in range(0, users_total, BATCH_SIZE):
        batch = filters_to_run[i:i+BATCH_SIZE]
        await asyncio.gather(*[_process_user(f) for f in batch])

    unique_metadata = list(all_metadata_map.values())
    total_found = len(unique_metadata)
    print(f"\n   📊 Sync Finish: {total_found:,} unique records identified.")

    if not unique_metadata:
        return SyncStats()

    # --- STEP 2: Dedup check & Bulk Upsert ---
    sync_state.progress.phase_label = f"🔍 Dedup & Upserting {len(unique_metadata):,} records..."
    all_ids = [m["id"] for m in unique_metadata]
    
    existing_mods = {}
    CHUNK = 5000
    for i in range(0, len(all_ids), CHUNK):
        existing_mods.update(get_existing_modifications_by_ids(session, all_ids[i:i+CHUNK]))

    upserter = BatchUpserterBulk(session, batch_size=2000, sync_log_id=sync_log_id)
    total_skipped = 0
    
    for m in unique_metadata:
        rec_id = m.get("id")
        remote_date = m.get("dateModifiedRemote")
        norm_api = normalize_bps_date(remote_date)
        norm_db = normalize_bps_date(existing_mods.get(rec_id))

        if rec_id in existing_mods and norm_db == norm_api and norm_db != "":
            total_skipped += 1
        else:
            upserter.add({
                "_id": rec_id,
                "assignment": m,
                "responses": [],
                "_survey_config_id": survey_config_id
            })

    stats = upserter.finish()
    stats.total_skipped += total_skipped
    return stats
```

### File: `rpa/src/worker/full_mode.py`
```python
import os
import asyncio
import random
from typing import List, Dict, Any, Optional

from db.repository import get_existing_modifications_by_ids_batched, BatchUpserterBulk, SyncStats, normalize_bps_date
from pages.detail_page import fetch_assignments_concurrent
from state import sync_state

FASIH_CONCURRENCY = int(os.getenv("FASIH_CONCURRENCY", "3"))


async def _fetch_one(
    api_client: Any,
    period_id: str,
    prov_code: str,
    region_filter: Optional[str],
    region_group_id: str,
    f: Dict,
    semaphore: asyncio.Semaphore,
    index: int = 0
) -> tuple[Dict, List[Dict]]:
    """Fetch metadata 1 user, throttled by semaphore + jitter."""
    jitter = random.uniform(0, min(index * 0.2, 2.0))
    await asyncio.sleep(jitter)
    async with semaphore:
        try:
            results = await api_client.get_assignments_metadata(
                period_id,
                prov_uuid=prov_code,
                kab_uuid=region_filter if region_filter != prov_code else None,
                kec_uuid=f.get("kec_uuid"),
                desa_uuid=f.get("desa_uuid"),
                pengawas_id=f.get("pengawas_id"),
                pencacah_id=f.get("pencacah_id"),
                region_group_id=region_group_id
            )
            return f, results or []
        except Exception as e:
            print(f"   ⚠️ Error fetching {f.get('label', '?')}: {e}")
            return f, []


async def run_full_sync(
    session,
    api_client: Any,
    cookie_dict: Dict[str, str],
    survey_id: str,
    period_id: str,
    survey_config_id: str,
    prov_code: str,
    region_filter: Optional[str],
    region_full_code: Optional[str],
    region_group_id: str,
    filters_to_run: List[Dict[str, Any]],
    sync_log_id: int = None
) -> SyncStats:
    """
    Full sync: 
    1. Smart Metadata Fetch: Fan-out per user. Jika user > 1000 (cap), slice per-kecamatan.
    2. Streaming Detail Fetch: Fetch response detail JSON + real-time Batch Upsert.
    """
    DETAIL_CONCURRENCY = int(os.getenv("FETCH_CONCURRENCY", "100"))
    if DETAIL_CONCURRENCY < 10:
        DETAIL_CONCURRENCY = 100
    TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")

    users_total = len(filters_to_run)
    sem = asyncio.Semaphore(FASIH_CONCURRENCY)
    print(f"\n--- FASE 4: Full Mode — Smart Slicing & Streaming ({users_total} users) ---")

    # --- STEP 1: Metadata Fetch (concurrent) ---
    sync_state.progress.phase = "fetch_assignments"
    sync_state.progress.phase_label = f"⚡ Fan-out: fetching {users_total} users..."
    sync_state.progress.users_total = users_total
    sync_state.progress.users_done = 0

    # Use the pre-resolved parent full code for slicing (fallback to region_filter if missing)
    parent_full_code = region_full_code or region_filter
    if parent_full_code and len(str(parent_full_code)) > 20:
        print(f"   ⚠️ [RPA] Parent code is still a UUID: {parent_full_code}. Slicing might fail.")

    all_tasks = [
        _fetch_one(api_client, period_id, prov_code, region_filter, region_group_id, f, sem, idx)
        for idx, f in enumerate(filters_to_run)
    ]

    all_metadata_map: Dict[str, Dict] = {}
    done_count = 0
    
    async def _handle_results(f_user, results):
        nonlocal done_count
        done_count += 1
        sync_state.progress.users_done = done_count
        
        user_total_metadata = {m.get("id"): m for m in results if m.get("id")}
        
        # If capped at 1000, we must slice immediately
        if len(results) >= 1000 and parent_full_code:
            print(f"   ⚠️  [CAP] {f_user.get('label')} hit {len(results)} limit. Diving into sub-regions (Parent: {parent_full_code})...")
            sync_state.progress.phase_label = f"🔬 Slicing {f_user.get('label')}..."
            
            l3_list = await api_client.get_sub_regions(3, region_group_id, parent_full_code)
            if l3_list:
                async def _slice_l3(l3):
                    sub_f = f_user.copy()
                    sub_f["kec_uuid"] = l3.get("id")
                    sub_f["label"] = f"{f_user.get('label')} - {l3.get('name')}"
                    sync_state.progress.phase_label = f"🔬 Slicing {f_user.get('label')} -> {l3.get('name')}..."
                    _, sub_res = await _fetch_one(api_client, period_id, prov_code, region_filter, region_group_id, sub_f, sem, 0)
                    local_map = {m.get("id"): m for m in sub_res if m.get("id")}
                    
                    # Nested Slicing to Level 4 (e.g. RBM)
                    if len(sub_res) >= 1000:
                        l4_list = await api_client.get_sub_regions(4, region_group_id, l3.get("fullCode"))
                        if l4_list:
                            print(f"      ⚠️ L3 {l3.get('name')} still capped. Diving to L4...")
                            async def _slice_l4(l4):
                                sub_f4 = sub_f.copy()
                                sub_f4["desa_uuid"] = l4.get("id")
                                _, res4 = await _fetch_one(api_client, period_id, prov_code, region_filter, region_group_id, sub_f4, sem, 0)
                                return {m.get("id"): m for m in res4 if m.get("id")}
                            
                            l4_results = await asyncio.gather(*[_slice_l4(l4) for l4 in l4_list])
                            for r in l4_results: local_map.update(r)
                    return local_map

                l3_results = await asyncio.gather(*[_slice_l3(l3) for l3 in l3_list])
                for r in l3_results: user_total_metadata.update(r)

        # Merge this user's results into global map
        all_metadata_map.update(user_total_metadata)

        found_for_this_user = len(user_total_metadata)
        sync_state.progress.phase_label = (
            f"⚡ [{done_count}/{users_total}] {f_user.get('label','?')}: {found_for_this_user} → total {len(all_metadata_map)}"
        )
        status = "✅" if found_for_this_user else "○"
        print(f"   {status} [{done_count}/{users_total}] {f_user.get('label','?')}: {found_for_this_user} records")

    for coro in asyncio.as_completed(all_tasks):
        f, results = await coro
        await _handle_results(f, results)

    unique_metadata = list(all_metadata_map.values())
    total_found = len(unique_metadata)
    print(f"\n   📊 Total unik (after adaptive immediate slicing): {total_found:,} assignments")

    if not unique_metadata:
        return SyncStats()

    # --- STEP 2: Bulk dedup check ---
    sync_state.progress.phase_label = f"🔍 Dedup check {total_found:,} records..."
    all_ids = [m["id"] for m in unique_metadata if m.get("id")]
    existing_mods = get_existing_modifications_by_ids_batched(session, all_ids)

    to_fetch_links = []
    total_skipped = 0

    for m in unique_metadata:
        rec_id = m.get("id")
        api_val = m.get("dateModifiedRemote")
        db_val = existing_mods.get(rec_id)

        norm_api = normalize_bps_date(api_val)
        norm_db = normalize_bps_date(db_val)

        if rec_id in existing_mods and norm_db == norm_api and norm_db != "":
            total_skipped += 1
        else:
            to_fetch_links.append(f"{TARGET_URL}/assignment-detail/{rec_id}/{survey_id}/1")

    print(f"   ⏭️  Skipped (Delta): {total_skipped:,} | To fetch detail: {len(to_fetch_links):,}")

    if not to_fetch_links:
        stats = SyncStats()
        stats.total_skipped = total_skipped
        return stats

    # --- STEP 3 & 4: Streaming Fetch & Upsert ---
    # Inisialisasi upserter SEBELUM fetch loop agar bisa streaming commit
    sync_state.progress.phase = "streaming_sync"
    sync_state.progress.phase_label = f"🚀 Streaming fetch & upsert {len(to_fetch_links):,} records..."
    sync_state.progress.assignments_total = len(to_fetch_links)
    sync_state.progress.assignments_fetched = 0

    upserter = BatchUpserterBulk(session, batch_size=2000, sync_log_id=sync_log_id)

    def on_progress(fetched_count: int, total: int, data_json: Optional[Dict]):
        sync_state.progress.assignments_fetched = fetched_count
        sync_state.progress.phase_label = (
            f"⬇️  Detail: {fetched_count}/{total} fetched & streamed..."
        )
        if data_json:
            data_json["_survey_config_id"] = survey_config_id
            upserter.add(data_json)

    # Menjalankan concurrent fetch, tapi upsert terjadi via callback di dalamnya
    # fetch_assignments_concurrent tidak lagi perlu return list raksasa
    await fetch_assignments_concurrent(
        cookie_dict, to_fetch_links,
        concurrency=DETAIL_CONCURRENCY,
        on_progress=on_progress
    )

    # Final commit untuk sisa batch terakhir
    stats = upserter.finish()
    stats.total_skipped += total_skipped
    
    print(f"   ✅ Full sync selesai: processed={stats.total_fetched:,}, new={stats.total_new:,}, skipped={stats.total_skipped:,}")
    return stats
```

### File: `rpa/src/worker/scheduler.py`
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
            # Normal syncs take 1-10 mins. 45 mins is very safe.
            from sqlalchemy import text
            stale_cutoff = datetime.now(timezone.utc).replace(tzinfo=None)
            result = session.execute(
                text("UPDATE sync_logs SET status = 'failed', notes = 'Marked as failed by auto-cleanup (stuck > 45m)', finished_at = :now "
                     "WHERE status = 'running' AND started_at < :cutoff"),
                {"now": datetime.now(timezone.utc), "cutoff": datetime.now(timezone.utc) - asyncio.Duration(minutes=45) if hasattr(asyncio, 'Duration') else datetime.now(timezone.utc).replace(minute=0)} 
            )
            # Actually, let's do it properly with timedelta
            from datetime import timedelta
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=45)
            stale_jobs = session.query(SyncLog).filter(SyncLog.status == "running", SyncLog.started_at < cutoff).all()
            if stale_jobs:
                print(f"🧹 Scheduler: Found {len(stale_jobs)} stale job(s). Cleaning up...", flush=True)
                for job in stale_jobs:
                    job.status = "failed"
                    job.notes = f"Killed by auto-cleanup (stuck since {job.started_at})"
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

### File: `rpa/src/worker/job_runner.py`
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
from connectivity import ensure_connected


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
                                    "pengawas_id": user['userId'],
                                    "pencacah_id": None
                                })
                        else:
                            for idx, user in enumerate(pengawas_list):
                                filters_to_run.append({
                                    "label": f"[{idx+1}/{len(pengawas_list)}] Pengawas: {user['fullname']}",
                                    "pengawas_id": user['userId'],
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

## 📄 Key Source Files
### File: `vpn/entrypoint.sh`
```bash
#!/bin/sh

# Base config
mkdir -p /etc/openfortivpn

# Add public DNS fallback so we can always resolve akses.bps.go.id for auto-reconnect
echo "nameserver 8.8.8.8" >> /etc/resolv.conf
echo "nameserver 1.1.1.1" >> /etc/resolv.conf

# Clean up only specifically if we need to, but let's avoid wiping extra_hosts for now
# as it breaks fasih-sm.bps.go.id pinning from docker-compose.

# Inject postgres IP into /etc/hosts so it survives openfortivpn overwriting /etc/resolv.conf
# This allows the RPA container (which shares the vpn network) to still reach the database
POSTGRES_IP=$(getent hosts postgres | awk '{print $1}')
# 📉 Set eth0 MTU to 1200 to prevent fragmentation on BPS network
echo "📉 Setting eth0 MTU to 1200..."
ip link set eth0 mtu 1200 2>/dev/null || true

GATEWAY_IP=$(ip route | grep default | awk '{print $3}')

if [ -n "$POSTGRES_IP" ]; then
    echo "📌 Mapping postgres -> $POSTGRES_IP in /etc/hosts"
    echo "$POSTGRES_IP postgres" >> /etc/hosts
fi

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
                    kill "$VPN_PID" 2>/dev/null
                fi
                LAST_COOKIE="$CURRENT_DB_COOKIE"
            fi
        fi
    done
}

monitor_cookie_changes &

# SMART Route Enforcement Helper
apply_smart_routing() {
    echo "⏳ Waiting for interface ppp0 to apply Smart Routing..."
    for i in $(seq 1 30); do
        if [ -d "/sys/class/net/ppp0" ]; then
            # Wait for ppp0 to get an IP address so the device is truly UP for routing
            if ip addr show ppp0 2>/dev/null | grep -q "inet "; then
                echo "✅ Interface ppp0 is fully UP (has IP). Applying route fixes..."
                
                # Resolve target and force route
                TARGET_DOMAIN="fasih-sm.bps.go.id"
                echo "🔍 Resolving $TARGET_DOMAIN..."
                
                # DNS might take a few seconds to stabilize after ppp0 is up
                TARGET_IP=""
                for j in 1 2 3 4 5; do
                    TARGET_IP=$(getent hosts "$TARGET_DOMAIN" | awk 'NR==1 {print $1}')
                    [ -n "$TARGET_IP" ] && break
                    sleep 2
                done
                
                if [ -n "$TARGET_IP" ]; then
                    echo "📍 Site $TARGET_DOMAIN resolved to $TARGET_IP"
                    
                    # Pin in /etc/hosts so DNS outages during reconnects don't break resolution
                    # Safe technique for Docker bind mounts
                    grep -v "$TARGET_DOMAIN" /etc/hosts > /tmp/hosts && cat /tmp/hosts > /etc/hosts
                    echo "$TARGET_IP $TARGET_DOMAIN" >> /etc/hosts
                    echo "📌 Pinned $TARGET_DOMAIN -> $TARGET_IP in /etc/hosts"

                    # 🔌 INJECT DNS (Ensures shared network containers like RPA can resolve internal domains)
                    echo "🔌 Injecting BPS Nameservers into /etc/resolv.conf..."
                    # We use a temporary file to avoid 'Device or resource busy' with sed -i on bind mounts
                    echo -e "nameserver 10.10.11.11\nnameserver 10.10.11.12\n$(cat /etc/resolv.conf)" > /etc/resolv.conf
                    echo "✅ DNS Injected."
                    
                    # Check if already routed via ppp0
                    if ! ip route get "$TARGET_IP" 2>/dev/null | grep -q "dev ppp0"; then
                        echo "🛠️  Forcing route for $TARGET_IP via ppp0 (Fixing missing BPS advertisement)..."
                        # Extra retry for route add just in case
                        for k in 1 2 3; do
                            ip route add "$TARGET_IP"/32 dev ppp0 2>/dev/null && break
                            echo "⏳ Retrying route add..."
                            sleep 1
                        done
                    fi

                    # 🚀 ROUTE BPS DNS via ppp0 (CRITICAL)
                    # The BPS DNS servers (172.16.2.2/3) are often in the 172.16.0.0/12 range
                    # which Docker uses for internal networking. We must force them to the VPN.
                    echo "🌐 Routing BPS DNS servers via ppp0..."
                    ip route add 172.16.2.2/32 dev ppp0 2>/dev/null || true
                    ip route add 172.16.2.3/32 dev ppp0 2>/dev/null || true
                    
                    # Also pin the 10.0.0.0/8 range to ppp0 just in case
                    ip route add 10.0.0.0/8 dev ppp0 2>/dev/null || true
                    
                    
                    # 📉 Set MTU to 1200 to prevent fragmentation
                    echo "📉 Setting ppp0 MTU to 1200..."
                    ip link set dev ppp0 mtu 1200 || true
                    
                    echo "✅ BPS Routing updated."
                else
                    echo "⚠️  Could not resolve $TARGET_DOMAIN inside VPN (DNS Timeout)."
                fi
                return 0
            fi
        fi
        sleep 1
    done
    echo "❌ Interface ppp0 never appeared. Skipping Smart Routing."
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



    # Priority: database > env var
    COOKIE=""
    
    # Try reading cookie from PostgreSQL
    if [ -n "$DATABASE_URL" ]; then
        DB_COOKIE=$(psql "$DATABASE_URL" -t -A -c "SELECT value FROM system_settings WHERE key='vpn_cookie'" 2>/dev/null)
        if [ -n "$DB_COOKIE" ]; then
            COOKIE="$DB_COOKIE"
            echo "🔑 Cookie loaded from database (Length: ${#COOKIE})"
        fi
    fi

    # Fallback to env var
    if [ -z "$COOKIE" ] && [ -n "${VPN_COOKIE}" ]; then
        COOKIE="${VPN_COOKIE}"
        echo "🔑 Cookie loaded from env var"
    fi

    if [ -n "$COOKIE" ]; then
        VAL=$(echo "$COOKIE" | grep -o 'SVPNCOOKIE=[^;]*' | sed 's/^SVPNCOOKIE=//')
        if [ -z "$VAL" ]; then VAL="$COOKIE"; fi

        echo "🔗 Connecting with cookie..."
        # Run VPN
        echo "⛓️ Establishing tunnel (Cookie Mode)..."
        openfortivpn ${VPN_HOST}:${VPN_PORT:-443} \
            --cookie="$VAL" \
            ${VPN_TRUSTED_CERT:+--trusted-cert "$VPN_TRUSTED_CERT"} \
            --set-dns=1 \
            --pppd-use-peerdns=1 &
        VPN_PID=$!
        apply_smart_routing &
        wait $VPN_PID
    else
        echo "👤 Using Username/Password for connection..."
        cat <<EOF > /etc/openfortivpn/config
host = ${VPN_HOST}
port = ${VPN_PORT:-443}
username = ${VPN_USER}
password = ${VPN_PASS}
${VPN_TRUSTED_CERT:+trusted-cert = $VPN_TRUSTED_CERT}
set-dns = 1
pppd-use-peerdns = 1
EOF
        # Run VPN
        echo "⛓️ Establishing tunnel (Config Mode)..."
        openfortivpn -c /etc/openfortivpn/config &
        VPN_PID=$!
        apply_smart_routing &
        wait $VPN_PID
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

### File: `dashboard/entrypoint.sh`
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
psql "$DATABASE_URL" -c "
DO \$\$ 
DECLARE
    r RECORD;
BEGIN 
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

### File: `rpa/src/connectivity.py`
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
        # Check ppp0 as secondary signal
        has_ppp = os.path.exists("/sys/class/net/ppp0")
        if has_ppp:
            # Interface exists — tunnel is up, just slow
            return True, "Reachable (ppp0 UP, HTTP slow)"
        return False, "Connection timeout"
    except Exception as e:
        has_ppp = os.path.exists("/sys/class/net/ppp0")
        err_type = type(e).__name__
        err_msg = str(e)
        if has_ppp:
            return True, f"Reachable (ppp0 UP, probe error: {err_type})"
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
            print("   ❌ Tidak ada survey aktif untuk digunakan sebagai kredensial VPN refresh.")
            print("   ⚠️  Melanjutkan sync meski VPN mungkin bermasalah...")
            return False

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

        print("   ⚠️ Cookie diperbarui tapi FASIH masih unreachable setelah 60s.")
        print("   ⚠️  Melanjutkan sync — mungkin tunnel sudah up tapi check belum stabil...")
        return False

    except Exception as e:
        import traceback
        print(f"   ❌ Self-healing error: {e}")
        traceback.print_exc()
        return False
    finally:
        session.close()
```

### File: `rpa/src/auth.py`
```python
"""
Auth — Automated Login SSO BPS via Keycloak
"""
import os
import asyncio
from datetime import datetime
from typing import Tuple, Dict, Optional
from playwright.async_api import Page, async_playwright


TARGET_URL = os.getenv("TARGET_URL", "https://fasih-sm.bps.go.id")

async def launch_stealth_browser(p):
    return await p.chromium.launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox"
        ]
    )

async def new_stealth_context(browser, **kwargs):
    kwargs.setdefault("ignore_https_errors", True)
    kwargs.setdefault("user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    context = await browser.new_context(**kwargs)
    await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return context

async def auto_login(page: Page, username: str, password: str) -> Tuple[bool, Dict, str]:
    """
    Otomasi login ke FASIH via SSO BPS.
    """
    try:
        print("🔐 [Auth] Membuka halaman login FASIH...")
        await page.goto(f"{TARGET_URL}/oauth_login.html", wait_until="domcontentloaded", timeout=120000)

        # Check if already logged in
        if "/oauth_login.html" not in page.url and "/login" not in page.url:
            print("   ✅ [Auth] Sudah login (Session valid).")
            return True, {c['name']: c['value'] for c in await page.context.cookies()}, ""

        print("   🖱️ [Auth] Mengklik 'Login SSO BPS'...")
        try:
            await page.wait_for_selector("a.login-button", state="visible", timeout=60000)
            await page.click("a.login-button")
        except Exception:
            await page.click("text='Login SSO BPS'")

        print("   ⌛ [Auth] Menunggu halaman Keycloak...")
        await page.wait_for_url("**/sso.bps.go.id/**", timeout=120000)
        
        # Wait for form
        await page.wait_for_selector("input#username", state="visible", timeout=60000)

        print(f"   ⌨️ [Auth] Mengisi kredensial: {username[:3]}***")
        await page.fill("input#username", username, timeout=60000)
        await page.fill("input#password", password, timeout=60000)
        
        # Click login and wait for either redirect or error
        print("   🚀 [Auth] Submit login & Polling...")
        await asyncio.sleep(1) # Small delay for stability
        await page.click("input#kc-login", force=True, timeout=60000)

        # Start polling for FASIH session cookies early as fallback for slow redirect
        for i in range(60): # 120s total
            cookies = await page.context.cookies()
            found_xsrf = next((c['value'] for c in cookies if c['name'].upper() == 'XSRF-TOKEN'), None)
            if found_xsrf:
                print(f"   ✅ [Auth] Session detected via cookies (Iteration {i})!")
                return True, {c['name']: c['value'] for c in cookies}, ""
            
            # Check for Keycloak errors
            if await page.locator("#input-error").count() > 0:
                err = await page.locator("#input-error").text_content()
                print(f"   ❌ [Auth] SSO Error: {err}")
                return False, {}, err
            
            if i % 5 == 0:
                names = [c['name'] for c in cookies]
                print(f"   ⏳ [Auth] Polling cookies ({i*2}s)... Found: {names}")
                
            await asyncio.sleep(2)

        print("   🔃 [Auth] Menunggu redirect ke FASIH...")
        try:
            # Flexible match for any FASIH domain page after login
            await page.wait_for_url(lambda url: "fasih-sm.bps.go.id" in url and "sso.bps.go.id" not in url, timeout=60000)
            print(f"   ✅ [Auth] Redirect sukses: {page.url}")
        except Exception as e:
            # Check if we are stuck on Keycloak with an error message
            error_msg = await page.locator("#input-error").text_content() if await page.locator("#input-error").count() > 0 else str(e)
            print(f"   ❌ [Auth] Redirect gagal: {error_msg}")
            # Take screenshot for debugging (saved in container)
            await page.screenshot(path="/tmp/auth_error.png")
            return False, {}, f"Redirect failed: {error_msg}"
        
        cookies = await page.context.cookies()
        cookie_dict = {c['name']: c['value'] for c in cookies}
        
        return True, cookie_dict, ""

    except Exception as e:
        print(f"   ❌ [Auth] Fatal error: {e}")
        return False, {}, str(e)

async def fetch_vpn_cookie(username: str, password: str) -> str | None:
    """
    Otomasi ambil SVPNCOOKIE dari akses.bps.go.id.
    """
    try:
        async with async_playwright() as p:
            browser = await launch_stealth_browser(p)
            context = await browser.new_context(ignore_https_errors=True)
            page = await context.new_page()
            
            print(f"🚀 [Auth] Membuka portal...")
            await page.goto("https://akses.bps.go.id/remote/login?lang=en", wait_until="domcontentloaded", timeout=120000)
            
            print(f"🚀 [Auth] Mengklik SAML/SSO...")
            await page.click("#saml-login-bn", timeout=60000)
            
            print(f"🚀 [Auth] Menunggu Keycloak...")
            await page.wait_for_selector("#username", timeout=120000)
            
            print(f"🚀 [Auth] Login SSO...")
            await page.fill("#username", username)
            await page.fill("#password", password)
            
            # Start polling in background while we click
            print(f"🚀 [Auth] Submit & Polling...")
            await page.click("#kc-login")
            
            vpn_cookie = None
            for _ in range(60): # 120s total polling
                cookies = await context.cookies()
                found = next((c['value'] for c in cookies if c['name'] == 'SVPNCOOKIE'), None)
                if found:
                    vpn_cookie = found
                    print(f"✅ [Auth] Cookie found!")
                    break
                await asyncio.sleep(2)
                
            await browser.close()
            return vpn_cookie

    except Exception as e:
        print(f"❌ [Auth] Error: {e}")
        return None
            
    except Exception as e:
        print(f"   ❌ Error saat fetch_vpn_cookie: {str(e)}")
        if browser: await browser.close()
        return None
```

### File: `dashboard/server/routes/sync.ts`
```typescript
import { Elysia } from "elysia";
import { db } from "../db";
import { surveyConfigs, systemSettings } from "../db/schema";
import { eq } from "drizzle-orm";
import { createHash, createDecipheriv } from "crypto";

const RPA_URL = process.env.RPA_URL || "http://vpn:8000";
const VPN_AUTH_URL = process.env.VPN_AUTH_URL || "http://vpn:8001";

function decryptPassword(ciphertext: string): string {
    const key = process.env.ENCRYPTION_KEY || "";
    if (!key) throw new Error("ENCRYPTION_KEY not set");
    const derivedKey = createHash("sha256").update(key).digest();
    const parts = ciphertext.split(":");
    const iv = Buffer.from(parts[0]!, "hex");
    const encrypted = Buffer.from(parts[1]!, "hex");
    const decipher = createDecipheriv("aes-256-cbc", derivedKey, iv);
    return decipher.update(encrypted).toString("utf8") + decipher.final("utf8");
}

import { requireAuth } from "../middleware/auth";

const lastLookup = new Map<string, number>();

export const syncRoutes = new Elysia({ prefix: "/api/surveys" })
    .use(requireAuth)
    // Trigger sync for a survey
    .post("/:id/sync", async ({ params, set }) => {
        const [survey] = await db
            .select()
            .from(surveyConfigs)
            .where(eq(surveyConfigs.id, params.id));

        if (!survey) {
            set.status = 404;
            return { error: "Survey not found" };
        }

        // Guard: Check if RPA is already busy
        try {
            const statusResp = await fetch(`${RPA_URL}/status`, { signal: AbortSignal.timeout(5000) });
            if (statusResp.ok) {
                const status = await statusResp.json() as any;
                if (status.is_running && status.active_job?.survey_config_id === survey.id) {
                    set.status = 409;
                    return { error: "Sync for this survey is already running in background." };
                }
            }
        } catch (e) {
            console.warn("RPA status check failed, proceeding anyway...", e);
        }

        // Decrypt password and send to RPA
        const password = decryptPassword(survey.ssoPasswordEncrypted);

        const response = await fetch(`${RPA_URL}/sync`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                survey_config_id: survey.id,
                survey_name: survey.surveyName,
                sso_username: survey.ssoUsername,
                sso_password: password,
                filter_provinsi: survey.filterProvinsi || "",
                filter_kabupaten: survey.filterKabupaten || "",
                filter_rotation: survey.filterRotation || "pengawas",
            }),
            signal: AbortSignal.timeout(10000)
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            set.status = response.status === 401 ? 401 : 400;
            return { error: (err as any).detail || `RPA responded with ${response.status}` };
        }

        return await response.json();
    })

    // Get RPA sync status
    .get("/sync/status", async () => {
        try {
            const response = await fetch(`${RPA_URL}/status`, { signal: AbortSignal.timeout(15000) });
            return await response.json();
        } catch {
            return { is_running: false, error: "RPA service unavailable" };
        }
    })

    // Get VPN connection status from RPA
    .get("/vpn/status", async () => {
        try {
            const [checkRes, statusRes] = await Promise.all([
                fetch(`${RPA_URL}/vpn/check`, { signal: AbortSignal.timeout(10000) }),
                fetch(`${RPA_URL}/status`, { signal: AbortSignal.timeout(5000) })
            ]);
            
            const vpnInfo = await checkRes.json() as any;
            const rpaInfo = await statusRes.json() as any;

            return { 
                ...vpnInfo, 
                is_fetching: rpaInfo.is_vpn_fetching 
            };
        } catch {
            return { connected: false, error: "RPA service unavailable" };
        }
    })

    // Cancel a queued sync job
    .delete("/sync/:jobId", async ({ params }) => {
        try {
            const response = await fetch(`${RPA_URL}/sync/${params.jobId}`, {
                method: "DELETE",
            });
            return await response.json();
        } catch {
            return { error: "RPA service unavailable" };
        }
    })

    // Update VPN cookie (store in PostgreSQL for VPN container to read)
    .post("/vpn/cookie", async ({ body, set }) => {
        const { cookie } = body as { cookie: string };
        if (!cookie || cookie.trim().length < 10) {
            set.status = 400;
            return { error: "Cookie is empty or too short" };
        }
        await db
            .insert(systemSettings)
            .values({ key: "vpn_cookie", value: cookie.trim(), updatedAt: new Date() })
            .onConflictDoUpdate({
                target: systemSettings.key,
                set: { value: cookie.trim(), updatedAt: new Date() },
            });
        return { success: true, message: "Cookie updated. VPN will reconnect automatically." };
    })

    // Clear VPN cookie (reverts to env var)
    .delete("/vpn/cookie", async () => {
        await db
            .delete(systemSettings)
            .where(eq(systemSettings.key, "vpn_cookie"));
        return { success: true, message: "Cookie cleared. Using env var fallback." };
    })

    // ===== FASIH Lookup (untuk wizard Add Survey) =====

    // Simple in-memory rate limiter for proxy lookups
    .onBeforeHandle(({ user, path, set }: any) => {
        if (path.includes("/fasih/")) {
            const now = Date.now();
            const last = lastLookup.get(user!.id) || 0;
            if (now - last < 5000) { // 5 seconds throttle
                set.status = 429;
                return { error: "Too many requests. Please wait 5s." };
            }
            lastLookup.set(user!.id, now);
        }
    })

    // Lookup surveys + provinces dari FASIH API (memerlukan SSO login ~15 detik)
    .post("/fasih/lookup", async ({ body, set }) => {
        const { ssoUsername, ssoPassword } = body as { ssoUsername: string; ssoPassword: string };
        
        // Input Validation
        if (!ssoUsername || !ssoUsername.includes("@bps.go.id")) {
            set.status = 400;
            return { error: "Invalid SSO Username format" };
        }

        const response = await fetch(`${RPA_URL}/lookup/metadata`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ sso_username: ssoUsername, sso_password: ssoPassword }),
        });

        if (!response.ok) {
            const contentType = response.headers.get("content-type");
            let detail = `RPA error ${response.status}`;
            
            if (contentType && contentType.includes("application/json")) {
                const err = await response.json().catch(() => ({}));
                detail = (err as any).detail || detail;
            } else {
                // If RPA returns 500 HTML or plain text
                const text = await response.text().catch(() => "");
                console.error(`RPA Non-JSON Error (${response.status}):`, text.substring(0, 200));
                if (response.status === 503 || response.status === 502) {
                    detail = "RPA service is unavailable or VPN is disconnected.";
                }
            }
            set.status = response.status === 401 ? 401 : 400;
            return { error: detail };
        }
        return await response.json();
    })

    // Lookup kabupaten untuk satu provinsi
    .post("/fasih/kabupaten", async ({ body, set }) => {
        const { ssoUsername, ssoPassword, provFullCode } = body as {
            ssoUsername: string;
            ssoPassword: string;
            provFullCode: string;
        };

        // Input Validation
        if (!ssoUsername || !ssoUsername.includes("@bps.go.id")) {
            set.status = 400;
            return { error: "Invalid SSO Username format" };
        }
        if (!provFullCode || !/^\d+$/.test(provFullCode)) {
            set.status = 400;
            return { error: "Invalid Province Code format" };
        }

        const response = await fetch(`${RPA_URL}/lookup/kabupaten`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                sso_username: ssoUsername,
                sso_password: ssoPassword,
                prov_full_code: provFullCode,
            }),
        });

        if (!response.ok) {
            const contentType = response.headers.get("content-type");
            let detail = `RPA error ${response.status}`;
            if (contentType && contentType.includes("application/json")) {
                const err = await response.json().catch(() => ({}));
                detail = (err as any).detail || detail;
            } else {
                if (response.status === 503 || response.status === 502) {
                    detail = "RPA service or VPN is down.";
                }
            }
            set.status = response.status === 401 ? 401 : 400;
            return { error: detail };
        }
        return await response.json();
    })
    
    // Explicitly trigger VPN auto-fetch from UI
    .post("/vpn/auto-fetch", async ({ set }) => {
        console.log("👆 UI Manual Trigger: VPN Auto-Fix requested.");
        
        const [survey] = await db
            .select()
            .from(surveyConfigs)
            .where(eq(surveyConfigs.isActive, true))
            .limit(1);

        if (!survey) {
            set.status = 404;
            return { error: "No active survey to borrow credentials from" };
        }

        const password = decryptPassword(survey.ssoPasswordEncrypted);
        
        try {
            const fetchRes = await fetch(`${VPN_AUTH_URL}/vpn/auto-fetch`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    sso_username: survey.ssoUsername,
                    sso_password: password
                }),
                signal: AbortSignal.timeout(300000)
            });

            if (!fetchRes.ok) {
                const text = await fetchRes.text().catch(() => "");
                let detail = `Auth service error ${fetchRes.status}`;
                try {
                    const err = JSON.parse(text);
                    detail = err.detail || detail;
                } catch {
                    if (text && text.length < 100) detail = text;
                }
                
                console.error(`   ❌ VPN Auto-fetch failed: ${detail}`);
                set.status = fetchRes.status === 401 ? 401 : 400;
                return { error: detail };
            }

            return await fetchRes.json();
        } catch (e: any) {
            console.error(`   ❌ VPN Auto-fetch connection failed: ${e.message}`);
            set.status = 503;
            return { error: `Gagal menghubungi service VPN-Auth: ${e.message}` };
        }
    });

// Use 127.0.0.1 instead of localhost for local dev to avoid IPv6 issues
const RPA_API_URL = RPA_URL.replace("localhost", "127.0.0.1");

// ===== VPN Auto-Pilot Background Loop =====
// Check VPN status periodically. If disconnected, trigger RPA to auto-fetch the cookie.
const checkVpnAndFetchCookie = async () => {
    try {
        // Use a strict timeout for the health check to avoid blocking the loop
        const statusRes = await fetch(`${RPA_API_URL}/vpn/check`, { 
            signal: AbortSignal.timeout(15000) 
        }).then(r => r.json()).catch(() => ({ connected: false })) as any;

        if (!statusRes.connected) {
            console.log("⚠️ VPN Disconnected detected! Attempting auto-fetch...");
            
            // 2. Identify an active survey to borrow credentials for auto-fetch
            let survey;
            try {
                [survey] = await db
                    .select()
                    .from(surveyConfigs)
                    .where(eq(surveyConfigs.isActive, true))
                    .limit(1);
            } catch (dbErr: any) {
                if (dbErr.message?.includes('does not exist')) {
                    console.log("   ⚠️ Table 'survey_configs' does not exist yet. Skipping auto-pilot.");
                } else if (dbErr.message?.includes('uuid')) {
                    console.error("   ❌ Database Schema Mismatch (UUID Cast Error). Please run manual migration.");
                } else {
                    console.error("   ❌ Database error in VPN Auto-Pilot:", dbErr.message);
                }
                return;
            }

            if (!survey) {
                // Fallback: Check if we have Master SSO credentials in .env
                if (process.env.VPN_USER && process.env.VPN_PASS) {
                    console.log("   🚀 No active survey found, but using Master SSO (VPN_USER) for bootstrap...");
                    const fetchRes = await fetch(`${VPN_AUTH_URL}/vpn/auto-fetch`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            sso_username: process.env.VPN_USER,
                            sso_password: process.env.VPN_PASS
                        }),
                        signal: AbortSignal.timeout(300000)
                    });
                    
                    if (fetchRes.ok) {
                        console.log("   ✅ VPN bootstrap triggered successfully!");
                    } else {
                        console.log(`   ❌ Failed to trigger VPN bootstrap: ${fetchRes.status}`);
                    }
                    return;
                }

                console.log("   ❌ No active survey found and no Master SSO (VPN_USER) configured. Cannot auto-pilot.");
                return;
            }

            console.log(`   🔑 Borrowing credentials from: ${survey.ssoUsername} (Survey: ${survey.surveyName})`);
            const password = decryptPassword(survey.ssoPasswordEncrypted);
            
            const fetchRes = await fetch(`${VPN_AUTH_URL}/vpn/auto-fetch`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    sso_username: survey.ssoUsername,
                    sso_password: password
                }),
                signal: AbortSignal.timeout(300000)
            });

            if (fetchRes.ok) {
                console.log("   ✅ VPN auto-fetch triggered successfully! RPA is grabbing the cookie.");
            } else {
                console.log(`   ❌ Failed to trigger RPA VPN auto-fetch: ${fetchRes.status}`);
            }
        }
    } catch (err: any) {
        console.error("❌ Fatal Error in VPN Auto-Pilot loop:", err.message);
    }
};

// Check every 60 seconds
setInterval(checkVpnAndFetchCookie, 60000);
// Also run it 5 seconds after the dashboard boots up (giving time for RPA to start)
setTimeout(checkVpnAndFetchCookie, 5000);
```

### File: `.env`
```text
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
STORAGE_LOCAL_DOMAIN=http://localhost:3000
PUBLIC_BASE_URL=http://localhost:9000

# Better Auth
BETTER_AUTH_SECRET=c6065adbae6f2d29b152b61de771feb2c1508a8281677ad81f9f190c9675b6c2
BETTER_AUTH_URL=http://localhost:3000
```

## 🚀 Entrypoint Summaries
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


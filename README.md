# CDC — FASIH-SM Data Sync Platform

Platform otomasi sinkronisasi data survei dari aplikasi **FASIH-SM** (fasih-sm.bps.go.id) milik BPS. Sistem berjalan sebagai multi-container Docker dan terdiri dari 5 komponen utama.

## Fitur Utama

- 🔄 **Sinkronisasi Otomatis** — Robot RPA login ke FASIH-SM via SSO dan mengambil data assignment survei
- 🖼️ **CDC Image Vault** — Archiver otomatis meng-mirror foto BPS (presigned S3 URL yang kadaluarsa ≤7 hari) ke penyimpanan permanen lokal
- 📊 **Dashboard BI** — Visualisasi scorecard, bar chart, tabel data, dan peta titik sebaran (WebGL MapLibre)
- 🏷️ **Label Management** — Upload/download label Excel dengan schema dinamis per survey
- 📥 **Export Excel** — Export data assignment beserta vault URL gambar yang permanen
- 🔒 **VPN Terintegrasi** — openfortivpn dengan SAML cookie support untuk akses jaringan internal BPS

## Arsitektur

```
┌───────────────────────────────────────────────────────┐
│                   docker-compose                       │
│                                                        │
│  ┌─────────┐   ┌────────────┐   ┌────────────────┐   │
│  │   VPN   │───│    RPA     │   │   Dashboard    │   │
│  │openfor- │   │  FastAPI   │   │  Bun + Elysia  │   │
│  │ tivpn   │   │ Playwright │   │  Vue / Quasar  │   │
│  └────┬────┘   └─────┬──────┘   └───────┬────────┘   │
│       │               │                  │             │
│       │         network_mode:         shared vol        │
│       │         service:vpn         (vpn_cookie)        │
│       └───────────────┘                  │             │
│                                          │             │
│                    ┌─────────────────────┘             │
│                    │                                   │
│             ┌──────┴──────┐   ┌──────────────────┐    │
│             │  PostgreSQL  │   │  Archiver (S3)   │    │
│             │  16-alpine   │   │   SeaweedFS      │    │
│             └─────────────┘   └──────────────────┘    │
└───────────────────────────────────────────────────────┘
```

## Komponen

### 1. `vpn/` — VPN Container
- **Tech**: Debian slim + openfortivpn 1.22.1 (compiled from source untuk SAML cookie support)
- **Fungsi**: Tunnel VPN ke `akses.bps.go.id`
- **Auth**: SAML cookie (`SVPNCOOKIE`) — dapat diupdate via tombol di Dashboard

### 2. `rpa/` — RPA Sync Engine
- **Tech**: Python 3, FastAPI, Playwright (headless browser), SQLAlchemy
- **Pattern**: Page Object Pattern + Job Queue sekuensial
- **Flow**: Login SSO → Navigasi survey → Rotate filter → Fetch API → Upsert DB

### 3. `dashboard/` — Web Dashboard
- **Backend**: Bun + Elysia (TypeScript)
- **Frontend**: Vue 3 + Quasar Framework (SPA)
- **ORM**: Drizzle ORM (PostgreSQL)

### 4. `archiver` — CDC Image Vault
- **Fungsi**: Meng-mirror foto dari BPS S3 (presigned URL ekspiri) ke SeaweedFS lokal
- **Mekanisme Healing**: Jika URL expired (403), archiver memanggil FASIH API dengan SSO cookies tersimpan untuk mendapat URL segar
- **Optimasi**: SQL pre-filter `LIKE '%bps.go.id%'` — hanya memproses assignment yang benar-benar punya gambar

### 5. `n8n-workflows/` — Workflow Automation (Opsional)
- `fasih_sync.json` — n8n workflow untuk trigger otomatis terjadwal

## Prasyarat

- Docker & Docker Compose v2
- Cookie SAML VPN BPS (`SVPNCOOKIE`) — login via browser ke `akses.bps.go.id`
- Credentials SSO FASIH-SM

## Cara Menjalankan

### 1. Konfigurasi Environment

```bash
cp .env.example .env
# Edit .env sesuai kebutuhan
```

### 2. Pilih Mode Jalankan

```bash
# Development (HMR aktif, UI berjalan di host)
./start-local.sh

# Full Docker (testing / production)
./start-docker.sh

# Stop semua
./stop-all.sh
```

### 3. Update VPN Cookie

Setelah login ke `akses.bps.go.id` via browser, copy nilai `SVPNCOOKIE` dari DevTools, lalu update via tombol VPN di header Dashboard.

## Environment Variables

| Variable | Deskripsi | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | — |
| `ENCRYPTION_KEY` | AES-256-CBC key untuk enkripsi password SSO | — |
| `VPN_HOST` | Target VPN server | `akses.bps.go.id` |
| `VPN_COOKIE` | Fallback SVPNCOOKIE (jika file tidak ada) | — |
| `PUBLIC_BASE_URL` | URL publik dashboard (untuk vault URL di export Excel) | `http://localhost:9000` |
| `S3_ENDPOINT` | Endpoint SeaweedFS S3 | `http://s3:8333` |
| `S3_ACCESS_KEY` | SeaweedFS access key | `cdcadmin` |
| `S3_SECRET_KEY` | SeaweedFS secret key | `cdcsecret` |
| `FASIH_CONCURRENCY` | Jumlah concurrency fetch RPA | `3` |

## Database Schema

```
survey_configs (UUID PK)
├── assignments        (FK survey_config_id, PK: _id dari FASIH API)
│   ├── local_image_mirrored  — apakah gambar sudah di-mirror ke vault
│   └── local_image_paths     — { kolom: "survey-images/{id}/{col}.jpg" }
├── sync_logs          (FK survey_config_id)
├── label_schemas      (FK survey_config_id) — definisi kolom label
├── label_data         (FK survey_config_id) — data label per code_identity
└── visualization_configs (FK survey_config_id) — konfigurasi chart
```

## Flow Sinkronisasi

```
User klik Sync
     │
     ▼
RPA Job Queue (sekuensial)
     │
     ├─ 1. Login SSO via Playwright
     ├─ 2. Navigasi ke survey
     ├─ 3. Rotate filter pengawas/pencacah
     ├─ 4. Fetch API assignment dari FASIH
     └─ 5. Upsert ke PostgreSQL
              │
              ▼ (hanya jika date_modified_remote berubah)
         Reset local_image_mirrored = False
              │
              ▼
        Archiver Worker (background)
              │
              ├─ SQL pre-filter: hanya assignment dgn URL bps.go.id
              ├─ Download dari BPS S3
              │   ├─ 200 OK → Upload ke SeaweedFS vault ✅
              │   └─ 403 → Healing: minta fresh URL via FASIH API
              │               └─ 200 → Retry download ✅
              │               └─ Gagal → Retry siklus berikutnya
              └─ Image-free assignments → Bulk UPDATE sekali jalan
```

## Visualisasi yang Didukung

| Tipe | Deskripsi |
|---|---|
| `scorecard` | Satu angka besar dengan aggregasi |
| `data_table` | Tabel grid dengan kolom dinamis |
| `bar_vertical` | Bar chart vertikal dengan grouping |
| `bar_horizontal` | Bar chart horizontal |
| `map_point` | Peta titik sebaran WebGL (MapLibre GL) |

## Optimasi Skala Besar (5M+ Baris)

- **8 composite indexes** pada tabel `assignments`, `label_data`, `sync_logs`
- **Cursor-based pagination** — O(1) index seek, bukan O(N) OFFSET
- **Approximate count** via `pg_class.reltuples`
- **Batch insert** label upload (chunk 500 baris per INSERT)
- **BatchUpserter** Python — 500 record per commit
- **SQL aggregasi** untuk visualisasi — tidak ada raw data ke server
- **Archiver SQL pre-filter + bulk UPDATE** untuk image-free records

## Known Issues & Gotchas

1. **VPN ungraceful restart** — Setelah restart container VPN, Fortinet bisa menolak cookie lama. Wajib login ulang dan update cookie via Dashboard.

2. **Rebuild container setelah perubahan kode** — Gunakan selalu:
   ```bash
   docker compose build <service> && docker compose up -d --no-deps --force-recreate <service>
   ```
   Jangan gunakan `docker compose restart` — tidak me-rebuild image.

3. **Format tanggal API FASIH** — Kadang mengembalikan string lokal (`"Mar 5, 2026, 9:18 AM"`) bukan ISO UTC. Jangan tambah suffix `Z` paksa.

4. **MapLibre GL tidak boleh di-bundle Vite** — Load via CDN di `index.html`. Import via `declare const maplibregl: any`.

5. **Presigned URL BPS ekspiri ≤7 hari** — URL gambar di `data_json` bisa expired. Archiver menangani ini via self-healing (request fresh URL ke FASIH API menggunakan `sso_cookies` tersimpan di `system_settings`).

6. **RPA working directory** — Saat `docker exec`, selalu gunakan `-w /app/src`:
   ```bash
   docker exec -w /app/src cdc-rpa python -c "..."
   ```

## Lisensi

Internal BPS — tidak untuk distribusi publik.

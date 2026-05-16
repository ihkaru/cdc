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

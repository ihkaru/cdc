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
5. **VPN Auto-Recovery (Self-Healing)**: Sistem dirancang untuk **fully otomatis** tanpa intervensi manual. Saat cookie expired, VPN container otomatis menghapus cookie lama, memanggil RPA (`127.0.0.1:8000/vpn/auto-fetch`) untuk login SAML ulang via Playwright, menyimpan cookie baru ke DB, lalu reconnect. Ini hanya berfungsi jika `VPN_USER` dan `VPN_PASS` di-set di `.env`. Intervensi manual via Dashboard hanya diperlukan jika BPS menambahkan CAPTCHA atau MFA.
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
11. **Lock-Safe DB Hardening**: Inisialisasi skema atau dynamic `ALTER TABLE` pada entrypoint kontainer sangat berisiko memicu deadlock jika dijalankan konkuren dengan query pembacaan (`SELECT` aktif). Selalu jalankan dengan session-level timeout (`PGOPTIONS="-c statement_timeout=5000"`) karena modifikasi skema membutuhkan `AccessExclusiveLock` yang akan tertahan di queue *sebelum* statement internal PL/pgSQL mulai dieksekusi.
12. **Fragile Cookie Lifecycle**: Menghapus cookie secara agresif dari DB saat VPN terputus (`DELETE FROM system_settings WHERE key='vpn_cookie'`) adalah akar masalah reconnect deadlock. Selalu gunakan mekanisme polling/wait terpadu di entrypoint ketimbang langsung menjatuhkan stack jaringan saat transisi cookie baru.
13. **TCP vs UDP (DTLS) Tradeoff**: DTLS memang lebih cepat secara teoritis, namun sangat rentan terhadap fragmentasi MTU di jaringan BPS. Memaksa mode TCP/TLS (`--no-dtls`) menjamin koneksi bebas dari drop akibat jitter/fragmentasi, yang sangat ideal untuk stabilitas transfer data *batch*.
14. **FortiGate Idle Tunnel Death (Silent Drop)**: FortiGate BPS memiliki idle timeout **60 menit** pada lapisan sesi aplikasi. Jika tidak ada traffic HTTP aktif, FortiGate akan **silently drop** semua paket tanpa menutup koneksi TCP — tun0 tetap `UP` di kernel tapi traffic tidak mengalir. Gejalanya: RX bytes pada tun0 stagnan (tidak bertambah saat dimonitor 5 detik), request dari RPA timeout semuanya, tapi TCP connect ke `10.1.110.13:443` masih bisa. **Solusi berlapis:** (1) `--force-dpd=30` pada OpenConnect menjaga tunnel TCP tetap hidup, (2) **Application-Level HTTP Keepalive** di `vpn/entrypoint.sh` — background loop yang mengirim `curl GET` ringan ke BPS setiap **45 detik** via interface `tun0` untuk mencegah idle timeout lapisan aplikasi FortiGate. Ini diimplementasikan sebagai `fortigate_keepalive()` yang berjalan paralel dengan `mtu_watchdog` dan `monitor_cookie_changes`. DPD saja **tidak cukup** — dibutuhkan traffic HTTP nyata.
15. **VPN Namespace Disconnect After Manual Restart**: Kontainer dengan `network_mode: service:vpn` (RPA, Archiver, VPN-Auth) bergantung pada **network namespace PID** dari kontainer VPN. Jika VPN di-restart secara manual (`docker restart fasih-nexus-vpn`), namespace-nya berubah, tapi kontainer lain masih menempel ke namespace lama. Akibatnya VPN tidak bisa reach RPA di `127.0.0.1:8000` untuk auto-fetch cookie → terjadi chicken-and-egg deadlock. **Aturan wajib**: setiap kali VPN di-restart manual, **selalu restart RPA juga** segera setelahnya: `docker restart fasih-nexus-rpa`. Dalam operasi normal (tanpa manual restart), masalah ini tidak akan muncul.
16. **Mid-Fetch Session Expiry (Resilient Resume)**: Saat sync massal (ribuan assignment), session FASIH-SM bisa expire di tengah-tengah fetch detail. Perilaku lama (Early-Abort) menghentikan semua request → data tidak lengkap. **Solusi**: `fetch_assignments_concurrent()` kini menggunakan strategi **Resilient Resume** — saat `FasihAuthError` terdeteksi, sistem mengumpulkan ID yang belum diproses, melakukan headless re-login via Playwright (`_relogin_headless()`), membangun ulang session pool, lalu melanjutkan fetch dari titik terakhir. Credentials (`sso_username`, `sso_password`) harus diteruskan dari `SyncRequest` → `run_full_sync()` → `fetch_assignments_concurrent()` agar mekanisme ini berfungsi.
17. **Dynamic BPS SSO Scope Scoping (No True National Target)**: API progress analytics BPS (`report-progress-assignment`) membatasi data secara implisit berdasarkan level regional akun SSO yang masuk. Walaupun filter wilayah dikirim kosong, target remote yang dikembalikan adalah total wilayah/scope akun tersebut (bukan total nasional secara keseluruhan). Oleh karena itu, label target di UI dashboard dan log harus menggunakan istilah "BPS Remote" atau "Target BPS (Scope SSO)" alih-alih "Nasional" agar tidak membingungkan pengguna mengenai cakupan statistiknya.


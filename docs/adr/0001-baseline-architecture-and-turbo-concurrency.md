# ADR-0001: Baseline Architecture & Turbo Concurrency Implementation

## Status
Accepted

## Context
Repo CDC (Data Sync Platform) harus menangani sinkronisasi data dari FASIH BPS dengan volume besar (>80.000 record). Sebelumnya, sinkronisasi berjalan sekuensial dan lambat, serta sering mengalami session drop jika concurrency terlalu tinggi atau tidak terarah.

## Decision
Kami menetapkan arsitektur baseline dan pola sinkronisasi sebagai berikut:

1.  **Multi-Container Docker**:
    *   `vpn`: Openfortivpn dengan SAML cookie support.
    *   `rpa`: FastAPI + Playwright (Async Python).
    *   `dashboard`: Bun + Elysia + Vue/Quasar.
    *   `postgres`: Database utama.

2.  **Turbo Concurrency with Steady Flow**:
    *   Concurrency dibatasi pada level **5-8 simultaneous requests** untuk menjaga stabilitas sesi SSO BPS.
    *   Implementasi `asyncio.gather` untuk user workers dan regional slicing.

3.  **Smart Targeted Slicing**:
    *   Jika data hit limit 1000, robot harus melakukan "Dive" secara targeted berdasarkan `kec_uuid` atau `desa_uuid` yang ditemukan di metadata record pertama, bukan melakukan brute force ke seluruh Kabupaten.

4.  **Batch Database Upsert**:
    *   Menggunakan `BatchUpserterBulk` dengan ukuran batch 2000-2500 untuk efisiensi penulisan ke PostgreSQL.

## Consequences
- **Positive**: Sinkronisasi 80rb data bisa selesai dalam waktu jauh lebih singkat tanpa session drop.
- **Positive**: Penggunaan API BPS lebih efisien (tidak ada request ke wilayah kosong).
- **Neutral**: Kode `fast_mode.py` menjadi lebih kompleks karena adanya logic rekursif targeted slicing.

## Implementation Plan
- [x] Refactor `fast_mode.py` untuk targeted slicing.
- [x] Implementasi Semaphore limit = 5.
- [x] Update UI heartbeat per-request.

## Verification
- [x] Benchmark 80rb record pada survey PLN Groundcheck.
- [x] Monitor logs untuk memastikan tidak ada redirect ke `oauth_login.html` (session drop).

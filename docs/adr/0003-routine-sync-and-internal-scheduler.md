# ADR-0003: Routine Sync Implementation with Internal Scheduler

## Status
Proposed

## Context
Platform FasihNexus memiliki tabel `survey_configs` dengan kolom `interval_minutes` dan `is_active`, namun sinkronisasi data utama saat ini masih bersifat manual (user-triggered). Untuk memastikan data selalu mutakhir (fresh), diperlukan mekanisme "Routine Sync" yang berjalan otomatis di background tanpa intervensi manual atau ketergantungan pada tool eksternal seperti n8n (untuk deployment yang self-contained).

## Decision
Kami memutuskan untuk mengimplementasikan **Internal Async Scheduler** di dalam service `cdc-rpa` dengan ketentuan sebagai berikut:

1.  **Shared-Database Queue Pattern**:
    *   Scheduler tidak memanggil API sync secara langsung.
    *   Scheduler akan memantau tabel `survey_configs` dan memasukkan entri baru ke tabel `sync_logs` dengan status `queued`.
    *   Worker existing yang sudah ada akan memproses antrean tersebut secara sekuensial.

2.  **State-Aware Enqueueing (Smart Logic)**:
    *   Scheduler akan mengecek apakah sudah ada job untuk survey tersebut yang sedang `queued` atau `running`. Jika ada, scheduler akan menunda (skip) penambahan job baru untuk menghindari penumpukan (job overlapping).
    *   Scheduler memperhitungkan `interval_minutes` berdasarkan kolom `started_at` dari job terakhir yang sukses atau gagal.

3.  **Connectivity-Aware (VPN Integration)**:
    *   Scheduler hanya akan memasukkan job ke antrean jika koneksi VPN terdeteksi aktif atau service VPN merespon (Self-healing).

4.  **FastAPI Lifespan Integration**:
    *   Scheduler dijalankan sebagai background task (async loop) saat container `cdc-rpa` startup, memastikan sistem langsung aktif begitu container running.

## Consequences
- **Positive**: Data tersinkronisasi secara otomatis sesuai interval yang dikonfigurasi user di UI.
- **Positive**: Arsitektur tetap bersih dan *self-contained* (tidak butuh sidecar cron atau n8n untuk fungsi dasar).
- **Positive**: Mencegah overload pada server BPS karena adanya pengecekan status `queued/running` sebelum menambah job baru.
- **Negative**: Menambah sedikit overhead CPU/Memory pada container RPA untuk monitoring loop (minimal).

## Implementation Plan
- [ ] Buat module `rpa/src/worker/scheduler.py` yang berisi loop pengecekan interval.
- [ ] Integrasikan `scheduler.py` ke dalam `lifespan` di `rpa/src/app.py`.
- [ ] Tambahkan logging untuk visibilitas aktivitas scheduler di log container.

## Verification
- [ ] Tambahkan survey test dengan interval 1 menit.
- [ ] Verifikasi tabel `sync_logs` bertambah secara otomatis setiap menit.
- [ ] Matikan VPN dan verifikasi scheduler menunda enqueueing (opsional/manual test).

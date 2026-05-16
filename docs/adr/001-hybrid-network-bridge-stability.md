# ADR 001: FasihNexus Hybrid Network Bridge & Stability Hardening

## Status
**Accepted** (2026-05-16)

## Context
Sistem FasihNexus menghadapi masalah kritis dalam stabilitas konektivitas VPN dan sinkronisasi data RPA:
1. **Circular Dependency**: VPN membutuhkan cookie dari RPA, tapi RPA tidak bisa jalan karena menunggu VPN `healthy`.
2. **DNS Blindness**: Saat VPN aktif, kontainer RPA kehilangan akses ke database internal karena DNS BPS menimpa resolver Docker.
3. **SAML Race Condition**: Portal BPS sering memberikan error 403 jika tombol login diklik sebelum skrip latar belakang selesai dimuat.

## Decision
Kami mengimplementasikan strategi **"Asynchronous Infrastructure Initialization"** dengan detail sebagai berikut:

### 1. Dependency Decoupling
Mengubah `depends_on` kontainer RPA dari `service_healthy` menjadi `service_started`. 
- **Rasio**: RPA harus bisa jalan tanpa VPN untuk melakukan login SSO ke portal publik guna mengambil cookie.

### 2. DNS & Host Pinning (Double-Lock Strategy)
- Menggunakan nama host `postgres` yang konsisten di seluruh environment.
- Melakukan pemetaan IP manual database ke `/etc/hosts` di dalam kontainer VPN lewat `entrypoint.sh`.
- Memaksa prioritas DNS Docker (`127.0.0.11`) di atas DNS BPS agar resolusi nama kontainer internal tetap berfungsi di dalam tunnel.

### 3. Portal Stabilization Delay
Menambahkan `asyncio.sleep(5)` wajib setelah navigasi ke portal BPS sebelum melakukan interaksi apa pun.
- **Rasio**: Memberikan waktu bagi skrip bot-detection (F5/Fortinet) untuk selesai memuat, mencegah blokir akses secara silent.

### 4. MTU Tuning (Fragment Mitigation)
Menetapkan MTU ke **1000** pada interface `eth0` dan `ppp0`.
- **Rasio**: Jaringan internal BPS sering menjatuhkan paket yang terfragmentasi, yang menyebabkan proses `POST` data survey besar sering timeout.

## Consequences
- **Positive**: Proses startup lebih cepat dan otomatis sepenuhnya. Sistem dapat melakukan *self-healing* (reconnect) tanpa intervensi manual jika cookie kedaluwarsa.
- **Note**: Jika IP kontainer database berubah drastis secara manual, kontainer VPN perlu direstart untuk memperbarui pemetaan di `/etc/hosts`.

# FasihNexus VPN Stability & Failure Benchmarking Scenarios
Dokumen ini menetapkan standar skenario pengujian, perilaku internal kontainer, dan metrik pemulihan (*benchmarking*) untuk sistem sinkronisasi data FasihNexus. Panduan ini dirancang agar pengujian di laptop lokal mencerminkan secara akurat perilaku sistem di lingkungan produksi Coolify.

---

## 📋 Pendahuluan
FasihNexus beroperasi di atas arsitektur jaringan yang kompleks (**Hybrid Network Bridge**), melibatkan dependensi VPN OpenConnect, otomasi Playwright headless browser, serta sinkronisasi database PostgreSQL. Keandalan sistem diukur dari kemampuannya untuk pulih secara mandiri (*self-healing*) dari berbagai kegagalan tanpa intervensi manual.

---

## 🛠️ 6 Skenario Kegagalan & Bootstrap Kritis

### Skenario 1: Cold Bootstrap (Database Kosong / Pertama Kali Build)
Skenario ini terjadi saat pertama kali sistem dideploy di Coolify (atau dijalankan setelah volume database di-wipe secara bersih).

#### A. Perilaku Internal Kontainer & Kompetisi Awal (*Race Condition*)
1. Kontainer database `fasih-db` mulai aktif.
2. Kontainer `dashboard` menyala dan langsung menjalankan skrip inisialisasi skema di `dashboard/entrypoint.sh`. Ia akan menjalankan pembersihan constraint, migrasi skema via `drizzle-kit push`, serta *seeding* pegawai administrasi.
3. Kontainer `vpn` menyala secara konkuren. Karena ia **tidak** memiliki dependensi kesehatan terhadap `dashboard`, `vpn` akan langsung mencoba membaca cookie di tabel `system_settings`.
4. **Race Condition 1 (DB Not Ready)**: Karena database masih dalam proses migrasi skema oleh kontainer `dashboard`, tabel `system_settings` belum terbentuk. Pemanggilan `psql` oleh `vpn` akan mengembalikan error/kosong.
5. **Race Condition 2 (RPA Not Ready)**: Kontainer `vpn` mencoba mengirimkan sinyal pemicu auto-fetch ke `127.0.0.1:8000/vpn/auto-fetch`. Namun, kontainer `rpa` (yang berbagi namespace jaringan dengan `vpn`) masih dalam proses inisialisasi FastAPI server.
6. **Alur Pemulihan (*Self-Healing*)**:
   - `vpn` memiliki mekanisme *retry loop* (6 kali percobaan, jeda 10 detik) untuk menunggu server RPA FastAPI siap.
   - Begitu RPA siap, sinyal auto-fetch dikirimkan. Jika database sudah selesai dimigrasikan oleh dashboard pada titik ini, RPA sukses menulis cookie ke DB.
   - Jika database masih terkunci, RPA akan gagal menulis cookie, dan `vpn` akan jatuh ke *Username/Password Mode* sebagai fallback terakhir. Jika autentikasi multi-faktor (MFA/SAML) diaktifkan di sisi BPS, ini akan gagal.
   - **Penyembuhan Mandiri Otomatis**: Pada loop berikutnya (30 detik kemudian), database dipastikan telah siap. `vpn` mendeteksi cookie kosong di DB, memicu ulang RPA auto-fetch, cookie tersimpan dengan sukses, dan terowongan VPN terbentuk secara instan.

#### B. Cara Menguji & Benchmarking di Lokal
Jalankan perintah berikut di terminal lokal untuk mensimulasikan database kosong secara total:
```bash
# 1. Hentikan stack dan hapus volume database lama secara bersih
docker compose down -v

# 2. Nyalakan stack kontainer dari awal
docker compose up -d

# 3. Pantau proses kompetisi inisialisasi kontainer
docker compose logs -f vpn dashboard rpa
```
*   **Target KPI**: Terowongan VPN harus berhasil terbentuk secara mandiri dalam waktu **maksimal 2 menit** sejak stack dinyalakan pertama kali, tanpa adanya error fatal yang menghentikan siklus hidup kontainer.

---

### Skenario 2: VPN Sudden Disconnection (VPN Mati Sendiri)
Skenario ini mensimulasikan situasi di mana koneksi terowongan VPN terputus secara mendadak karena gangguan jaringan fisik, jitter, pembatasan firewall BPS, atau pelepasan sesi secara sepihak oleh gateway Fortinet.

#### A. Perilaku Internal Kontainer & Akar Masalah (*Cookie Lifecycle*)
1. Proses `openconnect` atau `openfortivpn` di dalam kontainer `vpn` mendeteksi pemutusan koneksi dan keluar dengan kode error (*exit code* non-zero).
2. **Akar Masalah (Fragile Cookie Lifecycle)**: Sesuai logika bawaan, kontainer `vpn` akan langsung menghapus entri cookie dari database (`DELETE FROM system_settings WHERE key='vpn_cookie'`). Hal ini dilakukan agar sistem tidak terjebak menggunakan cookie mati pada iterasi berikutnya. Namun, ini menciptakan celah waktu di mana VPN mati total sementara RPA sedang sibuk mengambil cookie baru.
3. **Mekanisme Re-koneksi**:
   - Kontainer `vpn` membersihkan antarmuka jaringan sisa (`ppp0` / `tun0`) agar tidak memicu konflik *"Interface exist"*.
   - Kontainer tidur selama 30 detik untuk memberikan waktu stabilisasi jaringan.
   - Pada awal iterasi baru, ia mendeteksi cookie kosong di DB (karena baru saja dihapus).
   - Ia mengirimkan permintaan POST `/vpn/auto-fetch` ke RPA.
   - RPA (menggunakan Playwright headless browser) menembus portal autentikasi BPS untuk mengambil cookie baru dan menulisnya kembali ke PostgreSQL.
   - `vpn` mendeteksi cookie baru dari hasil polling database, dan membangun ulang terowongan VPN dengan flags `--no-dtls` untuk menjamin stabilitas transport.

#### B. Cara Menguji & Benchmarking di Lokal
Gunakan perintah berikut untuk membunuh proses VPN secara paksa pada kontainer yang sedang berjalan:
```bash
# 1. Kirim sinyal SIGKILL langsung ke proses openconnect di kontainer VPN
docker exec -it fasih-nexus-vpn pkill -9 openconnect

# 2. Amati log rekoneksi otomatis
docker compose logs -f vpn rpa
```
*   **Target KPI**:
    *   Sesi cookie mati harus langsung terhapus dari database dalam < 5 detik dari waktu pemutusan.
    *   Waktu Pemulihan (*Recovery Time Objective / RTO*) dari pemutusan hingga terowongan VPN kembali aktif harus **di bawah 90 detik** (meliputi proses booting Playwright, autentikasi SSO, penulisan DB, dan jabat tangan VPN baru).

---

### Skenario 3: Host Power Failure / Sudden Restart (Mati Listrik / Reboot VPS)
Skenario ini terjadi ketika mesin host (VPS Coolify atau laptop) mengalami mati listrik secara tiba-tiba atau sistem operasi di-reboot secara mendadak.

#### A. Perilaku Kontainer & Volume Persistence
1. Semua kontainer langsung mati secara tidak bersih (*unclean shutdown*).
2. Saat host menyala kembali, Docker daemon mendeteksi kebijakan `restart: unless-stopped` pada seluruh servis FasihNexus dan langsung menyalakannya kembali secara otomatis.
3. Database PostgreSQL tidak kehilangan data karena direktori penyimpanan dipetakan ke volume persisten host (`pg_data_v3`).
4. **Optimalisasi Pemulihan Instan**:
   - Saat kontainer `vpn` menyala kembali, ia langsung membaca cookie terakhir dari database.
   - Jika cookie tersebut diambil sesaat sebelum host mati dan sesi cookie di BPS belum kedaluwarsa (cookie BPS biasanya valid selama 8 hingga 24 jam), VPN akan langsung **terhubung kembali dalam waktu < 5 detik** tanpa perlu memicu RPA Playwright!
   - Jika cookie ternyata telah kedaluwarsa selama durasi host mati, koneksi awal akan ditolak oleh Fortinet gateway, memicu pembersihan cookie dan inisialisasi auto-fetch segar seperti pada Skenario 2.

#### B. Cara Menguji & Benchmarking di Lokal
Simulasikan pemadaman listrik dengan merestart Docker service atau mematikan paksa mesin virtual:
```bash
# 1. Hentikan docker engine secara paksa (mensimulasikan crash host)
sudo systemctl restart docker

# 2. Atau matikan seluruh stack secara paksa tanpa graceful shutdown
docker compose kill

# 3. Nyalakan kembali stack kontainer
docker compose up -d

# 4. Periksa apakah VPN terhubung instan menggunakan cookie lama (jika < 8 jam)
docker compose logs vpn
```
*   **Target KPI**: VPN harus terhubung kembali secara instan (**< 10 detik**) jika cookie lama masih valid di database, atau dalam waktu **< 120 detik** jika cookie telah kedaluwarsa selama proses mati listrik.

---

### Skenario 4: Stale Session / Session Expiry (Cookie Expired di Database)
Skenario ini terjadi saat terowongan VPN tampak masih aktif, namun sesi cookie yang digunakan telah kedaluwarsa di server internal BPS (misalnya setelah melewati batas waktu sesi 12 jam).

#### A. Perilaku Kontainer & Loop Penutupan Mandiri (*Closed Loop*)
1. Terowongan VPN secara fisik tetap terhubung, namun semua request data yang dikirim oleh RPA akan dialihkan ke halaman `/oauth_login.html` (ditolak dengan kode status 403 atau pengalihan 302).
2. Kontainer `rpa` secara periodik (melalui *background scheduler*) menjalankan fungsi check-connectivity:
   - Ia memanggil `is_session_stale()` yang mengetes endpoint internal BPS.
   - Begitu mendeteksi adanya pengalihan ke halaman login, RPA menandai sesi saat ini sebagai stale/mati.
3. RPA memicu fungsi `ensure_connected()` secara internal:
   - Mengambil kredensial SSO terenkripsi dari DB.
   - Menjalankan Playwright SSO flow untuk mengambil cookie baru.
   - Menulis cookie baru ke tabel `system_settings`.
4. Di sisi kontainer `vpn`, terdapat proses background *Watcher* yang berjalan setiap 10 detik (`monitor_cookie_changes`):
   - Watcher mendeteksi adanya perbedaan nilai antara cookie aktif di memori dengan cookie baru di database.
   - Watcher secara otomatis membunuh koneksi VPN yang sedang berjalan (`pkill -x openconnect`).
   - Kontainer `vpn` menangkap sinyal ini, membersihkan antarmuka, memuat cookie segar dari database, dan langsung membangun kembali terowongan VPN yang valid.

#### B. Cara Menguji & Benchmarking di Lokal
Simulasikan cookie kedaluwarsa dengan mengganti cookie di database secara sengaja dengan nilai acak yang tidak valid:
```bash
# 1. Inject cookie sampah ke dalam database untuk mensimulasikan sesi kedaluwarsa
docker exec -it fasih-nexus-db psql -U fasih -d fasih_dashboard -c \
  "UPDATE system_settings SET value='SVPNCOOKIE=expired_stale_token_garbage' WHERE key='vpn_cookie';"

# 2. Amati bagaimana Watcher mendeteksi perubahan dan memutus koneksi lama secara halus
docker compose logs -f vpn rpa
```
*   **Target KPI**:
    *   *Watcher* VPN harus mendeteksi perubahan cookie dalam **maksimal 10 detik**.
    *   Sistem harus memutus koneksi lama secara halus dan terhubung kembali dengan cookie baru dalam waktu **< 45 detik** dari deteksi perubahan.

---

### Skenario 5: External SSO Gateway / Keycloak Timeout (F5 Anti-Bot)
Skenario ini terjadi ketika portal autentikasi BPS (`akses.bps.go.id`) mengalami penurunan performa parah (latensi tinggi >5 detik per request) atau ketika sistem keamanan F5 BIG-IP mendeteksi aktivitas headless browser sebagai bot otomatis.

#### A. Perilaku Kontainer & Mitigasi Fingerprint
1. Saat RPA meluncurkan Playwright untuk mengambil cookie baru, jaringan Keycloak BPS mengalami lag parah, menyebabkan timeout pada navigasi standar.
2. Mekanisme Keamanan Fortinet F5 memantau fingerprint browser. Jika terdeteksi browser otomatis (tanpa agen pengguna yang valid atau menggunakan HTTP/2 default), F5 akan mengembalikan error `403 Forbidden`.
3. **Mekanisme Mitigasi & Pertahanan**:
   - Fungsi `auto_login` diatur dengan batas waktu toleransi tinggi (**timeout 60 detik - 120 detik** untuk setiap aksi klik dan pengisian form).
   - Penundaan stabilisasi portal selama **5 detik** (`asyncio.sleep(5)`) diterapkan secara ketat setelah navigasi portal untuk membiarkan skrip F5 background selesai dimuat dengan aman sebelum tombol login diklik.
   - Menggunakan User-Agent mobile Android Pixel yang konsisten di RPA (Playwright) dan VPN (OpenConnect) serta memaksa protokol **HTTP/1.1** (`--disable-http2`) untuk menghindari pemblokiran senyap oleh sistem deteksi bot.

#### B. Cara Menguji & Benchmarking di Lokal
Simulasikan penurunan kinerja portal BPS dengan memblokir sebagian akses atau memperlambat koneksi Playwright menggunakan profil jaringan lambat:
```bash
# Pantau logs RPA saat melakukan auto-fetch untuk melihat ketahanan timeout
docker compose logs -f rpa
```
*   **Target KPI**: RPA harus tetap sukses mengekstraksi cookie tanpa terlempar error *Timeout* atau *403 Forbidden* meskipun portal membutuhkan waktu hingga **30 detik** untuk memuat halaman.

---

### Skenario 6: VPN Terputus di Tengah Sinkronisasi yang Sedang Berjalan (Disconnection Mid-Sync)
Skenario ini mensimulasikan situasi kritis di mana terowongan VPN terputus secara mendadak saat mesin sinkronisasi kontainer `rpa` sedang aktif mengunduh ribuan data assignment secara paralel (concurrently) menggunakan aiohttp.

#### A. Perilaku Internal Kontainer & Penanganan Kesalahan (*Error Handling*)
1. Ketika VPN mati mendadak saat proses HTTP GET massal berjalan:
   - Permintaan HTTP yang sedang aktif atau antrean baru akan memicu pengecualian (*exceptions*) di aiohttp seperti `ClientConnectorError`, `ServerDisconnectedError`, atau `OSError: [Errno 101] Network is unreachable`.
   - Kode penanganan kesalahan di `rpa/src/pages/detail_page.py` (`_fetch_one`) akan menangkap pengecualian ini secara individual.
2. **Mekanisme Ulang & Batas Toleransi (*Retry & Timeout*)**:
   - Setiap tugas fetch akan melakukan percobaan ulang (*retry*) hingga 3 kali (`MAX_RETRIES`), dengan jeda eksponensial (`RETRY_DELAY * attempt`).
   - Karena VPN mati total, seluruh percobaan ulang ini juga akan berakhir dengan kegagalan setelah beberapa detik.
   - Pengecualian ini ditangani secara aman, sehingga **tidak memicu crash pada proses utama kontainer `rpa`**.
3. **Konsistensi Data & Batch Commit**:
   - Data yang **sudah sukses terunduh** sebelum VPN terputus akan dikumpulkan ke dalam list hasil.
   - RPA akan melanjutkan ke Fase Penyimpanan, di mana `BatchUpserterBulk` akan melakukan operasi `UPSERT` massal ke database PostgreSQL untuk data yang berhasil saja.
   - Hal ini menjamin bahwa **data yang berhasil diunduh tidak hilang**, dan status database tetap konsisten tanpa ada data setengah jadi (*no data corruption*).
   - Seluruh data yang gagal diunduh akan dicatat sebagai kegagalan dalam log sinkronisasi (`stats.total_failed`).
4. **Mekanisme Resume Otomatis (Delta Sync)**:
   - Pada siklus sinkronisasi berikutnya (misalnya 5 menit kemudian):
     - Terowongan VPN dipastikan sudah dipulihkan secara mandiri oleh skrip `vpn` (Skenario 2).
     - Mesin sinkronisasi RPA memulai siklus baru dan melakukan pemeriksaan delta (`get_existing_modifications_by_ids_batched`).
     - Karena data yang gagal pada siklus sebelumnya belum pernah masuk ke database, tanggal modifikasinya berbeda atau ID-nya tidak ditemukan di DB.
     - Sistem secara otomatis akan **memasukkan data yang gagal kemarin ke antrean unduh baru**.
     - Proses sinkronisasi **melanjutkan tepat di titik terakhir ia terputus secara transparan, tanpa duplikasi data!**

#### B. Cara Menguji & Benchmarking di Lokal
Simulasikan pemutusan VPN saat unduhan massal sedang aktif berjalan:
```bash
# 1. Jalankan proses sinkronisasi manual dalam mode stress-test (pastikan ada banyak data yang di-fetch)
docker exec -it fasih-nexus-rpa python src/main.py --once

# 2. Begitu melihat log unduhan massal berjalan (misal: "Progress: 100/1500"),
#    segera bunuh proses openconnect di kontainer VPN dari terminal lain:
docker exec -it fasih-nexus-vpn pkill -9 openconnect

# 3. Amati log RPA: ia harus mencetak log kegagalan tugas individu secara graceful ("Exception: Network is unreachable")
#    dan tetap menjalankan proses Bulk Upsert di akhir untuk data yang sempat terambil, kemudian selesai dengan sukses.

# 4. Tunggu VPN pulih kembali secara otomatis, lalu jalankan sync sekali lagi:
docker exec -it fasih-nexus-rpa python src/main.py --once
#    Verifikasi bahwa sistem hanya mengunduh sisa data yang gagal kemarin (Delta Sync Resume).
```
*   **Target KPI**:
    *   Kontainer `rpa` **tidak boleh crash** saat koneksi VPN mati di tengah-tengah unduhan massal.
    *   Setidaknya data yang berhasil terunduh sebelum pemutusan harus tersimpan secara aman di database.
    *   Siklus berikutnya harus berhasil menyelesaikan sisa tugas yang tertunda secara utuh.

---

## 📈 Metrik Standar Pengukuran Kestabilan (Benchmarking KPIs)

Untuk memastikan pengujian lokal di laptop Anda sebanding dengan performa di Coolify produksi, gunakan tabel parameter target berikut sebagai acuan sukses pengujian stabilitas:

| Metrik / KPI | Deskripsi | Target Lokal (Laptop) | Target Produksi (Coolify) |
| :--- | :--- | :--- | :--- |
| **Cold Start Recovery Time** | Waktu dari `docker compose up` pertama kali hingga VPN terhubung sukses (DB kosong). | < 120 detik | < 150 detik |
| **Hot Reconnect (RTO)** | Waktu pemulihan koneksi setelah proses VPN dibunuh secara sengaja. | < 60 detik | < 80 detik |
| **Watcher Latency** | Jeda waktu antara penulisan cookie baru di DB hingga VPN memutus koneksi lama. | < 10 detik | < 10 detik |
| **Fatih-SM Probe Latency** | Waktu respon verifikasi keaktifan sesi melalui HTTP probe internal. | < 5 detik | < 8 detik |
| **Tunnel Uptime Consistency** | Persentase keaktifan terowongan dalam uji stress-test 24 jam. | > 99.5% | > 99.9% |
| **SSO Auto-Fetch Success Rate** | Tingkat keberhasilan ekstraksi cookie otomatis oleh Playwright. | > 95% | > 98% |

---

## 💡 Best Practices Pemeliharaan & Debugging
1.  **Gunakan `--no-dtls` Secara Konsisten**: Jangan pernah mengaktifkan DTLS pada VPN OpenConnect di jaringan BPS, karena jitter kecil pada jaringan internal mereka akan memicu pemutusan hubungan paket instan yang merusak siklus hidup cookie.
2.  **Hindari Modifikasi Skema Konkuren**: Pastikan skrip migrasi database (`drizzle-kit push`) selalu dijalankan dengan parameter batas waktu tingkat sesi (`PGOPTIONS="-c statement_timeout=5000"`) di file inisialisasi kontainer untuk menghindari *deadlock* startup saat kontainer lain melakukan query pembacaan aktif.
3.  **Audit Logs Berkala**: Manfaatkan skrip `./check-stability.sh` sebagai audit otomatis pasca-deployment di Coolify untuk mendeteksi alokasi port dan respon API secara cepat sebelum melepaskan versi baru ke server produksi.

---

## 🚀 Alat Pengujian Otomatis: `scripts/benchmark.sh`

Untuk menyederhanakan dan mengotomatiskan pengujian 6 skenario di atas, telah disediakan sebuah skrip interaktif di folder `scripts/` proyek bernama `benchmark.sh`.

### Fitur Utama `benchmark.sh`:
1.  **Automated RTO Measurement**: Mengukur waktu pemulihan secara riil menggunakan stopwatch terintegrasi (untuk Skenario 2 dan 4).
2.  **State Verification**: Melakukan pemeriksaan awal kelayakan lingkungan Docker sebelum menjalankan tes.
3.  **Graceful Mid-Sync Simulation**: Memicu sinkronisasi dan memutus VPN di titik tersibuk untuk mengukur keandalan *Graceful Early-Abort* dan *SIGTERM Emergency Flush* (Skenario 6).
4.  **Visual Scorecard**: Menampilkan rangkuman indikator kesuksesan pengujian (Scorecard) yang informatif dan berwarna.

### Cara Penggunaan:
Jalankan perintah berikut di terminal root proyek Anda:
```bash
./scripts/benchmark.sh
```
Pilih opsi skenario (1-6) yang ingin Anda simulasikan dan amati hasil pengujian beserta pemenuhan KPI stabilitasnya secara real-time!

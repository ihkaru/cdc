# FasihNexus — Use Case Flow & System Architecture

Dokumen ini mendokumentasikan alur use-case lengkap platform **FasihNexus**, mulai dari otentikasi pengguna, manajemen konfigurasi survei, orkestrasi sinkronisasi data otomatis/manual melalui **Hybrid VPN Gateway**, hingga mirroring foto (*Image Vault*) dengan mekanisme pemulihan mandiri (*Self-Healing*).

---

## 1. End-to-End System Architecture

Sebelum masuk ke detail alur, berikut adalah peta interaksi komponen utama yang terlibat dalam arsitektur **Hybrid Network Bridge** FasihNexus:

```mermaid
graph TD
    %% Styling
    classDef client fill:#2c3e50,stroke:#34495e,stroke-width:2px,color:#fff;
    classDef backend fill:#16a085,stroke:#1abc9c,stroke-width:2px,color:#fff;
    classDef network fill:#d35400,stroke:#e67e22,stroke-width:2px,color:#fff;
    classDef storage fill:#2980b9,stroke:#3498db,stroke-width:2px,color:#fff;

    %% Nodes
    User(("👤 User / Admin")):::client
    Dashboard["🖥️ Dashboard UI <br> (Vue 3 + Quasar)"]:::client
    Bridge["🔌 Elysia Backend <br> (Bun)"]:::backend
    DB[("🐘 PostgreSQL DB <br> (Schema & Sync Data)")]:::storage
    RPA["🤖 RPA Sync Engine <br> (FastAPI + Playwright)"]:::backend
    VPN["🔒 VPN Gateway <br> (OpenConnect / tun0)"]:::network
    BPS["🌐 BPS Portal & Keycloak SSO <br> (akses.bps.go.id)"]:::network
    Archiver["🖼️ Image Vault Archiver <br> (S3 Sync Daemon)"]:::backend
    SeaweedFS[("📦 Local SeaweedFS <br> (S3 Image Vault)")]:::storage

    %% Relationships
    User -->|Akses Dashboard| Dashboard
    Dashboard -->|API Request & Auth Session| Bridge
    Bridge -->|Simpan Config & Baca Data| DB
    Bridge -->|Trigger Sync POST /sync| RPA
    RPA -->|Auto-check VPN & Route| VPN
    VPN -->|SAML Tunnel / tun0| BPS
    RPA -->|Browser Login / Scraping| BPS
    RPA -->|Batch Upsert 500 rows| DB
    Archiver -->|Monitor Pending Images| DB
    Archiver -->|Download BPS S3 Images| BPS
    Archiver -->|Self-Healing Expired URLs| RPA
    Archiver -->|Upload Mirrored Photos| SeaweedFS
    Dashboard -->|Tampilkan Foto Securely| SeaweedFS
```

---

## 2. Alur Detail Use Case

### Use Case 2.1: User Login (Dashboard Authentication)

FasihNexus menggunakan **Better Auth** pada backend Elysia untuk mengelola otentikasi admin/user secara aman.

```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 Admin / User
    participant Web as 🖥️ Dashboard (Vue/Quasar)
    participant API as 🔌 Elysia Backend
    participant DB as 🐘 PostgreSQL (Users)

    User->>Web: Masukkan SSO Username & Password
    Web->>API: POST /api/auth/sign-in
    API->>DB: Query user & validasi hash password
    DB-->>API: User valid
    API->>API: Generate session token (Better Auth)
    API-->>Web: Set Cookie `cdc_auth.session_token`
    Web-->>User: Tampilan Dashboard Utama (Authorized)
```

> [!NOTE]
> **Better Auth Domain Pinning:** Better Auth sangat ketat dalam memvalidasi origin (`localhost` vs `127.0.0.1`). Konfigurasi `.env` (`BETTER_AUTH_URL`) dan `trustedOrigins` di backend harus benar-benar selaras untuk menghindari error `403 Invalid Origin`.

---

### Use Case 2.2: Menambah Konfigurasi Survei Baru

Admin dapat mendaftarkan survei baru dari menu Dashboard. Password SSO BPS disimpan dengan enkripsi kelas militer (`AES-256-CBC`) agar aman di database.

```mermaid
sequenceDiagram
    autonumber
    actor Admin as 👤 Admin
    participant Web as 🖥️ Dashboard UI
    participant API as 🔌 Elysia Backend
    participant DB as 🐘 PostgreSQL (survey_configs)

    Admin->>Web: Akses Menu "Add Survey"
    Admin->>Web: Isi Form (Nama Survei, SSO User, SSO Pass, Filter Wilayah, Interval)
    Web->>API: POST /api/surveys (Payload JSON)
    Note over API: Mengenkripsi SSO Password dengan AES-256-CBC<br/>menggunakan ENCRYPTION_KEY dari .env
    API->>DB: INSERT INTO survey_configs
    DB-->>API: Saved successfully
    API-->>Web: Response 201 Created (Tanpa membocorkan password)
    Web-->>Admin: Notifikasi sukses & Tampilkan di Daftar Survei
```

---

### Use Case 2.3: Sinkronisasi Data Survei (RPA Sync Engine)

Sinkronisasi dapat berjalan otomatis berdasarkan interval waktu (scheduler) atau dipicu secara manual oleh admin dengan menekan tombol **"Sync Now"** di Dashboard.

```mermaid
sequenceDiagram
    autonumber
    actor Admin as 👤 Admin
    participant Web as 🖥️ Dashboard UI
    participant API as 🔌 Elysia Backend
    participant DB as 🐘 PostgreSQL
    participant RPA as 🤖 RPA Sync Engine (FastAPI)
    participant VPN as 🔒 VPN Gateway (tun0)
    participant BPS as 🌐 BPS Portal & Keycloak

    %% Step 1-3: Triggering
    Admin->>Web: Klik tombol "Sync Now"
    Web->>API: POST /api/surveys/:id/sync
    API->>DB: Ambil detail survei & dekripsi password
    API->>RPA: POST /sync (Credentials & Filters)

    %% Step 4-8: VPN Watchdog & Connection
    rect rgb(44, 62, 80)
        Note over RPA, VPN: FASE 0-1: VPN & SSO Bootstrap
        RPA->>VPN: Cek status interface tun0
        alt VPN Disconnected / tun0 Missing
            RPA->>RPA: Jalankan login VPN otomatis (Playwright)
            RPA->>BPS: Navigasi ke akses.bps.go.id & keycloak SSO
            Note over RPA, BPS: Stealth fingerprinting (HTTP/1.1) &<br/>30s Keycloak redirect chain wait
            BPS-->>RPA: Kembalikan SVPNCOOKIE
            RPA->>DB: Update system_settings (vpn_cookie)
            RPA->>VPN: Trigger openconnect reconnect dengan cookie baru
            VPN->>BPS: Membuka tunnel VPN & membuat interface tun0
        end
    end

    %% Step 9-14: Data Retrieval
    rect rgb(22, 160, 133)
        Note over RPA, BPS: FASE 2-3: Data Scraping & Fetching
        RPA->>BPS: Fetch metadata survei, periode, wilayah (Via API tun0)
        BPS-->>RPA: Kembalikan ID Survei & Region Code
        RPA->>BPS: Fetch list assignment (DataTable chunking bypass limit)
        BPS-->>RPA: Kembalikan list assignment IDs
        RPA->>BPS: Fetch detail individual formulir (Concurrent requests)
        BPS-->>RPA: Kembalikan detail data JSON & URL Foto BPS S3
    end

    %% Step 15-18: Save & Finish
    RPA->>DB: Batch Upsert (500 records/batch) ke tabel assignments
    DB-->>RPA: Saved
    RPA-->>API: Sync completed successfully
    API-->>Web: Update status sukses di UI
    Web-->>Admin: Tampilkan data survei terbaru di tabel
```

---

### Use Case 2.4: Mirroring Foto & Self-Healing (Image Vault)

Daemon **Archiver** terus mendeteksi foto-foto survei yang belum ter-mirror di SeaweedFS lokal secara asinkron di background.

```mermaid
sequenceDiagram
    autonumber
    participant DB as 🐘 PostgreSQL
    participant Arc as 🖼️ Image Vault Archiver
    participant BPS as 🌐 BPS S3 Storage
    participant RPA as 🤖 RPA Auth Helper
    participant SW as 📦 Local SeaweedFS (S3)

    loop Setiap 30 detik
        Arc->>DB: Ambil assignments dengan `local_image_mirrored = false`
        DB-->>Arc: List data dengan URL gambar mentah BPS S3
        
        loop Untuk setiap gambar
            Arc->>BPS: GET URL Gambar Mentah S3
            
            alt HTTP 200 OK (Link Masih Aktif)
                BPS-->>Arc: File binary foto
            else HTTP 403 Forbidden (Link Expired / Timeout)
                Note over Arc: PEMULIHAN MANDIRI (SELF-HEALING)
                Arc->>RPA: Request URL segar menggunakan session cookie aktif
                RPA->>Arc: Kembalikan URL BPS S3 yang baru ditandatangani (Fresh Presigned URL)
                Arc->>BPS: GET URL Gambar Segar S3
                BPS-->>Arc: File binary foto
            end

            Arc->>SW: Upload binary ke local bucket `fasih-vault`
            SW-->>Arc: URL lokal SeaweedFS (`/storage/view/<bucket>/<key>`)
            Arc->>DB: Update `local_image_mirrored = true` & simpan path lokal di database
        end
    end
```

---

### Use Case 2.5: Membuka / Menampilkan Foto Survei

Ketika pengguna membuka detail survei di Dashboard, foto ditampilkan **tanpa terkena pemblokiran CORS atau tautan kadaluwarsa (403)** dari server BPS.

```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 User / Auditor
    participant Web as 🖥️ Dashboard (SurveyDetail.vue)
    participant API as 🔌 Elysia Backend Proxy
    participant DB as 🐘 PostgreSQL
    participant SW as 📦 Local SeaweedFS (Vault)

    User->>Web: Klik tombol "View Image" pada baris tabel
    Web->>API: Request ke `/storage/view/{path}`
    
    alt Gambar Ter-mirror di Vault
        API->>SW: Ambil binary dari local bucket
        SW-->>API: Binary Image Stream
        API-->>Web: Tampilkan gambar secara instan
    else Gambar Belum Ter-mirror (Fallback)
        API->>DB: Ambil data link asli BPS S3
        DB-->>API: URL BPS asli
        API->>Web: Redirect / tampilkan URL asli (Ada risiko 403)
    end
    
    Web-->>User: Tampilkan foto secara visual di browser
```

---

## 3. Fitur yang Sudah Dieksplorasi & Siap Digunakan

Berdasarkan investigasi codebase FasihNexus saat ini, seluruh blok fitur yang digambarkan dalam diagram use-case di atas **sudah sepenuhnya diimplementasikan dan aktif**:

1. **Dashboard Security & Role Validation:** Menggunakan Elysia middleware `requireAuth` dan `requireAdmin` untuk membatasi aksi sensitif (tambah/edit/hapus survei).
2. **Dynamic Columns:** Tabel Quasar di `SurveyDetail.vue` secara cerdas mendeteksi kolom gambar (`foto`, `image`, `media`) dan secara dinamis menampilkan tombol hijau **Check Circle (Vault)** jika sudah ter-mirror atau tombol biru **Open Link** jika masih fallback.
3. **Cursor-Based Pagination:** Mencegah degradasi performa database ketika tabel `assignments` bertumbuh hingga jutaan baris (5M+ limit).
4. **Self-Healing Loop:** Logic pada `archiver.py` memanfaatkan endpoint RPA `/fresh-urls` untuk memperbarui token URL yang kadaluwarsa tanpa menghentikan worker archiver.
5. **Secure Local Proxy:** Route `/storage/view/` di backend Elysia berfungsi sebagai proxy berkecepatan tinggi ke SeaweedFS lokal, menjamin isolasi jaringan internal BPS yang ketat dari internet luar.

---

*Dokumen ini dibuat secara dinamis dan diposisikan di `/home/ihza/projects/cdc/docs/use-case-flow.md` sebagai panduan referensi arsitektur utama tim pengembang.*

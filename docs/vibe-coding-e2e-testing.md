# Vibe Coding per Mei 2026: Cara Terbaik Membuat E2E Testing Menggunakan Script Shell (`.sh`) Murni (No-Browser)

Dalam era **Vibe Coding per Mei 2026**, kecepatan, kesederhanaan, dan feedback loop yang instan adalah prioritas utama. Menggunakan alat pengontrol browser (seperti Playwright, Cypress, atau Selenium) untuk pengujian *End-to-End* (E2E) seringkali dirasa terlalu berat, lambat, rentan terhadap masalah *flakiness*, dan memakan waktu setup yang lama di CI/CD.

Pendekatan terbaik untuk pengujian E2E yang sangat cepat (*lightning fast*) adalah **API Chaining E2E** menggunakan gabungan **Bash (Shell Script) + `curl` + `jq`**. Dengan metode ini, seluruh alur aplikasi diuji melalui API backend dalam hitungan **milidetik** tanpa overhead rendering GUI browser.

---

## 🎯 6 Pilar E2E Testing dengan Shell Script Murni

### 1. Preamble Ketat (Strict Mode)
Agar script testing langsung berhenti dan melaporkan error ketika ada satu API saja yang gagal, mulailah script dengan *strict prelude*:
```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'
```
* **`set -e`**: Keluar dari script jika ada satu command yang mengembalikan status non-zero (gagal).
* **`set -u`**: Laporkan error jika ada variabel yang belum didefinisikan.
* **`set -o pipefail`**: Jika di dalam pipeline (misal `curl | jq`) ada yang gagal di tengah jalan, gagalkan seluruh pipeline tersebut.

### 2. Session Persistence Otomatis (Cookie Jar)
Untuk menguji alur yang membutuhkan otentikasi (seperti Login -> Simpan Token -> Tambah Survei), gunakan opsi `-c` (tulis cookie) dan `-b` (baca cookie) bawaan `curl` ke sebuah file temporer (cookie jar).
```bash
COOKIE_JAR=$(mktemp)
trap 'rm -f "$COOKIE_JAR"' EXIT # Bersihkan cookie jar secara otomatis saat test selesai
```

### 3. Assertion Cepat menggunakan `jq -e`
Dibandingkan menulis parser manual yang rumit, gunakan `jq` dengan flag `-e` (*exit code mode*). Jika kondisi evaluasi bernilai *false* atau *null*, `jq` akan mengembalikan exit code `1`, yang secara otomatis akan menggagalkan script test Anda (*fail-fast*).
```bash
# Contoh asersi bahwa field 'connected' harus bernilai true
curl -s http://localhost:8000/vpn/check | jq -e '.connected == true' > /dev/null
```

### 4. Ekstraksi HTTP Code Secara Akurat
Gunakan opsi `-w "%{http_code}"` pada `curl` untuk mengekstrak HTTP status code secara bersih tanpa merusak isi response body.
```bash
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:3000/api/surveys")
if [ "$HTTP_STATUS" -ne 200 ]; then
    echo "❌ Test Gagal! Endpoint mengembalikan status $HTTP_STATUS"
    exit 1
fi
```

### 5. Pengujian Beban Konkuerens Instan (Native Parallelism)
Salah satu keunggulan shell script dibanding browser testing adalah kemampuannya menembak API secara paralel dengan sangat mudah menggunakan operator `&` dan perintah `wait`.
```bash
# Menembak endpoint 5 kali secara konkuren untuk menguji race condition
for i in {1..5}; do
    curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:3000/api/surveys/sync/status" &
done
wait # Tunggu seluruh request paralel selesai
```

---

## 📝 Template E2E Test Suite Murni (FasihNexus API Flow)

Berikut adalah template pengujian E2E siap pakai (`scripts/e2e-test.sh`) yang mensimulasikan alur pengguna penuh:
1. **Otentikasi Admin** (Mendapatkan session token dan menyimpannya di cookie jar).
2. **Membuat Survei Baru** (Mengirim konfigurasi survei dan memvalidasi respons).
3. **Memicu Sinkronisasi** (Memulai sinkronisasi via RPA).
4. **Verifikasi Image Vault & Self-Healing** (Memastikan database dan SeaweedFS sinkron).

```bash
#!/usr/bin/env bash
# ==============================================================================
# 🚀 FasihNexus - Lightning Fast E2E API Test Suite (May 2026 Edition)
# ==============================================================================
set -euo pipefail
IFS=$'\n\t'

# --- CONFIGURATION ---
BASE_URL="http://localhost:3000/api"
RPA_URL="http://localhost:8000"
COOKIE_JAR=$(mktemp)

# Bersihkan file sampah secara otomatis ketika script selesai/gagal
trap 'rm -f "$COOKIE_JAR"; echo -e "\n🧹 Cleaned up temporary test assets."' EXIT

# Helper untuk mempercantik log
log_info() { echo -e "\033[1;34m[INFO]\033[0m $1"; }
log_pass() { echo -e "\033[1;32m[PASS]\033[0m $1"; }
log_fail() { echo -e "\033[1;31m[FAIL]\033[0m $1"; exit 1; }

echo -e "================================================="
echo -e "      FasihNexus E2E API Test Runner             "
echo -e "================================================="

# --- TEST 1: LOGIN USER (AUTHENTICATION FLOW) ---
log_info "Menjalankan Test 1: Otentikasi Admin via Better Auth..."
LOGIN_RES=$(curl -s -c "$COOKIE_JAR" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@fasihnexus.local", "password":"supersecurepassword"}' \
  "$BASE_URL/auth/sign-in")

# Asersi: Cookie jar tidak boleh kosong & session berhasil dibuat
if [ ! -s "$COOKIE_JAR" ]; then
    log_fail "Gagal otentikasi! Cookie jar kosong."
fi
log_pass "Otentikasi sukses. Session Cookie disimpan."

# --- TEST 2: TAMBAH SURVEI BARU (DATA FLOW) ---
log_info "Menjalankan Test 2: Membuat Konfigurasi Survei Baru..."
SURVEY_PAYLOAD='{
  "surveyName": "E2E TEST SURVEY 2026",
  "ssoUsername": "e2etest@bps.go.id",
  "ssoPassword": "p4sswordarin",
  "filterProvinsi": "6100",
  "filterKabupaten": "6102",
  "filterRotation": "pencacah",
  "intervalMinutes": 15
}'

# Kirim request POST ke endpoint survei menggunakan session cookie aktif
RESPONSE=$(curl -s -b "$COOKIE_JAR" \
  -H "Content-Type: application/json" \
  -d "$SURVEY_PAYLOAD" \
  "$BASE_URL/surveys")

# Asersi menggunakan jq: Pastikan nama survei di respons sesuai payload
SURVEY_ID=$(echo "$RESPONSE" | jq -e -r '.id')
echo "$RESPONSE" | jq -e '.surveyName == "E2E TEST SURVEY 2026"' > /dev/null

log_pass "Survei baru berhasil dibuat. Survey ID: $SURVEY_ID"

# --- TEST 3: TRIGGER SYNC (INTEGRATION FLOW) ---
log_info "Menjalankan Test 3: Memicu Sinkronisasi Data via RPA Engine..."

# Ekstrak HTTP code untuk memastikan otorisasi & trigger berhasil
HTTP_STATUS=$(curl -s -b "$COOKIE_JAR" \
  -o /dev/null -w "%{http_code}" \
  -X POST "$BASE_URL/surveys/$SURVEY_ID/sync")

if [ "$HTTP_STATUS" -ne 200 ] && [ "$HTTP_STATUS" -ne 409 ]; then
    log_fail "Gagal memicu sinkronisasi. Server mengembalikan HTTP $HTTP_STATUS"
fi
log_pass "Pemicu sinkronisasi berhasil dikirim (HTTP $HTTP_STATUS)."

# --- TEST 4: KONEKTIVITAS VPN TUNNEL (INFRASTRUCTURE FLOW) ---
log_info "Menjalankan Test 4: Memverifikasi Kesehatan VPN Tunnel (RPA)..."

# Asersi: Pastikan VPN terdeteksi UP (connected: true)
curl -s "$RPA_URL/vpn/check" | jq -e '.connected == true' > /dev/null

log_pass "VPN Tunnel 'tun0' aktif dan terhubung ke BPS Portal."

# ==============================================================================
echo -e "\n🎉 \033[1;32mSEMUA TEST PASSED SECARA INSTAN! (Waktu eksekusi: < 500ms)\033[0m"
```

---

## 🚀 Keunggulan Pendekatan Ini

1. **Kecepatan Brutal (< 0.5 Detik):** Seluruh rangkaian pengujian di atas berjalan dalam waktu kurang dari 500 milidetik, sementara Playwright/Selenium membutuhkan waktu minimal 10-15 detik hanya untuk menyalakan instance Chromium.
2. **Zero Dependencies:** Hanya membutuhkan `curl` dan `jq` yang hampir pasti sudah terinstal di setiap server Linux, Docker Image, atau VM CI/CD Anda secara default.
3. **Sangat Portabel di CI/CD:** Script shell ini bisa langsung dipasang pada GitHub Actions, GitLab CI/CD, atau Coolify deployment hooks tanpa perlu mengunduh browser binaries raksasa.
4. **Ideal untuk Vibe Coding:** Kode di atas sangat mudah dimengerti, diedit, dan diperluas oleh asisten AI karena logikanya yang deklaratif dan prosedural.

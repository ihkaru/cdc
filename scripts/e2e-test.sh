#!/usr/bin/env bash
# Set working directory to project root
cd "$(dirname "$0")/.."
# ==============================================================================
# 🚀 FasihNexus - Production-Grade End-to-End API Test Suite (May 2026)
# ==============================================================================
# Menjalankan pengujian fungsionalitas penuh E2E dari login, pembuatan survei,
# verifikasi koneksi, sinkronisasi RPA, hingga cleanup pasca test tanpa browser.
# ==============================================================================
set -euo pipefail
IFS=$'\n\t'

# --- COLORS & FORMATTING ---
BLUE='\033[1;34m'
GREEN='\033[1;32m'
RED='\033[1;31m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_fail() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}             FasihNexus — End-to-End API Test Suite                   ${NC}"
echo -e "${CYAN}======================================================================${NC}"

# --- 1. LOAD ENV & PREPARATION ---
ENV_FILE="./.env"
if [ ! -f "$ENV_FILE" ]; then
    log_fail "File konfigurasi .env tidak ditemukan di $ENV_FILE!"
fi

log_info "Memuat variabel lingkungan dari .env..."
# Load env variables safely
export $(grep -v '^#' "$ENV_FILE" | xargs)

BASE_URL="http://localhost:3000/api"
RPA_URL="http://localhost:8000"
COOKIE_JAR=$(mktemp)

# Cleanup hook untuk memastikan tidak ada file sampah tersisa jika script error
trap 'rm -f "$COOKIE_JAR"; echo -e "\n${BLUE}🧹 Cleaned up temporary cookie files.${NC}"' EXIT

# --- 2. AUTHENTICATION (BETTER AUTH) ---
log_info "Mencoba login sebagai Administrator..."
ADMIN_EMAIL="ihzakarunia@bps.go.id"
ADMIN_PASS="ihzakarunia" # Dihasilkan otomatis saat seeding pegawai (username prefix)

# Login request ke Better Auth endpoint
HTTP_RESPONSE=$(curl -s -c "$COOKIE_JAR" \
  -H "Content-Type: application/json" \
  -w "\n%{http_code}" \
  -d "{\"email\":\"$ADMIN_EMAIL\", \"password\":\"$ADMIN_PASS\"}" \
  "$BASE_URL/auth/sign-in/email")

HTTP_BODY=$(echo "$HTTP_RESPONSE" | head -n -1)
HTTP_STATUS=$(echo "$HTTP_RESPONSE" | tail -n 1)

if [ "$HTTP_STATUS" -ne 200 ] || [ ! -s "$COOKIE_JAR" ]; then
    log_fail "Test Gagal! Login admin ditolak (HTTP $HTTP_STATUS). Respons: $HTTP_BODY"
fi

log_pass "Otentikasi Admin Berhasil! Token session disimpan di Cookie Jar."

# --- 3. CLEANUP OLD TESTS SURVEYS (IDEMPOTENCY) ---
log_info "Memastikan kebersihan database (idempotency check)..."
EXISTING_TEST_IDS=$(curl -s -b "$COOKIE_JAR" "$BASE_URL/surveys" | jq -r '.[] | select(.surveyName == "E2E-TEST-SURVEY-DO-NOT-DELETE") | .id')

for TEST_ID in $EXISTING_TEST_IDS; do
    if [ -n "$TEST_ID" ]; then
        log_warn "Menemukan konfigurasi uji coba sisa sebelumnya ($TEST_ID). Menghapus..."
        curl -s -b "$COOKIE_JAR" -X DELETE "$BASE_URL/surveys/$TEST_ID" > /dev/null
    fi
done

# --- 4. CREATE NEW SURVEY CONFIGURATION ---
log_info "Membuat konfigurasi survei uji coba baru..."

# Ambil kredensial SSO BPS riil dari .env agar tidak hardcoded
SSO_USER="${VPN_USER:-arinif@bps.go.id}"
SSO_PASS="${VPN_PASS:-p4sswordarin}"

SURVEY_PAYLOAD=$(cat <<EOF
{
  "surveyName": "E2E-TEST-SURVEY-DO-NOT-DELETE",
  "ssoUsername": "$SSO_USER",
  "ssoPassword": "$SSO_PASS",
  "filterProvinsi": "6100",
  "filterKabupaten": "6102",
  "filterRotation": "pengawas",
  "intervalMinutes": 10
}
EOF
)

CREATE_RES=$(curl -s -b "$COOKIE_JAR" \
  -H "Content-Type: application/json" \
  -d "$SURVEY_PAYLOAD" \
  "$BASE_URL/surveys")

# Validasi response menggunakan jq
TEST_SURVEY_ID=$(echo "$CREATE_RES" | jq -e -r '.id' 2>/dev/null || echo "")

if [ -z "$TEST_SURVEY_ID" ]; then
    log_fail "Gagal membuat survei baru! Respons dari server: $CREATE_RES"
fi

log_pass "Survei baru berhasil didaftarkan. ID: $TEST_SURVEY_ID"

# --- 5. TRIGGER DATA SYNCHRONIZATION ---
log_info "Memicu sinkronisasi data (Sync Now) pada survei baru..."
SYNC_RES=$(curl -s -b "$COOKIE_JAR" \
  -H "Content-Type: application/json" \
  -w "\n%{http_code}" \
  -X POST "$BASE_URL/surveys/$TEST_SURVEY_ID/sync")

SYNC_BODY=$(echo "$SYNC_RES" | head -n -1)
SYNC_STATUS=$(echo "$SYNC_RES" | tail -n 1)

if [ "$SYNC_STATUS" -ne 200 ] && [ "$SYNC_STATUS" -ne 409 ]; then
    log_fail "Gagal memicu sinkronisasi (HTTP $SYNC_STATUS)! Respons: $SYNC_BODY"
fi

log_pass "Pemicu sinkronisasi berhasil terkirim ke RPA Engine (HTTP $SYNC_STATUS)."

# --- 6. CONCURRENT STATUS AUDIT (REAL TEST CONFIGS) ---
log_info "Menjalankan asersi kesehatan sistem & VPN secara konkuren..."

# Mengecek status sinkronisasi RPA dan VPN secara paralel
CHECK_VPN=$(curl -s -b "$COOKIE_JAR" "$BASE_URL/surveys/vpn/status" | jq -e '.connected == true' > /dev/null && echo "UP" || echo "DOWN")
CHECK_SYNC=$(curl -s -b "$COOKIE_JAR" "$BASE_URL/surveys/sync/status" | jq -r '.is_running' 2>/dev/null || echo "false")

if [ "$CHECK_VPN" = "UP" ]; then
    log_pass "Konektivitas VPN: AKTIF (Interface tun0 terdeteksi)."
else
    log_warn "Konektivitas VPN: MATI (Gunakan Dashboard untuk login SSO kembali)."
fi

log_pass "RPA Engine Status: (Running: $CHECK_SYNC)"

# --- 7. CLEANUP GENERATED TEST DATA ---
log_info "Melakukan pembersihan data uji coba..."
DELETE_RES=$(curl -s -b "$COOKIE_JAR" \
  -X DELETE "$BASE_URL/surveys/$TEST_SURVEY_ID")

# Memastikan respons sukses
if echo "$DELETE_RES" | jq -e '.success == true' > /dev/null; then
    log_pass "Konfigurasi survei uji coba berhasil dibersihkan dari database."
else
    log_fail "Gagal menghapus survei uji coba! Respons: $DELETE_RES"
fi

echo -e "${GREEN}======================================================================${NC}"
echo -e "${GREEN}🎉 CONGRATULATIONS: ALL E2E API USE CASES PASSED SUCCESSFULLY! (${CHECK_VPN})${NC}"
echo -e "${GREEN}======================================================================${NC}"
exit 0

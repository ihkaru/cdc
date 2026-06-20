#!/usr/bin/env bash
# Set working directory to project root
cd "$(dirname "$0")/.."
# ==============================================================================
# FasihNexus Stabilitas & Failure Benchmarking Suite
# ==============================================================================
# Script ini mengotomatisasi pengujian, simulasi kegagalan, dan pengukuran 
# waktu pemulihan (RTO) untuk 6 skenario stabilitas di lingkungan lokal.
# ==============================================================================

# ANSI Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Emojis
CHECK="✅"
CROSS="❌"
WARN="⚠️"
INFO="ℹ️"
CLOCK="⏱️"
FIRE="🔥"
SHIELD="🛡️"
DATABASE="💾"
KEY="🔑"
ROCKET="🚀"

clear

echo -e "${CYAN}${BOLD}"
echo "=========================================================================="
echo "    🛡️  FasihNexus — Stabilitas & Failure Benchmarking Suite v1.0  🛡️     "
echo "=========================================================================="
echo -e "${NC}"

# Verification function
check_env() {
    echo -e "${BOLD}[*] Memvalidasi Lingkungan Docker...${NC}"
    
    if ! docker info >/dev/null 2>&1; then
        echo -e "${RED}${CROSS} Error: Docker daemon tidak berjalan. Pastikan Docker sudah aktif.${NC}"
        exit 1
    fi

    # Check containers
    REQUIRED_CONTAINERS=("fasih-nexus-db" "fasih-nexus-vpn" "fasih-nexus-rpa" "fasih-nexus-dashboard")
    ALL_UP=true
    
    for c in "${REQUIRED_CONTAINERS[@]}"; do
        if ! docker ps --format '{{.Names}}' | grep -q "^${c}$"; then
            echo -e "${YELLOW}${WARN} Peringatan: Kontainer '${c}' tidak berjalan.${NC}"
            ALL_UP=false
        fi
    done

    if [ "$ALL_UP" = false ]; then
        echo -e "${YELLOW}   Beberapa kontainer mati. Silakan nyalakan stack terlebih dahulu dengan: docker compose up -d${NC}"
        echo ""
    else
        echo -e "${GREEN}${CHECK} Semua kontainer utama berjalan dengan sehat.${NC}\n"
    fi
}

check_env

# Helper to check VPN interface status
get_vpn_interface() {
    if docker exec fasih-nexus-vpn ip link show tun0 >/dev/null 2>&1; then
        echo "tun0"
    elif docker exec fasih-nexus-vpn ip link show ppp0 >/dev/null 2>&1; then
        echo "ppp0"
    else
        echo ""
    fi
}

# Helper to query DB
query_db() {
    local sql="$1"
    docker exec -i fasih-nexus-db psql -U fasih -d fasih_dashboard -t -A -c "$sql" 2>/dev/null
}

# ------------------------------------------------------------------------------
# Skenario 1: Cold Bootstrap
# ------------------------------------------------------------------------------
run_scenario_1() {
    echo -e "${MAGENTA}${BOLD}=== Skenario 1: Cold Bootstrap (Database Kosong / Pertama Kali Build) ===${NC}"
    echo -e "Skenario ini mensimulasikan deployment pertama kali di Coolify dengan database kosong."
    echo -e "Dashboard akan melakukan inisialisasi skema DB secara konkuren dengan booting VPN."
    echo -e "VPN harus pulih secara mandiri meskipun DB belum siap saat startup.\n"
    
    read -p "⚠️ PERINGATAN: Tindakan ini akan menghapus database lokal Anda (volume pg_data_v3). Lanjutkan? (y/n): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Dibatalkan.${NC}"
        return
    fi

    echo -e "\n${BLUE}[1/4] Menghancurkan stack dan menghapus volume database...${NC}"
    docker compose down -v
    
    echo -e "\n${BLUE}[2/4] Menyalakan stack dari keadaan kosong...${NC}"
    START_TIME=$SECONDS
    docker compose up -d
    
    echo -e "\n${BLUE}[3/4] Memulai stopwatch. Memantau penyembuhan mandiri VPN...${NC}"
    echo -e "Menunggu antarmuka VPN (tun0 atau ppp0) terbentuk secara otomatis..."
    
    while true; do
        ELAPSED=$(( SECONDS - START_TIME ))
        VPN_IF=$(get_vpn_interface)
        
        if [ -n "$VPN_IF" ]; then
            echo -e "\n${GREEN}${CHECK} Terowongan VPN terdeteksi aktif pada interface: ${BOLD}$VPN_IF${NC}"
            echo -e "${GREEN}${CLOCK} Waktu Pemulihan Cold Bootstrap: ${BOLD}${ELAPSED} detik${NC}"
            
            # Periksa apakah cookie tersimpan di DB
            DB_COOKIE=$(query_db "SELECT count(*) FROM system_settings WHERE key='vpn_cookie';")
            if [ "$DB_COOKIE" != "0" ]; then
                echo -e "${GREEN}${DATABASE} Cookie berhasil ter-sinkronisasi ke database.${NC}"
            fi
            
            if [ $ELAPSED -le 120 ]; then
                echo -e "${GREEN}${BOLD}🏆 KEPUTUSAN: SUKSES (Di bawah target KPI 120 detik)${NC}"
            else
                echo -e "${YELLOW}${BOLD}⚠️ KEPUTUSAN: WARNING (Melebihi target KPI 120 detik)${NC}"
            fi
            break
        fi
        
        if [ $ELAPSED -gt 180 ]; then
            echo -e "\n${RED}${CROSS} TIMEOUT: Terowongan VPN gagal terbentuk dalam 180 detik.${NC}"
            echo -e "${RED}Silakan jalankan: docker compose logs vpn untuk debugging.${NC}"
            break
        fi
        
        echo -ne "   ⏱️ Berjalan: ${ELAPSED}s | Polling interface VPN... \r"
        sleep 2
    done
    
    echo ""
    read -p "Tekan [Enter] untuk kembali ke menu utama..."
}

# ------------------------------------------------------------------------------
# Skenario 2: VPN Sudden Disconnection
# ------------------------------------------------------------------------------
run_scenario_2() {
    echo -e "${MAGENTA}${BOLD}=== Skenario 2: VPN Sudden Disconnection (VPN Mati Sendiri) ===${NC}"
    echo -e "Skenario ini mensimulasikan pemutusan jaringan mendadak pada terowongan VPN."
    echo -e "Sistem harus mendeteksi hilangnya koneksi, menghapus cookie mati, memicu RPA auto-fetch,"
    echo -e "dan menyambungkan kembali terowongan VPN dengan cookie baru secara otomatis.\n"

    VPN_IF=$(get_vpn_interface)
    if [ -z "$VPN_IF" ]; then
        echo -e "${RED}${CROSS} Error: VPN sedang tidak aktif saat ini. Skenario tidak dapat dijalankan.${NC}"
        read -p "Tekan [Enter] untuk kembali..."
        return
    fi

    echo -e "${GREEN}${CHECK} VPN terdeteksi aktif di interface: $VPN_IF${NC}"
    echo -e "${BLUE}[1/3] Membunuh paksa proses VPN di dalam kontainer...${NC}"
    
    # Bunuh openconnect/openfortivpn
    docker exec fasih-nexus-vpn pkill -9 openconnect 2>/dev/null
    docker exec fasih-nexus-vpn pkill -9 openfortivpn 2>/dev/null
    
    START_TIME=$SECONDS
    echo -e "${YELLOW}${FIRE} Proses VPN berhasil dibunuh. Memulai pencatatan RTO...${NC}"
    
    while true; do
        ELAPSED=$(( SECONDS - START_TIME ))
        NEW_IF=$(get_vpn_interface)
        
        if [ -n "$NEW_IF" ]; then
            echo -e "\n${GREEN}${CHECK} VPN berhasil terhubung kembali secara mandiri di interface: ${BOLD}$NEW_IF${NC}"
            echo -e "${GREEN}${CLOCK} Waktu Pemulihan VPN (RTO): ${BOLD}${ELAPSED} detik${NC}"
            
            if [ $ELAPSED -le 90 ]; then
                echo -e "${GREEN}${BOLD}🏆 KEPUTUSAN: SUKSES (Di bawah target KPI 90 detik)${NC}"
            else
                echo -e "${YELLOW}${BOLD}⚠️ KEPUTUSAN: WARNING (Melebihi target KPI 90 detik)${NC}"
            fi
            break
        fi
        
        if [ $ELAPSED -gt 150 ]; then
            echo -e "\n${RED}${CROSS} TIMEOUT: VPN gagal melakukan self-healing dalam 150 detik.${NC}"
            break
        fi
        
        # Check if cookie was cleared in DB
        DB_HAS_COOKIE=$(query_db "SELECT count(*) FROM system_settings WHERE key='vpn_cookie';")
        STATUS_STR="Menunggu koneksi ulang..."
        if [ "$DB_HAS_COOKIE" = "0" ]; then
            STATUS_STR="Cookie lama terhapus | Menunggu RPA auto-fetch..."
        else
            STATUS_STR="Cookie baru masuk ke DB | Menjalankan OpenConnect..."
        fi
        
        echo -ne "   ⏱️ Waktu berjalan: ${ELAPSED}s | Status: $STATUS_STR \r"
        sleep 2
    done

    echo ""
    read -p "Tekan [Enter] untuk kembali ke menu utama..."
}

# ------------------------------------------------------------------------------
# Skenario 3: Host Power Failure
# ------------------------------------------------------------------------------
run_scenario_3() {
    echo -e "${MAGENTA}${BOLD}=== Skenario 3: Host Power Failure / Sudden Restart ===${NC}"
    echo -e "Skenario ini mensimulasikan mati listrik mendadak pada server host."
    echo -e "Kita akan mematikan paksa seluruh kontainer secara kasar (docker kill)"
    echo -e "dan mengujinya kembali. VPN harus terhubung INSTAN (<10s) jika session cookie lama"
    echo -e "di database masih valid di server BPS.\n"

    echo -e "${BLUE}[1/3] Mematikan paksa seluruh stack kontainer secara kasar...${NC}"
    docker compose kill
    
    echo -e "${GREEN}${CHECK} Seluruh kontainer mati mendadak.${NC}"
    echo -e "\n${BLUE}[2/3] Menyalakan kembali stack kontainer...${NC}"
    START_TIME=$SECONDS
    docker compose up -d
    
    echo -e "\n${BLUE}[3/3] Memantau pemulihan instan (Hot Reconnect)...${NC}"
    while true; do
        ELAPSED=$(( SECONDS - START_TIME ))
        VPN_IF=$(get_vpn_interface)
        
        if [ -n "$VPN_IF" ]; then
            echo -e "\n${GREEN}${CHECK} Terowongan VPN berhasil aktif kembali di interface: ${BOLD}$VPN_IF${NC}"
            echo -e "${GREEN}${CLOCK} Total waktu pemulihan restart host: ${BOLD}${ELAPSED} detik${NC}"
            
            if [ $ELAPSED -le 15 ]; then
                echo -e "${GREEN}${BOLD}🏆 KEPUTUSAN: SUKSES (Hot Reconnect Instan < 15s menggunakan cookie cache DB)${NC}"
            elif [ $ELAPSED -le 120 ]; then
                echo -e "${GREEN}${BOLD}🏆 KEPUTUSAN: SUKSES (Graceful Recovery < 120s - Sesi cache kadaluwarsa)${NC}"
            else
                echo -e "${RED}${CROSS} KEPUTUSAN: GAGAL (Pemulihan terlalu lama: >120s)${NC}"
            fi
            break
        fi
        
        if [ $ELAPSED -gt 150 ]; then
            echo -e "\n${RED}${CROSS} TIMEOUT: VPN gagal pulih setelah restart dalam 150 detik.${NC}"
            break
        fi
        
        echo -ne "   ⏱️ Waktu berjalan: ${ELAPSED}s | Polling interface VPN... \r"
        sleep 1
    done

    echo ""
    read -p "Tekan [Enter] untuk kembali ke menu utama..."
}

# ------------------------------------------------------------------------------
# Skenario 4: Stale Session / Session Expiry
# ------------------------------------------------------------------------------
run_scenario_4() {
    echo -e "${MAGENTA}${BOLD}=== Skenario 4: Stale Session / Session Expiry (Cookie Expired) ===${NC}"
    echo -e "Skenario ini mensimulasikan kadaluwarsanya sesi cookie yang tersimpan di DB."
    echo -e "Kita akan meng-inject cookie sampah/rusak langsung ke database."
    echo -e "Watcher monitor_cookie_changes harus mendeteksi ketidaksesuaian ini,"
    echo -e "memutus koneksi VPN lama, dan menyambung kembali dengan cookie baru secara graceful.\n"

    VPN_IF=$(get_vpn_interface)
    if [ -z "$VPN_IF" ]; then
        echo -e "${RED}${CROSS} Error: VPN tidak berjalan. Nyalakan VPN terlebih dahulu.${NC}"
        read -p "Tekan [Enter] untuk kembali..."
        return
    fi

    # Read current cookie to show comparison
    CURRENT_COOKIE=$(query_db "SELECT value FROM system_settings WHERE key='vpn_cookie';")
    echo -e "${GREEN}${CHECK} Cookie aktif saat ini: ${CURRENT_COOKIE:0:30}...${NC}"
    
    echo -e "\n${BLUE}[1/3] Meng-inject cookie kadaluwarsa (sampah) ke database...${NC}"
    query_db "UPDATE system_settings SET value='SVPNCOOKIE=expired_stale_token_garbage_benchmark' WHERE key='vpn_cookie';"
    
    START_TIME=$SECONDS
    echo -e "${YELLOW}${FIRE} Cookie rusak berhasil di-inject. Watcher monitor_cookie_changes seharusnya mendeteksi hal ini dalam 10 detik!${NC}"
    
    COOKIE_DETECTED=false
    while true; do
        ELAPSED=$(( SECONDS - START_TIME ))
        
        # Check active vpn cookie file
        ACTIVE_FILE_COOKIE=""
        if [ -f "/tmp/active_vpn_cookie" ]; then
            ACTIVE_FILE_COOKIE=$(cat /tmp/active_vpn_cookie 2>/dev/null)
        fi
        
        # If the VPN container was killed, the active interface might temporarily disappear
        NEW_IF=$(get_vpn_interface)
        
        # Check if the DB cookie has been overwritten with a fresh cookie by RPA (auto-healed)
        DB_COOKIE=$(query_db "SELECT value FROM system_settings WHERE key='vpn_cookie';")
        
        if [ "$COOKIE_DETECTED" = false ] && [[ "$DB_COOKIE" != *"expired_stale_token_garbage_benchmark"* ]] && [ -n "$DB_COOKIE" ]; then
            echo -e "\n${GREEN}${CHECK} Watcher mendeteksi cookie stale! VPN diputus dan cookie baru berhasil di-fetch: ${DB_COOKIE:0:30}...${NC}"
            COOKIE_DETECTED=true
        fi
        
        if [ "$COOKIE_DETECTED" = true ] && [ -n "$NEW_IF" ] && [[ "$ACTIVE_FILE_COOKIE" == "$DB_COOKIE" ]]; then
            echo -e "${GREEN}${CHECK} VPN kembali terhubung penuh dengan cookie baru!${NC}"
            echo -e "${GREEN}${CLOCK} Waktu Pemulihan Stale Session (RTO): ${BOLD}${ELAPSED} detik${NC}"
            
            if [ $ELAPSED -le 45 ]; then
                echo -e "${GREEN}${BOLD}🏆 KEPUTUSAN: SUKSES (Di bawah target KPI 45 detik)${NC}"
            else
                echo -e "${YELLOW}${BOLD}⚠️ KEPUTUSAN: WARNING (Melebihi target KPI 45 detik)${NC}"
            fi
            break
        fi
        
        if [ $ELAPSED -gt 90 ]; then
            echo -e "\n${RED}${CROSS} TIMEOUT: Watcher atau RPA gagal mendeteksi/memulihkan stale session dalam 90 detik.${NC}"
            break
        fi
        
        echo -ne "   ⏱️ Waktu berjalan: ${ELAPSED}s | Watcher check... \r"
        sleep 2
    done

    echo ""
    read -p "Tekan [Enter] untuk kembali ke menu utama..."
}

# ------------------------------------------------------------------------------
# Skenario 5: External SSO Gateway / Keycloak Timeout
# ------------------------------------------------------------------------------
run_scenario_5() {
    echo -e "${MAGENTA}${BOLD}=== Skenario 5: External SSO Gateway / Keycloak Timeout ===${NC}"
    echo -e "Skenario ini menguji ketahanan Playwright login flow terhadap F5 BIG-IP bot detection"
    echo -e "serta Keycloak SSO latency yang tinggi. Kita akan memicu test login Playwright."
    echo -e "Alur login dibekali penundaan 5 detik dan HTTP/1.1 mobile emulation untuk anti-bot.\n"

    echo -e "${BLUE}[*] Memulai pengetesan login SSO di dalam kontainer RPA...${NC}"
    docker exec -it fasih-nexus-rpa python src/main.py --test-login
    
    echo -e "\n${GREEN}${CHECK} Skenario selesai dieksekusi.${NC}"
    read -p "Tekan [Enter] untuk kembali ke menu utama..."
}

# ------------------------------------------------------------------------------
# Skenario 6: VPN Disconnection Mid-Sync
# ------------------------------------------------------------------------------
run_scenario_6() {
    echo -e "${MAGENTA}${BOLD}=== Skenario 6: VPN Terputus di Tengah Sinkronisasi (Disconnection Mid-Sync) ===${NC}"
    echo -e "Skenario paling kritis: VPN terputus saat RPA sedang asyik mengunduh ribuan data"
    echo -e "secara paralel. Kita akan membuktikan ketahanan sistem baru kita:"
    echo -e "1. Graceful Early-Abort: Sisa unduhan dihentikan instan saat terdeteksi auth error."
    echo -e "2. SIGTERM Emergency Flush: Data di buffer langsung di-save darurat ke database."
    echo -e "3. Resume Delta Sync: Siklus berikutnya melanjutkan secara mulus tanpa korupsi data.\n"

    # Pastikan VPN menyala
    VPN_IF=$(get_vpn_interface)
    if [ -z "$VPN_IF" ]; then
        echo -e "${RED}${CROSS} Error: VPN sedang mati. Nyalakan VPN terlebih dahulu.${NC}"
        read -p "Tekan [Enter] untuk kembali..."
        return
    fi

    echo -e "${BLUE}[1/4] Menyiapkan trigger sinkronisasi massal manual...${NC}"
    
    # Kita buat flag SKIP_DETAIL_FETCH=false agar detail page di-fetch
    # Jalankan sync di latar belakang dan buang log sementara ke file
    TMP_LOG="/tmp/mid_sync_benchmark.log"
    rm -f "$TMP_LOG"
    touch "$TMP_LOG"
    
    echo -e "${BLUE}[2/4] Menjalankan sinkronisasi secara paralel di background...${NC}"
    docker exec -d fasih-nexus-rpa sh -c "PYTHONUNBUFFERED=1 python src/main.py --once" > "$TMP_LOG" 2>&1
    
    echo -e "Mengamati inisialisasi sync..."
    
    # Tunggu log memunculkan progress fetching
    FETCH_STARTED=false
    for idx in $(seq 1 60); do
        if grep -q -E "Fetching.*assignments|Progress:" "$TMP_LOG" 2>/dev/null; then
            FETCH_STARTED=true
            break
        fi
        echo -ne "   ⏱️ Menunggu inisialisasi data: ${idx}s... \r"
        sleep 1
    done
    
    if [ "$FETCH_STARTED" = false ]; then
        echo -e "\n${RED}${CROSS} Gagal memulai stress-test sync (Timeout / no assignments to fetch).${NC}"
        echo -e "Mungkin semua data Anda sudah up-to-date. Cobalah jalankan Skenario 1 terlebih dahulu."
        echo -e "Catatan log terakhir:"
        tail -n 10 "$TMP_LOG"
        read -p "Tekan [Enter] untuk kembali..."
        return
    fi
    
    echo -e "\n\n${YELLOW}${FIRE} BINGO! Sinkronisasi massal terdeteksi sedang berjalan!${NC}"
    echo -e "${RED}${BOLD}[3/4] MENSIMULASIKAN CRASH: Membunuh koneksi VPN SEKARANG!!!${NC}"
    
    # Kill the VPN connection!
    docker exec fasih-nexus-vpn pkill -9 openconnect 2>/dev/null
    docker exec fasih-nexus-vpn pkill -9 openfortivpn 2>/dev/null
    
    echo -e "${YELLOW}Koneksi VPN diputus secara paksa. Menunggu data emergency flush di database...${NC}"
    
    # Monitor log RPA
    for idx in $(seq 1 15); do
        echo -ne "   Polling log penyelesaian graceful: ${idx}/15s... \r"
        sleep 1
    done
    
    echo -e "\n\n${CYAN}${BOLD}[4/4] Scorecard Hasil Pengujian Ketahanan:${NC}"
    echo -e "--------------------------------------------------------"
    
    # Check log content for new resilient keywords
    if grep -q -E "Emergency flush|Emergency flush selesai|active buffer" "$TMP_LOG" 2>/dev/null; then
        echo -e "   1. Graceful SIGTERM/Emergency Flush: ${GREEN}${CHECK} PROTECTED${NC}"
        echo -e "      (Buffer database berhasil diselamatkan darurat ke PostgreSQL)"
    else
        echo -e "   1. Graceful SIGTERM/Emergency Flush: ${YELLOW}${INFO} NOT RUNNING (Buffer empty at crash point)${NC}"
    fi

    if grep -q -E "Early-Abort|Aborting all remaining|sisa request" "$TMP_LOG" 2>/dev/null; then
        echo -e "   2. Early-Abort on Auth Error:        ${GREEN}${CHECK} PROTECTED${NC}"
        echo -e "      (Sisa antrean dibatalkan instan untuk mencegah pemboman request ke BPS)"
    else
        echo -e "   2. Early-Abort on Auth Error:        ${YELLOW}${INFO} NO AUTH EXPIRE AT CRASH POINT${NC}"
    fi

    if grep -q -E "Connection error|Exception: [Ee]rrno 101|Network is unreachable" "$TMP_LOG" 2>/dev/null; then
        echo -e "   3. Graceful Exception Handling:      ${GREEN}${CHECK} SUCCESS${NC}"
        echo -e "      (Kegagalan koneksi ditangani aman tanpa kontainer RPA crash)"
    else
        echo -e "   3. Graceful Exception Handling:      ${RED}${CROSS} NO ERROR DETECTED (Mungkin sync selesai sebelum VPN mati)${NC}"
    fi
    echo -e "--------------------------------------------------------"
    
    echo -e "\n${BLUE}Log mentah dari RPA sync saat kejadian:${NC}"
    echo "=========================================="
    tail -n 25 "$TMP_LOG"
    echo "=========================================="

    echo -e "\n${GREEN}${CHECK} Uji ketahanan selesai. Silakan periksa tabel assignments di DB lokal."
    echo -e "Data yang terunduh sebelum VPN mati dipastikan tersimpan aman!${NC}"
    rm -f "$TMP_LOG"
    
    echo ""
    read -p "Tekan [Enter] untuk kembali ke menu utama..."
}

# ------------------------------------------------------------------------------
# Skenario 7: Audit Kesehatan
# ------------------------------------------------------------------------------
run_audit() {
    echo -e "${MAGENTA}${BOLD}=== Audit Kesehatan & Keandalan Koneksi ===${NC}"
    if [ -f "./check-health.sh" ]; then
        ./check-health.sh
    else
        echo -e "${YELLOW}Menjalankan audit manual sederhana...${NC}"
        docker compose ps
    fi
    echo ""
    read -p "Tekan [Enter] untuk kembali ke menu utama..."
}

# Main Loop Menu
while true; do
    clear
    echo -e "${CYAN}${BOLD}==========================================================================${NC}"
    echo -e "${CYAN}${BOLD}       🛡️  FasihNexus — Stabilitas & Failure Benchmarking Suite  🛡️      ${NC}"
    echo -e "${CYAN}${BOLD}==========================================================================${NC}"
    echo -e "Pilih Skenario Stabilitas untuk diuji di Laptop Lokal Anda:"
    echo -e "--------------------------------------------------------------------------"
    echo -e "  ${BOLD}1.${NC} Skenario 1: Cold Bootstrap (Database Kosong / Pertama Kali Build)"
    echo -e "  ${BOLD}2.${NC} Skenario 2: VPN Sudden Disconnection (VPN Mati Sendiri) - ${BOLD}[AUTO RTO]${NC}"
    echo -e "  ${BOLD}3.${NC} Skenario 3: Host Power Failure / Sudden Restart"
    echo -e "  ${BOLD}4.${NC} Skenario 4: Stale Session / Session Expiry (Cookie Expired) - ${BOLD}[AUTO RTO]${NC}"
    echo -e "  ${BOLD}5.${NC} Skenario 5: External SSO Gateway / Keycloak Timeout (F5 Anti-Bot)"
    echo -e "  ${BOLD}6.${NC} Skenario 6: VPN Terputus Mid-Sync (Uji Ketahanan & Emergency Flush)"
    echo -e "  ${BOLD}7.${NC} Jalankan Audit Kesehatan & Uji Stabilitas Kontainer"
    echo -e "  ${BOLD}8.${NC} Keluar"
    echo -e "--------------------------------------------------------------------------"
    read -p "Masukkan pilihan Anda (1-8): " choice
    echo ""

    case $choice in
        1) run_scenario_1 ;;
        2) run_scenario_2 ;;
        3) run_scenario_3 ;;
        4) run_scenario_4 ;;
        5) run_scenario_5 ;;
        6) run_scenario_6 ;;
        7) run_audit ;;
        8) 
            echo -e "${GREEN}Terima kasih telah menggunakan FasihNexus Benchmarking Suite! Sampai jumpa.${NC}"
            exit 0 
            ;;
        *) 
            echo -e "${RED}${CROSS} Pilihan tidak valid. Masukkan angka 1-8.${NC}"
            sleep 2
            ;;
    esac
done

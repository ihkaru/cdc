#!/bin/bash

# ==========================================================
# FasihNexus API Benchmark Tool
# Mengukur performa end-to-end dari Dashboard ke Robot RPA
# ==========================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}       FasihNexus API Performance Audit          ${NC}"
echo -e "${BLUE}=================================================${NC}"

# 1. Test Dashboard Base Latency (Bun/Elysia)
echo -ne "🚀 [1/3] Dashboard Base Latency... "
START=$(date +%s%N)
curl -s -o /dev/null http://127.0.0.1:9000/api/surveys/vpn/status
END=$(date +%s%N)
DIFF=$((($END - $START)/1000000))
echo -e "${GREEN}${DIFF}ms${NC}"

# 2. Test VPN Tunnel Latency (Direct to FASIH-SM via RPA Proxy)
echo -ne "🔒 [2/3] VPN Tunnel Reachability... "
START=$(date +%s%N)
curl -s -o /dev/null http://127.0.0.1:8000/vpn/check
END=$(date +%s%N)
DIFF=$((($END - $START)/1000000))
if [ $DIFF -lt 2000 ]; then
    echo -e "${GREEN}${DIFF}ms (Fast)${NC}"
else
    echo -e "${YELLOW}${DIFF}ms (High Latency - VPN Bottleneck?)${NC}"
fi

# 3. Test Metadata Lookup (Playwright SSO Flow)
echo -e "${YELLOW}🤖 [3/3] RPA Metadata Lookup (SSO Login Flow)...${NC}"
echo -e "   (Ini akan memakan waktu 15-45 detik karena robot harus login SSO)"

# Membaca kredensial dari .env jika ada untuk simulasi
SSO_USER=$(grep SSO_USER .env 2>/dev/null | cut -d '=' -f2 | xargs)
SSO_PASS=$(grep SSO_PASS .env 2>/dev/null | cut -d '=' -f2 | xargs)

if [ -z "$SSO_USER" ]; then
    SSO_USER=$(grep VPN_USER .env 2>/dev/null | cut -d '=' -f2 | xargs)
    SSO_PASS=$(grep VPN_PASS .env 2>/dev/null | cut -d '=' -f2 | xargs)
fi

if [ -z "$SSO_USER" ]; then
    echo -e "${RED}   Gagal: SSO_USER atau VPN_USER tidak ditemukan di .env. Lewati tes lookup.${NC}"
else
    START_LOOKUP=$(date +%s)
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST http://127.0.0.1:8000/lookup/metadata \
        -H "Content-Type: application/json" \
        -d "{\"sso_username\": \"$SSO_USER\", \"sso_password\": \"$SSO_PASS\"}")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
    END_LOOKUP=$(date +%s)
    DURATION=$((END_LOOKUP - START_LOOKUP))

    if [ "$HTTP_CODE" == "200" ]; then
        echo -e "${GREEN}   ✅ Success in ${DURATION}s${NC}"
    else
        echo -e "${RED}   ❌ Failed with code ${HTTP_CODE} in ${DURATION}s${NC}"
    fi
fi

echo -e "${BLUE}=================================================${NC}"
echo -e "Audit Selesai."

#!/usr/bin/env bash
# ======================================================================
#            FasihNexus — Concurrency Performance Experiment            
# ======================================================================
# Menjalankan stress-test concurrency untuk menentukan batas maksimum 
# request paralel detail assignment yang didukung oleh gateway BPS.
# ======================================================================

set -e

# Load environment variables if available
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Terminal colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0;0m' # No Color

echo -e "${BLUE}======================================================================${NC}"
echo -e "         ${CYAN}FasihNexus — Concurrency Performance Stress Tester${NC}          "
echo -e "${BLUE}======================================================================${NC}"

# Ensure rpa container is running
if ! docker compose -f docker-compose.yml -f docker-compose.local.yml ps | grep -q "fasih-nexus-rpa.*Up"; then
    echo -e "${YELLOW}[WARN] Container RPA tidak aktif. Mencoba mengaktifkan stack...${NC}"
    docker compose -f docker-compose.yml -f docker-compose.local.yml up -d rpa fasih-db vpn
    echo -e "${GREEN}[OK] Stack diaktifkan.${NC}"
    sleep 3
fi

# Copy all source files to the running container
echo -e "${GREEN}[INFO] Menyalin seluruh source code RPA ke dalam kontainer...${NC}"
docker cp rpa/src/. fasih-nexus-rpa:/app/src/

# Run python stress-test script inside container
echo -e "${GREEN}[INFO] Menjalankan experiment stress-test di dalam kontainer Docker...${NC}"
echo -e "${YELLOW}Ini akan memakan waktu sekitar 1-2 menit tergantung daftar concurrency yang diuji...${NC}"
echo ""

docker compose -f docker-compose.yml -f docker-compose.local.yml exec -w /app/src rpa python test_concurrency_perf.py "$@"

echo -e "${GREEN}======================================================================${NC}"
echo -e "🎉 ${CYAN}EXPERIMENT COMPLETED SUCCESSFULLY!${NC}"
echo -e "${GREEN}======================================================================${NC}"

#!/bin/bash
# FasihNexus Pre-Flight Validator (Health Check)
# Digunakan untuk memastikan kode siap deploy ke Coolify/Production.

set -e

# Warna untuk output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}      FasihNexus - Pre-Flight Validator          ${NC}"
echo -e "${BLUE}=================================================${NC}"

# 1. Validasi Environment File
echo -n "[1/7] Checking .env integrity... "
if [ ! -f .env ]; then
    echo -e "${RED}FAILED${NC}"
    echo "      Error: .env file missing. Please copy from .env.example"
    exit 1
fi
# Cek apakah variabel kritikal ada isinya
MISSING_VARS=0
check_var() {
    if ! grep -q "^$1=" .env || grep -q "^$1=[[:space:]]*$" .env; then
        echo -e "\n      ${RED}⚠️  Warning: $1 is empty or missing in .env${NC}"
        MISSING_VARS=$((MISSING_VARS + 1))
    fi
}
check_var "BETTER_AUTH_SECRET"
check_var "ENCRYPTION_KEY"
check_var "DATABASE_URL"

if [ $MISSING_VARS -eq 0 ]; then echo -e "${GREEN}OK${NC}"; else echo -e "      Status: ${RED}Incomplete${NC}"; fi

# 2. Validasi Docker Compose
echo -n "[2/7] Validating Docker Compose schema... "
if docker compose config > /dev/null 2>&1; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
    docker compose config
    exit 1
fi

# 3. Type-Check Backend (Elysia)
echo -e "[3/7] Running TypeScript check on Server (Backend)... "
cd dashboard/server
if bun x tsc --noEmit; then
    echo -e "      ${GREEN}Backend Types OK${NC}"
else
    echo -e "      ${RED}Backend Type Errors Detected${NC}"
    exit 1
fi
cd ../..

# 4. Type-Check Frontend (Quasar/Vue)
echo -e "[4/7] Running TypeScript check on Client (Frontend)... "
cd dashboard/client
# Menggunakan vue-tsc untuk validasi template Vue + TS
if bun x vue-tsc --noEmit; then
    echo -e "      ${GREEN}Frontend Types OK${NC}"
else
    echo -e "      ${RED}Frontend Type Errors Detected${NC}"
    exit 1
fi
cd ../..

# 5. Static Code Analysis - Biome (Frontend & Backend)
echo -e "[5/7] Running Biome Lint & Format Check... "
if bunx @biomejs/biome check dashboard/server dashboard/client; then
    echo -e "      ${GREEN}Biome Linter OK${NC}"
else
    echo -e "      ${RED}Biome Linter detected issues (run 'bunx @biomejs/biome check --write' to auto-fix)${NC}"
    exit 1
fi

# 6. Static Code Analysis - Ruff (Python Engine)
echo -e "[6/7] Running Ruff Python Check... "
if rpa/venv/bin/ruff check rpa/src; then
    echo -e "      ${GREEN}Ruff Linter OK${NC}"
else
    echo -e "      ${RED}Ruff Linter detected issues (run 'rpa/venv/bin/ruff check --fix' to auto-fix)${NC}"
    exit 1
fi

# 7. Static Code Analysis - Basedpyright (Python Types)
echo -e "[7/7] Running Basedpyright Type Check... "
if bunx basedpyright rpa/src; then
    echo -e "      ${GREEN}Basedpyright Type Check OK${NC}"
else
    echo -e "      ${RED}Basedpyright detected type or import issues${NC}"
    exit 1
fi

echo -e "${BLUE}=================================================${NC}"
echo -e "${GREEN}✅ PASSED: FasihNexus is ready for deployment!${NC}"
echo -e "${BLUE}=================================================${NC}"

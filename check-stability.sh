#!/bin/bash

# =================================================
#      FasihNexus - Stability & Health Checker
# =================================================
# This script simulates Traefik's routing logic by 
# verifying Docker Health status and connectivity.

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🔍 Starting Stability Audit...${NC}"

# 1. Wait and Check Docker Health Status (The Traefik "Golden Rule")
SERVICES=("fasih-nexus-db" "fasih-nexus-vpn" "fasih-nexus-rpa" "fasih-nexus-dashboard")
MAX_RETRIES=12
RETRY_COUNT=0
echo -e "${YELLOW}⏳ Waiting for all services to become HEALTHY...${NC}"

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    STILL_STARTING=false
    for service in "${SERVICES[@]}"; do
        HEALTH=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "$service" 2>/dev/null)
        if [ "$HEALTH" == "starting" ]; then
            STILL_STARTING=true
            break
        fi
    done

    if [ "$STILL_STARTING" = false ]; then
        break
    fi

    echo -ne "   ...waiting for startup (${RETRY_COUNT}/${MAX_RETRIES})\r"
    sleep 5
    RETRY_COUNT=$((RETRY_COUNT+1))
done
echo -e "\n"

ALL_HEALTHY=true
for service in "${SERVICES[@]}"; do
    STATE=$(docker inspect --format='{{.State.Status}}' "$service" 2>/dev/null)
    HEALTH=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "$service" 2>/dev/null)
    
    if [ -z "$STATE" ] || [ "$STATE" != "running" ]; then
        echo -e "${RED}❌ $service: NOT RUNNING (Status: ${STATE:-missing})${NC}"
        ALL_HEALTHY=false
    elif [ "$HEALTH" == "unhealthy" ] || ([ "$service" == "fasih-nexus-vpn" ] && [ "$HEALTH" == "starting" ] && [ $RETRY_COUNT -eq $MAX_RETRIES ]); then
        if [ "$service" == "fasih-nexus-vpn" ]; then
            echo -e "${YELLOW}⚠️ $service: Detected GHOST SESSION or CONNECTION FAILURE.${NC}"
            echo -e "${YELLOW}🛠️  Attempting Self-Healing (Auto-fetching fresh SAML cookie)...${NC}"
            
            # Load credentials from .env
            VPN_USER=$(grep VPN_USER .env | cut -d '=' -f2)
            VPN_PASS=$(grep VPN_PASS .env | cut -d '=' -f2)
            
            if [ -n "$VPN_USER" ] && [ -n "$VPN_PASS" ]; then
                # Trigger RPA Auto-Fetch (vpn-auth runs on port 8000)
                RESP=$(curl -s -X POST http://127.0.0.1:8000/vpn/auto-fetch \
                    -H "Content-Type: application/json" \
                    -d "{\"sso_username\":\"$VPN_USER\", \"sso_password\":\"$VPN_PASS\"}")
                
                if echo "$RESP" | grep -q "success"; then
                    echo -e "${GREEN}✅ Auto-fetch success! VPN will reconnect shortly via DB trigger.${NC}"
                    echo -e "${YELLOW}⏳ Waiting 15s for reconnection...${NC}"
                    sleep 15
                    # Re-check status once
                    HEALTH=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "$service" 2>/dev/null)
                    if [ "$HEALTH" == "healthy" ]; then
                        echo -e "${GREEN}✅ $service: RECOVERED & HEALTHY${NC}"
                        continue
                    fi
                else
                    echo -e "${RED}❌ Auto-fetch failed: $RESP${NC}"
                fi
            else
                echo -e "${RED}❌ Self-healing skipped: VPN_USER/PASS not found in .env${NC}"
            fi
        fi
        
        echo -e "${RED}❌ $service: $HEALTH (Traefik will DROP traffic!)${NC}"
        ALL_HEALTHY=false
    elif [ "$HEALTH" == "starting" ]; then
        echo -e "${RED}❌ $service: TIMEOUT (Still starting after 60s)${NC}"
        ALL_HEALTHY=false
    elif [ "$HEALTH" == "no-healthcheck" ]; then
        echo -e "${GREEN}✅ $service: Running (No explicit healthcheck defined)${NC}"
    else
        echo -e "${GREEN}✅ $service: HEALTHY${NC}"
    fi
done

# 3. Network Connectivity Check (Simulation of Real Traffic)
echo -e "\n${YELLOW}🌐 Simulating Traffic Routing...${NC}"

# Dashboard API Health (with retry)
DASHBOARD_OK=false
for i in {1..5}; do
    if curl -s -f http://127.0.0.1:3000/api/health > /dev/null; then
        DASHBOARD_OK=true
        break
    fi
    sleep 2
done

if [ "$DASHBOARD_OK" = true ]; then
    echo -e "${GREEN}✅ Dashboard API: Reachable at port 3000${NC}"
else
    echo -e "${RED}❌ Dashboard API: Failed to respond at port 3000${NC}"
    ALL_HEALTHY=false
fi

# RPA API Health (with retry)
RPA_OK=false
for i in {1..5}; do
    if curl -s -f http://127.0.0.1:8000/health > /dev/null; then
        RPA_OK=true
        break
    fi
    sleep 2
done

if [ "$RPA_OK" = true ]; then
    echo -e "${GREEN}✅ RPA Sync Engine: Reachable at port 8000${NC}"
else
    echo -e "${RED}❌ RPA Sync Engine: Failed to respond at port 8000${NC}"
    ALL_HEALTHY=false
fi

# 4. Final Verdict
echo -e "\n================================================="
if [ "$ALL_HEALTHY" = true ]; then
    echo -e "${GREEN}✅ STABILITY VERIFIED: All systems are green.${NC}"
    exit 0
else
    echo -e "${RED}❌ STABILITY FAILED: Fix the issues above before push!${NC}"
    exit 1
fi

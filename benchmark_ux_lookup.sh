#!/bin/bash

# RPA berbagi network dengan container VPN (network_mode: service:vpn)
# Port 8000 tidak di-expose ke host — akses lewat IP VPN container di Docker bridge network
API_URL="http://127.0.0.1:8000/lookup/metadata"
# Membaca kredensial dari .env jika ada
SSO_USER="ihzakarunia@bps.go.id"
SSO_PASS='Fikrizaki2!'

if [ -f .env ]; then
    ENV_USER=$(grep VPN_USER .env | cut -d '=' -f2 | xargs)
    ENV_PASS=$(grep VPN_PASS .env | cut -d '=' -f2 | xargs)
    if [ -n "$ENV_USER" ]; then
        SSO_USER="$ENV_USER"
        SSO_PASS="$ENV_PASS"
    fi
fi

echo "================================================="
echo "   FasihNexus UX Benchmark: RCA Transparent Mode "
echo "================================================="
echo "👤 User: $SSO_USER"
echo "-------------------------------------------------"

run_benchmark() {
    local label=$1
    echo "🚀 Running Request: $label..."
    
    # Capture response and time
    start_time=$(date +%s%N)
    response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL" \
        -H "Content-Type: application/json" \
        -d "{\"sso_username\": \"$SSO_USER\", \"sso_password\": \"$SSO_PASS\"}")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    end_time=$(date +%s%N)
    
    duration_ms=$(( (end_time - start_time) / 1000000 ))

    if [ "$http_code" -eq 200 ]; then
        echo "✅ SUCCESS in ${duration_ms}ms"
        
        # Extract timings using jq if available, else raw
        if command -v jq >/dev/null 2>&1; then
            echo "--- RCA Breakdown ---"
            echo "$body" | jq -r '.debug_timings | to_entries | .[] | "📍 \(.key): \(.value)ms"'
            is_cache=$(echo "$body" | jq -r '.debug_timings.cache_hit')
            if [ "$is_cache" == "true" ]; then
                echo "✨ RESULT: CACHE HIT (Premium UX)"
            else
                echo "❄️  RESULT: COLD START (Browser Required)"
            fi
        else
            echo "Body: $body"
        fi
    else
        echo "❌ FAILED with Status: $http_code"
        echo "Error: $body"
    fi
    echo "-------------------------------------------------"
}

# 1. Cold Start
run_benchmark "1. COLD START (Fresh Session)"

# 2. Warm Start
echo "⏳ Waiting 2 seconds for DB stability..."
sleep 2
run_benchmark "2. WARM START (Cached Session)"

# 3. Concurrent Check
echo "🔥 Stress Test: Concurrent Request..."
run_benchmark "3. REPEAT (Consistency Check)"

echo "Done."

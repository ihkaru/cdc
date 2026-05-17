#!/bin/sh

# Unified Logging Helper
log() {
    LEVEL=${2:-"info"}
    MSG=$1
    TIME_ISO=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ")
    if [ "$LOG_FORMAT" = "json" ] || [ "$ENV" = "production" ]; then
        ESCAPED_MSG=$(echo "$MSG" | sed 's/"/\\"/g')
        printf '{"time":"%s","level":"%s","trace_id":"vpn-gateway","message":"%s","module":"vpn-entrypoint"}\n' "$TIME_ISO" "$LEVEL" "$ESCAPED_MSG"
    else
        TIME_STR=$(date +'%H:%M:%S')
        case "$LEVEL" in
            "debug") LVL_STR="\033[34m[DEBUG]\033[0m" ;;
            "info")  LVL_STR="\033[32m[INFO] \033[0m" ;;
            "warn")  LVL_STR="\033[33m[WARN] \033[0m" ;;
            "error") LVL_STR="\033[31m[ERROR]\033[0m" ;;
            *)       LVL_STR="\033[32m[INFO] \033[0m" ;;
        esac
        printf '\033[90m[%s]\033[0m %b \033[36m[vpn-gateway]\033[0m %s\n' "$TIME_STR" "$LVL_STR" "$MSG"
    fi
}

# 🛡️ Disable IPv6 to prevent connection resets (ERR_CONNECTION_RESET)
sysctl -w net.ipv6.conf.all.disable_ipv6=1 >/dev/null 2>&1 || true
sysctl -w net.ipv6.conf.default.disable_ipv6=1 >/dev/null 2>&1 || true

# Base config
mkdir -p /etc/openfortivpn

# Ensure vpnc-script symlink exists so openconnect can set up routing correctly
mkdir -p /etc/vpnc
if [ ! -f /etc/vpnc/vpnc-script ] && [ -f /usr/share/vpnc-scripts/vpnc-script ]; then
    log "🔗 Creating symlink for vpnc-script..." "info"
    ln -sf /usr/share/vpnc-scripts/vpnc-script /etc/vpnc/vpnc-script
fi

# Add public DNS fallback so we can always resolve akses.bps.go.id for auto-reconnect
echo "nameserver 8.8.8.8" >> /etc/resolv.conf
echo "nameserver 1.1.1.1" >> /etc/resolv.conf

# Clean up only specifically if we need to, but let's avoid wiping extra_hosts for now
# as it breaks fasih-sm.bps.go.id pinning from docker-compose.

# Wait a bit for Docker DNS to be fully ready
sleep 2

# Inject database IP into /etc/hosts so it survives DNS overrides
for i in 1 2 3; do
    DB_IP=$(getent hosts fasih-db | awk '{print $1}')
    [ -n "$DB_IP" ] && break
    sleep 1
done

if [ -n "$DB_IP" ]; then
    log "📌 Mapping fasih-db -> $DB_IP in /etc/hosts" "info"
    echo "$DB_IP fasih-db" >> /etc/hosts
fi

# Inject S3 IP into /etc/hosts
for i in 1 2 3; do
    S3_IP=$(getent hosts fasih-nexus-s3 | awk '{print $1}')
    if [ -z "$S3_IP" ]; then S3_IP=$(getent hosts s3 | awk '{print $1}'); fi
    [ -n "$S3_IP" ] && break
    sleep 1
done

if [ -n "$S3_IP" ]; then
    log "📌 Mapping fasih-nexus-s3 -> $S3_IP in /etc/hosts" "info"
    echo "$S3_IP fasih-nexus-s3" >> /etc/hosts
    echo "$S3_IP s3" >> /etc/hosts
fi

# 📉 Restore eth0 MTU to default (1500) for stable inter-container comms
log "📉 Ensuring eth0 MTU is 1500..." "info"
ip link set eth0 mtu 1500 2>/dev/null || true

GATEWAY_IP=$(ip route | grep default | awk '{print $3}')

# 🛠️ DYNAMIC FIX: Ensure internal Docker network stays on eth0
# We detect the actual subnet of eth0 to avoid hardcoding 172.16.0.0/12
# which might change in production environments like Coolify.
LOCAL_SUBNET=$(ip route show dev eth0 | grep "proto kernel" | awk '{print $1}')
if [ -n "$GATEWAY_IP" ] && [ -n "$LOCAL_SUBNET" ]; then
    log "🛣️  Pinning local Docker network ($LOCAL_SUBNET) to eth0 via $GATEWAY_IP" "info"
    ip route add "$LOCAL_SUBNET" dev eth0 via "$GATEWAY_IP" 2>/dev/null || true
fi
# Helper function to handle graceful shutdown
cleanup() {
    log "🛑 Caught termination signal! Shutting down..." "warn"
    pkill -x openconnect 2>/dev/null
    pkill -x openfortivpn 2>/dev/null
    kill $(jobs -p) 2>/dev/null
    exit 0
}

trap cleanup INT TERM

# 🛡️ MTU Watchdog: Permanently locks VPN MTU to prevent resets
mtu_watchdog() {
    log "🛡️ MTU Watchdog started (Target: 500)" "info"
    while true; do
        sleep 10
        VPN_IF=""
        if [ -d "/sys/class/net/tun0" ]; then VPN_IF="tun0"; fi
        if [ -z "$VPN_IF" ] && [ -d "/sys/class/net/ppp0" ]; then VPN_IF="ppp0"; fi
        
        if [ -n "$VPN_IF" ]; then
            CURRENT_MTU=$(cat "/sys/class/net/$VPN_IF/mtu" 2>/dev/null)
            if [ "$CURRENT_MTU" != "500" ]; then
                log "🛡️ MTU Watchdog: Re-locking $VPN_IF MTU to 500 (was $CURRENT_MTU)..." "warn"
                ip link set dev "$VPN_IF" mtu 500 2>/dev/null || true
            fi
        fi
    done
}

mtu_watchdog &

# Background Watcher: Monitors DB for cookie changes and triggers restart
monitor_cookie_changes() {
    # Clean up any stale active cookie file on boot
    rm -f /tmp/active_vpn_cookie
    
    while true; do
        sleep 10
        if [ -n "$DATABASE_URL" ]; then
            CURRENT_DB_COOKIE=$(psql "$DATABASE_URL" -t -A -c "SELECT value FROM system_settings WHERE key='vpn_cookie'" 2>/dev/null)
            ACTIVE_COOKIE=""
            if [ -f "/tmp/active_vpn_cookie" ]; then
                ACTIVE_COOKIE=$(cat /tmp/active_vpn_cookie 2>/dev/null)
            fi
            
            if [ -n "$CURRENT_DB_COOKIE" ] && [ -n "$ACTIVE_COOKIE" ] && [ "$CURRENT_DB_COOKIE" != "$ACTIVE_COOKIE" ]; then
                ACTIVE_COOKIE_PART=$(echo "$ACTIVE_COOKIE" | cut -c 1-15)
                DB_COOKIE_PART=$(echo "$CURRENT_DB_COOKIE" | cut -c 1-15)
                log "🔄 DB Cookie changed! Active cookie: ${ACTIVE_COOKIE_PART}..., DB cookie: ${DB_COOKIE_PART}..." "info"
                log "🔄 DB Cookie changed! Triggering organic VPN reconnect..." "info"
                rm -f /tmp/active_vpn_cookie
                pkill -x openconnect 2>/dev/null
                pkill -x openfortivpn 2>/dev/null
            fi
        fi
    done
}

monitor_cookie_changes &

# SMART Route Enforcement Helper
apply_smart_routing() {
    log "⏳ Waiting for interface tun0 or ppp0 to apply Smart Routing..." "info"
    VPN_IF=""
    for i in $(seq 1 30); do
        if [ -d "/sys/class/net/tun0" ]; then VPN_IF="tun0"; break; fi
        if [ -d "/sys/class/net/ppp0" ]; then VPN_IF="ppp0"; break; fi
        sleep 1
    done

    if [ -n "$VPN_IF" ]; then
        # Wait for IP address
        for i in $(seq 1 10); do
            if ip addr show "$VPN_IF" 2>/dev/null | grep -q "inet "; then
                log "✅ Interface $VPN_IF is fully UP. Applying route fixes..." "info"
                break
            fi
            sleep 1
        done
        
        # Resolve target and force route
        TARGET_DOMAIN="fasih-sm.bps.go.id"
        log "🔍 Resolving $TARGET_DOMAIN..." "info"
        
        TARGET_IP=""
        for j in 1 2 3 4 5; do
            TARGET_IP=$(getent hosts "$TARGET_DOMAIN" | awk 'NR==1 {print $1}')
            [ -n "$TARGET_IP" ] && break
            sleep 2
        done
        
        if [ -n "$TARGET_IP" ]; then
            log "📍 Site $TARGET_DOMAIN resolved to $TARGET_IP" "info"
            
            grep -v "$TARGET_DOMAIN" /etc/hosts > /tmp/hosts && cat /tmp/hosts > /etc/hosts
            echo "$TARGET_IP $TARGET_DOMAIN" >> /etc/hosts
            log "📌 Pinned $TARGET_DOMAIN -> $TARGET_IP in /etc/hosts" "info"

            log "🔌 Prioritizing Docker DNS and injecting BPS Nameservers..." "info"
            echo -e "nameserver 127.0.0.11\nnameserver 10.10.11.11\nnameserver 10.10.11.12\n$(grep -vE '127.0.0.11|10.10.11.11|10.10.11.12' /etc/resolv.conf)" > /etc/resolv.conf
            
            if ! ip route get "$TARGET_IP" 2>/dev/null | grep -q "dev $VPN_IF"; then
                log "🛠️  Forcing route for $TARGET_IP via $VPN_IF..." "info"
                ip route add "$TARGET_IP"/32 dev "$VPN_IF" 2>/dev/null || true
            fi

            log "🌐 Routing BPS DNS servers via $VPN_IF..." "info"
            ip route add 172.16.2.2/32 dev "$VPN_IF" 2>/dev/null || true
            ip route add 172.16.2.3/32 dev "$VPN_IF" 2>/dev/null || true
            ip route add 10.0.0.0/8 dev "$VPN_IF" 2>/dev/null || true
            
            log "📉 Setting $VPN_IF MTU to 500..." "info"
            ip link set dev "$VPN_IF" mtu 500 || true
            
            # 🛡️ MSS Clamping: Force TCP to use small packets to prevent "silent hangs"
            iptables -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 460
            iptables -t mangle -A POSTROUTING -p tcp --tcp-flags SYN,RST SYN -o "$VPN_IF" -j TCPMSS --set-mss 460
            
            log "✅ BPS Routing & MSS Clamping updated." "info"
        else
            log "⚠️  Could not resolve $TARGET_DOMAIN (DNS Timeout)." "warn"
        fi
        return 0
    fi
    log "❌ No VPN interface appeared. Skipping Smart Routing." "error"
}

log "🚀 Starting VPN Architecture (Self-Healing Enabled)..." "info"

while true; do
    # --- Cleanup stale ppp0 interface to prevent 'Interface ppp0: Exist' on reconnect ---
    if ip link show ppp0 > /dev/null 2>&1; then
        log "🧹 Removing stale ppp0 interface..." "info"
        ip link set ppp0 down 2>/dev/null || true
        ip link delete ppp0 2>/dev/null || true
        sleep 1
    fi



    # Priority: database ALWAYS (env var is usually stale)
    COOKIE=""
    
    # Try reading cookie from PostgreSQL
    if [ -n "$DATABASE_URL" ]; then
        DB_COOKIE=$(psql "$DATABASE_URL" -t -A -c "SELECT value FROM system_settings WHERE key='vpn_cookie'" 2>/dev/null)
        if [ -n "$DB_COOKIE" ]; then
            COOKIE="$DB_COOKIE"
            log "🔑 Fresh cookie loaded from database (Length: ${#COOKIE})" "info"
        else
            log "⏳ No cookie found in database. Triggering RPA auto-fetch via internet..." "info"
            # RPA shares the same network namespace, so we use 127.0.0.1
            # We use a retry loop because RPA might still be starting its web server.
            for attempt in $(seq 1 6); do
                RESP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "http://127.0.0.1:8000/vpn/auto-fetch" \
                    -H "Content-Type: application/json" \
                    -d "{\"sso_username\":\"$VPN_USER\", \"sso_password\":\"$VPN_PASS\"}")
                
                if [ "$RESP" = "200" ]; then
                    log "   ✅ RPA auto-fetch triggered in background. Polling DB for fresh cookie..." "info"
                    for poll in $(seq 1 12); do
                        sleep 5
                        DB_COOKIE=$(psql "$DATABASE_URL" -t -A -c "SELECT value FROM system_settings WHERE key='vpn_cookie'" 2>/dev/null)
                        if [ -n "$DB_COOKIE" ]; then
                            COOKIE="$DB_COOKIE"
                            log "🔑 Fresh cookie loaded from database after auto-fetch polling (Attempt $poll/12, Length: ${#COOKIE})" "info"
                            break 2
                        fi
                        log "      ⏳ Waiting for RPA background fetch to complete ($poll/12)..." "info"
                    done
                    
                    # If we exhausted the polling loop and COOKIE is still empty, break attempt loop to allow password fallback
                    if [ -z "$COOKIE" ]; then
                        log "   ❌ Timeout waiting for RPA background fetch to save cookie." "warn"
                        break
                    fi
                fi
                log "   ⚠️ RPA not ready yet ($attempt/6, code: $RESP), retrying in 10s..." "warn"
                sleep 10
            done
        fi
    fi

    # ONLY fallback to env var if DB is not available (Legacy mode)
    if [ -z "$DATABASE_URL" ] && [ -n "${VPN_COOKIE}" ]; then
        COOKIE="${VPN_COOKIE}"
        log "🔑 Cookie loaded from env var (Legacy Fallback)" "info"
    fi

    if [ -n "$COOKIE" ]; then
        VAL=$(echo "$COOKIE" | grep -o 'SVPNCOOKIE=[^;]*' | sed 's/^SVPNCOOKIE=//')
        if [ -z "$VAL" ]; then VAL="$COOKIE"; fi

        # Write active cookie to file to communicate with monitor background process
        echo "$COOKIE" > /tmp/active_vpn_cookie

        log "🔗 Connecting with cookie (OpenConnect Mode)..." "info"
        log "🚀 Using DTLS + Android Spoofing for 'Lightning Fast' performance" "info"
        
        # 📱 Android Spoofing for 'Lightning Fast' performance
        ANDROID_UA="Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36 FortiClient/7.2.4"
        
        # Run smart routing in the background to apply as soon as interface comes up
        apply_smart_routing &
        
        # We try OpenConnect first. We force standard HTTPS/TLS with --no-dtls to avoid DTLS dead-peer detection drops and cookie invalidations.
        openconnect --protocol=fortinet \
            "${VPN_HOST}:${VPN_PORT:-443}" \
            --cookie="SVPNCOOKIE=$VAL" \
            --useragent="$ANDROID_UA" \
            --os=android \
            --no-dtls \
            --reconnect-timeout 60 \
            --passwd-on-stdin \
            --servercert "pin-sha256:u5HMq39pIYRefHyrvy+wZgxcW/a+Oa5N0x65brFLNsA=" <<EOF
$VAL
EOF
        
        EXIT_STATUS=$?
        
        if [ $EXIT_STATUS -ne 0 ]; then
            log "⚠️ OpenConnect failed to start or run (Status: $EXIT_STATUS). Falling back to openfortivpn..." "warn"
            apply_smart_routing &
            openfortivpn "${VPN_HOST}:${VPN_PORT:-443}" \
                --cookie="$VAL" \
                ${VPN_TRUSTED_CERT:+--trusted-cert "$VPN_TRUSTED_CERT"} \
                --set-dns=1 \
                --pppd-use-peerdns=1
            EXIT_STATUS=$?
        fi
    else
        log "👤 Using Username/Password Mode (OpenConnect)..." "info"
        # 📱 Android Spoofing for Password Mode
        ANDROID_UA="Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36 FortiClient/7.2.4"
        
        apply_smart_routing &
        
        openconnect --protocol=fortinet \
            "${VPN_HOST}:${VPN_PORT:-443}" \
            -u "$VPN_USER" \
            --useragent="$ANDROID_UA" \
            --os=android \
            --no-dtls \
            --passwd-on-stdin \
            --servercert "pin-sha256:u5HMq39pIYRefHyrvy+wZgxcW/a+Oa5N0x65brFLNsA=" <<EOF
$VPN_PASS
EOF
            
        EXIT_STATUS=$?
        
        if [ $EXIT_STATUS -ne 0 ]; then
            log "⚠️ OpenConnect failed. Falling back to openfortivpn..." "warn"
            cat <<EOF > /etc/openfortivpn/config
host = ${VPN_HOST}
port = ${VPN_PORT:-443}
username = ${VPN_USER}
password = ${VPN_PASS}
${VPN_TRUSTED_CERT:+trusted-cert = $VPN_TRUSTED_CERT}
set-dns = 1
pppd-use-peerdns = 1
EOF
            apply_smart_routing &
            openfortivpn -c /etc/openfortivpn/config
            EXIT_STATUS=$?
        fi
    fi

    EXIT_CODE=$EXIT_STATUS
    log "⚠️ VPN Disconnected (Code: $EXIT_CODE). Cleaning up before reconnect..." "warn"
    
    # --- Self-Healing: If connection failed and we used a cookie, it might be stale ---
    if [ "$EXIT_CODE" -ne 0 ] && [ -n "$COOKIE" ] && [ -n "$DATABASE_URL" ]; then
        log "🧐 VPN failed while using a cookie. Checking if it should be cleared..." "info"
        # If openfortivpn/openconnect exits with error, we assume the cookie might be dead.
        # We clear it from DB so the next loop can try Password Mode or wait for Auto-Fetch.
        psql "$DATABASE_URL" -c "DELETE FROM system_settings WHERE key='vpn_cookie'" > /dev/null 2>&1
        log "🗑️  Stale cookie cleared from database to allow fallback/refresh." "info"
        unset VPN_COOKIE
    fi
    
    # --- Cleanup stale ppp0 interface to prevent 'Interface ppp0: Exist' on reconnect ---
    if ip link show ppp0 > /dev/null 2>&1; then
        log "🧹 Removing stale ppp0 interface..." "info"
        ip link set ppp0 down 2>/dev/null || true
        ip link delete ppp0 2>/dev/null || true
        sleep 1
    fi
    
    log "🔄 Reconnecting in 30 seconds..." "info"
    sleep 30
done

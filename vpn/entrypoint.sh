#!/bin/sh

# Base config
mkdir -p /etc/openfortivpn

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
    echo "📌 Mapping fasih-db -> $DB_IP in /etc/hosts"
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
    echo "📌 Mapping fasih-nexus-s3 -> $S3_IP in /etc/hosts"
    echo "$S3_IP fasih-nexus-s3" >> /etc/hosts
    echo "$S3_IP s3" >> /etc/hosts
fi

# 📉 Set eth0 MTU to 900 to prevent fragmentation on BPS network
echo "📉 Setting eth0 MTU to 900..."
ip link set eth0 mtu 900 2>/dev/null || true

GATEWAY_IP=$(ip route | grep default | awk '{print $3}')

# 🛠️ DYNAMIC FIX: Ensure internal Docker network stays on eth0
# We detect the actual subnet of eth0 to avoid hardcoding 172.16.0.0/12
# which might change in production environments like Coolify.
LOCAL_SUBNET=$(ip route show dev eth0 | grep "proto kernel" | awk '{print $1}')
if [ -n "$GATEWAY_IP" ] && [ -n "$LOCAL_SUBNET" ]; then
    echo "🛣️  Pinning local Docker network ($LOCAL_SUBNET) to eth0 via $GATEWAY_IP"
    ip route add "$LOCAL_SUBNET" dev eth0 via "$GATEWAY_IP" 2>/dev/null || true
fi
# Helper function to handle graceful shutdown
cleanup() {
    echo "🛑 Caught termination signal! Shutting down..."
    kill $(jobs -p) 2>/dev/null
    exit 0
}

trap cleanup INT TERM

# Background Watcher: Monitors DB for cookie changes and triggers restart
monitor_cookie_changes() {
    LAST_COOKIE=""
    while true; do
        sleep 10
        if [ -n "$DATABASE_URL" ] && [ -n "$VPN_PID" ]; then
            CURRENT_DB_COOKIE=$(psql "$DATABASE_URL" -t -A -c "SELECT value FROM system_settings WHERE key='vpn_cookie'" 2>/dev/null)
            if [ -n "$CURRENT_DB_COOKIE" ] && [ "$CURRENT_DB_COOKIE" != "$LAST_COOKIE" ]; then
                if [ -n "$LAST_COOKIE" ]; then
                    echo "🔄 DB Cookie changed! Triggering organic VPN reconnect..."
                    # Check if VPN_PID is actually running before killing
                    if [ -n "$VPN_PID" ] && kill -0 "$VPN_PID" 2>/dev/null; then
                        kill "$VPN_PID" 2>/dev/null
                    fi
                fi
                LAST_COOKIE="$CURRENT_DB_COOKIE"
            fi
        fi
    done
}

monitor_cookie_changes &

# SMART Route Enforcement Helper
apply_smart_routing() {
    echo "⏳ Waiting for interface tun0 or ppp0 to apply Smart Routing..."
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
                echo "✅ Interface $VPN_IF is fully UP. Applying route fixes..."
                break
            fi
            sleep 1
        done
        
        # Resolve target and force route
        TARGET_DOMAIN="fasih-sm.bps.go.id"
        echo "🔍 Resolving $TARGET_DOMAIN..."
        
        TARGET_IP=""
        for j in 1 2 3 4 5; do
            TARGET_IP=$(getent hosts "$TARGET_DOMAIN" | awk 'NR==1 {print $1}')
            [ -n "$TARGET_IP" ] && break
            sleep 2
        done
        
        if [ -n "$TARGET_IP" ]; then
            echo "📍 Site $TARGET_DOMAIN resolved to $TARGET_IP"
            
            grep -v "$TARGET_DOMAIN" /etc/hosts > /tmp/hosts && cat /tmp/hosts > /etc/hosts
            echo "$TARGET_IP $TARGET_DOMAIN" >> /etc/hosts
            echo "📌 Pinned $TARGET_DOMAIN -> $TARGET_IP in /etc/hosts"

            echo "🔌 Prioritizing Docker DNS and injecting BPS Nameservers..."
            echo -e "nameserver 127.0.0.11\nnameserver 10.10.11.11\nnameserver 10.10.11.12\n$(grep -vE '127.0.0.11|10.10.11.11|10.10.11.12' /etc/resolv.conf)" > /etc/resolv.conf
            
            if ! ip route get "$TARGET_IP" 2>/dev/null | grep -q "dev $VPN_IF"; then
                echo "🛠️  Forcing route for $TARGET_IP via $VPN_IF..."
                ip route add "$TARGET_IP"/32 dev "$VPN_IF" 2>/dev/null || true
            fi

            echo "🌐 Routing BPS DNS servers via $VPN_IF..."
            ip route add 172.16.2.2/32 dev "$VPN_IF" 2>/dev/null || true
            ip route add 172.16.2.3/32 dev "$VPN_IF" 2>/dev/null || true
            ip route add 10.0.0.0/8 dev "$VPN_IF" 2>/dev/null || true
            
            echo "📉 Setting $VPN_IF MTU to 900..."
            ip link set dev "$VPN_IF" mtu 900 || true
            
            echo "✅ BPS Routing updated."
        else
            echo "⚠️  Could not resolve $TARGET_DOMAIN (DNS Timeout)."
        fi
        return 0
    fi
    echo "❌ No VPN interface appeared. Skipping Smart Routing."
}

echo "🚀 Starting VPN Architecture (Self-Healing Enabled)..."

while true; do
    # --- Cleanup stale ppp0 interface to prevent 'Interface ppp0: Exist' on reconnect ---
    if ip link show ppp0 > /dev/null 2>&1; then
        echo "🧹 Removing stale ppp0 interface..."
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
            echo "🔑 Fresh cookie loaded from database (Length: ${#COOKIE})"
        else
            echo "⏳ No cookie found in database. Triggering RPA auto-fetch via internet..."
            # RPA shares the same network namespace, so we use 127.0.0.1
            # We use a retry loop because RPA might still be starting its web server.
            for attempt in $(seq 1 6); do
                RESP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "http://127.0.0.1:8000/vpn/auto-fetch" \
                    -H "Content-Type: application/json" \
                    -d "{\"sso_username\":\"$VPN_USER\", \"sso_password\":\"$VPN_PASS\"}")
                
                if [ "$RESP" = "200" ]; then
                    echo "   ✅ RPA auto-fetch triggered successfully."
                    break
                fi
                echo "   ⚠️ RPA not ready yet ($attempt/6, code: $RESP), retrying in 10s..."
                sleep 10
            done
        fi
    fi

    # ONLY fallback to env var if DB is not available (Legacy mode)
    if [ -z "$DATABASE_URL" ] && [ -n "${VPN_COOKIE}" ]; then
        COOKIE="${VPN_COOKIE}"
        echo "🔑 Cookie loaded from env var (Legacy Fallback)"
    fi

    if [ -n "$COOKIE" ]; then
        VAL=$(echo "$COOKIE" | grep -o 'SVPNCOOKIE=[^;]*' | sed 's/^SVPNCOOKIE=//')
        if [ -z "$VAL" ]; then VAL="$COOKIE"; fi

        echo "🔗 Connecting with cookie (OpenConnect Mode)..."
        echo "🚀 Using DTLS + Android Spoofing for 'Lightning Fast' performance"
        
        # 📱 Android Spoofing for 'Lightning Fast' performance
        ANDROID_UA="Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36 FortiClient/7.2.4"
        
        # We try OpenConnect first as it supports DTLS
        openconnect --protocol=fortinet \
            "${VPN_HOST}:${VPN_PORT:-443}" \
            --cookie="SVPNCOOKIE=$VAL" \
            --useragent="$ANDROID_UA" \
            --os=android \
            --reconnect-timeout 60 \
            --passwd-on-stdin \
            --servercert "pin-sha256:u5HMq39pIYRefHyrvy+wZgxcW/a+Oa5N0x65brFLNsA=" \
            --background \
            --pid-file=/tmp/vpn.pid <<EOF
$VAL
EOF
        
        # Wait for the background process to start
        sleep 2
        if [ -f /tmp/vpn.pid ]; then
            VPN_PID=$(cat /tmp/vpn.pid)
            apply_smart_routing
            # 🛡️ Robust background wait: wait $PID only works for direct children.
            # Since openconnect daemonizes, we must use a kill -0 loop.
            echo "🛡️ Monitoring VPN PID $VPN_PID..."
            while kill -0 "$VPN_PID" 2>/dev/null; do
                sleep 5
            done
        else
            echo "⚠️ OpenConnect failed to start (PID file missing). Falling back to openfortivpn..."
            openfortivpn "${VPN_HOST}:${VPN_PORT:-443}" \
                --cookie="$VAL" \
                ${VPN_TRUSTED_CERT:+--trusted-cert "$VPN_TRUSTED_CERT"} \
                --set-dns=1 \
                --pppd-use-peerdns=1 &
            VPN_PID=$!
            apply_smart_routing
            wait $VPN_PID
        fi
    else
        echo "👤 Using Username/Password Mode (OpenConnect)..."
        # 📱 Android Spoofing for Password Mode
        ANDROID_UA="Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36 FortiClient/7.2.4"
        
        openconnect --protocol=fortinet \
            "${VPN_HOST}:${VPN_PORT:-443}" \
            -u "$VPN_USER" \
            --useragent="$ANDROID_UA" \
            --os=android \
            --passwd-on-stdin \
            --servercert "pin-sha256:u5HMq39pIYRefHyrvy+wZgxcW/a+Oa5N0x65brFLNsA=" \
            --background \
            --pid-file=/tmp/vpn.pid <<EOF
$VPN_PASS
EOF
            
        sleep 5 
        if [ -f /tmp/vpn.pid ] && kill -0 $(cat /tmp/vpn.pid) 2>/dev/null; then
            VPN_PID=$(cat /tmp/vpn.pid)
            apply_smart_routing
            wait $VPN_PID
        else
            echo "⚠️ OpenConnect failed to stay alive. Falling back to openfortivpn..."
            # ... (rest of fallback)
            cat <<EOF > /etc/openfortivpn/config
host = ${VPN_HOST}
port = ${VPN_PORT:-443}
username = ${VPN_USER}
password = ${VPN_PASS}
${VPN_TRUSTED_CERT:+trusted-cert = $VPN_TRUSTED_CERT}
set-dns = 1
pppd-use-peerdns = 1
EOF
            openfortivpn -c /etc/openfortivpn/config &
            VPN_PID=$!
            apply_smart_routing
            wait $VPN_PID
        fi
        echo "⚠️ VPN connection closed."
        VPN_PID=""
    fi

    EXIT_CODE=$?
    echo "⚠️ VPN Disconnected (Code: $EXIT_CODE). Cleaning up before reconnect..."
    
    # --- Self-Healing: If connection failed and we used a cookie, it might be stale ---
    if [ "$EXIT_CODE" -ne 0 ] && [ -n "$COOKIE" ] && [ -n "$DATABASE_URL" ]; then
        echo "🧐 VPN failed while using a cookie. Checking if it should be cleared..."
        # If openfortivpn exits with error, we assume the cookie might be dead.
        # We clear it from DB so the next loop can try Password Mode or wait for Auto-Fetch.
        psql "$DATABASE_URL" -c "DELETE FROM system_settings WHERE key='vpn_cookie'" > /dev/null 2>&1
        echo "🗑️  Stale cookie cleared from database to allow fallback/refresh."
        unset VPN_COOKIE
    fi
    
    # --- Cleanup stale ppp0 interface to prevent 'Interface ppp0: Exist' on reconnect ---
    if ip link show ppp0 > /dev/null 2>&1; then
        echo "🧹 Removing stale ppp0 interface..."
        ip link set ppp0 down 2>/dev/null || true
        ip link delete ppp0 2>/dev/null || true
        sleep 1
    fi
    
    echo "🔄 Reconnecting in 30 seconds..."
    sleep 30
done

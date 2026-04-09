#!/bin/sh

# Base config
mkdir -p /etc/openfortivpn

# Inject postgres IP into /etc/hosts so it survives openfortivpn overwriting /etc/resolv.conf
# This allows the RPA container (which shares the vpn network) to still reach the database
POSTGRES_IP=$(getent hosts postgres | awk '{print $1}')
if [ -n "$POSTGRES_IP" ]; then
    echo "📌 Mapping postgres -> $POSTGRES_IP in /etc/hosts"
    echo "$POSTGRES_IP postgres" >> /etc/hosts
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
                    kill "$VPN_PID" 2>/dev/null
                fi
                LAST_COOKIE="$CURRENT_DB_COOKIE"
            fi
        fi
    done
}

monitor_cookie_changes &

# SMART Route Enforcement Helper
apply_smart_routing() {
    echo "⏳ Waiting for interface ppp0 to apply Smart Routing..."
    for i in $(seq 1 30); do
        if [ -d "/sys/class/net/ppp0" ]; then
            # Wait for ppp0 to get an IP address so the device is truly UP for routing
            if ip addr show ppp0 2>/dev/null | grep -q "inet "; then
                echo "✅ Interface ppp0 is fully UP (has IP). Applying route fixes..."
                
                # Resolve target and force route
                TARGET_DOMAIN="fasih-sm.bps.go.id"
                echo "🔍 Resolving $TARGET_DOMAIN..."
                
                # DNS might take a few seconds to stabilize after ppp0 is up
                TARGET_IP=""
                for j in 1 2 3 4 5; do
                    TARGET_IP=$(getent hosts "$TARGET_DOMAIN" | awk '{print $1}')
                    [ -n "$TARGET_IP" ] && break
                    sleep 2
                done
                
                if [ -n "$TARGET_IP" ]; then
                    echo "📍 Site $TARGET_DOMAIN resolved to $TARGET_IP"
                    
                    # Pin in /etc/hosts so DNS outages during reconnects don't break resolution
                    # Safe technique for Docker bind mounts
                    grep -v "$TARGET_DOMAIN" /etc/hosts > /tmp/hosts && cat /tmp/hosts > /etc/hosts
                    echo "$TARGET_IP $TARGET_DOMAIN" >> /etc/hosts
                    echo "📌 Pinned $TARGET_DOMAIN -> $TARGET_IP in /etc/hosts"
                    
                    # Also pin sso.bps.go.id for login flows
                    SSO_IP=$(getent hosts "sso.bps.go.id" | awk '{print $1}')
                    if [ -n "$SSO_IP" ]; then
                        grep -v "sso.bps.go.id" /etc/hosts > /tmp/hosts && cat /tmp/hosts > /etc/hosts
                        echo "$SSO_IP sso.bps.go.id" >> /etc/hosts
                        echo "📌 Pinned sso.bps.go.id -> $SSO_IP in /etc/hosts"
                    fi
                    
                    # Check if already routed via ppp0
                    if ! ip route get "$TARGET_IP" 2>/dev/null | grep -q "dev ppp0"; then
                        echo "🛠️  Forcing route for $TARGET_IP via ppp0 (Fixing missing BPS advertisement)..."
                        # Extra retry for route add just in case
                        for k in 1 2 3; do
                            ip route add "$TARGET_IP"/32 dev ppp0 2>/dev/null && break
                            echo "⏳ Retrying route add..."
                            sleep 1
                        done
                    else
                        echo "👌 Route to $TARGET_IP already properly set via ppp0."
                    fi
                else
                    echo "⚠️  Could not resolve $TARGET_DOMAIN inside VPN (DNS Timeout)."
                fi
                return 0
            fi
        fi
        sleep 1
    done
    echo "❌ Interface ppp0 never appeared. Skipping Smart Routing."
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



    # Priority: database > env var
    COOKIE=""
    
    # Try reading cookie from PostgreSQL
    if [ -n "$DATABASE_URL" ]; then
        DB_COOKIE=$(psql "$DATABASE_URL" -t -A -c "SELECT value FROM system_settings WHERE key='vpn_cookie'" 2>/dev/null)
        if [ -n "$DB_COOKIE" ]; then
            COOKIE="$DB_COOKIE"
            echo "🔑 Cookie loaded from database (Length: ${#COOKIE})"
        fi
    fi

    # Fallback to env var
    if [ -z "$COOKIE" ] && [ -n "${VPN_COOKIE}" ]; then
        COOKIE="${VPN_COOKIE}"
        echo "🔑 Cookie loaded from env var"
    fi

    if [ -n "$COOKIE" ]; then
        VAL=$(echo "$COOKIE" | grep -o 'SVPNCOOKIE=[^;]*' | sed 's/^SVPNCOOKIE=//')
        if [ -z "$VAL" ]; then VAL="$COOKIE"; fi

        echo "🔗 Connecting with cookie..."
        # Run VPN
        echo "⛓️ Establishing tunnel (Cookie Mode)..."
        openfortivpn ${VPN_HOST}:${VPN_PORT:-443} \
            --cookie="$VAL" \
            ${VPN_TRUSTED_CERT:+--trusted-cert "$VPN_TRUSTED_CERT"} \
            --set-dns=1 \
            --pppd-use-peerdns=1 &
        VPN_PID=$!
        apply_smart_routing &
        wait $VPN_PID
    else
        echo "👤 Using Username/Password for connection..."
        cat <<EOF > /etc/openfortivpn/config
host = ${VPN_HOST}
port = ${VPN_PORT:-443}
username = ${VPN_USER}
password = ${VPN_PASS}
${VPN_TRUSTED_CERT:+trusted-cert = $VPN_TRUSTED_CERT}
set-dns = 1
pppd-use-peerdns = 1
EOF
        # Run VPN
        echo "⛓️ Establishing tunnel (Config Mode)..."
        openfortivpn -c /etc/openfortivpn/config &
        VPN_PID=$!
        apply_smart_routing &
        wait $VPN_PID
        echo "⚠️ VPN connection closed."
        VPN_PID=""
    fi

    EXIT_CODE=$?
    echo "⚠️ VPN Disconnected (Code: $EXIT_CODE). Cleaning up before reconnect..."
    
    # --- Cleanup stale ppp0 interface to prevent 'Interface ppp0: Exist' on reconnect ---
    if ip link show ppp0 > /dev/null 2>&1; then
        echo "🧹 Removing stale ppp0 interface..."
        ip link set ppp0 down 2>/dev/null || true
        ip link delete ppp0 2>/dev/null || true
        sleep 1
    fi
    
    echo "🔄 Reconnecting in 5 seconds..."
    sleep 5
done

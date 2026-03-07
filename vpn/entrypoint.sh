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

echo "🚀 Starting VPN to ${VPN_HOST}..."

while true; do
    # Priority: database > env var
    COOKIE=""

    # Try reading cookie from PostgreSQL
    if [ -n "$DATABASE_URL" ]; then
        DB_COOKIE=$(psql "$DATABASE_URL" -t -A -c "SELECT value FROM system_settings WHERE key='vpn_cookie'" 2>/dev/null)
        if [ -n "$DB_COOKIE" ]; then
            COOKIE="$DB_COOKIE"
            echo "🔑 Cookie loaded from database"
        fi
    fi

    # Fallback to env var
    if [ -z "$COOKIE" ] && [ -n "${VPN_COOKIE}" ]; then
        COOKIE="${VPN_COOKIE}"
        echo "🔑 Cookie loaded from env var"
    fi

    if [ -n "$COOKIE" ]; then
        # Extract the value after SVPNCOOKIE= reliably using regex (handles arbitrary positions and spacing)
        VAL=$(echo "$COOKIE" | grep -o 'SVPNCOOKIE=[^;]*' | sed 's/^SVPNCOOKIE=//')
        
        if [ -z "$VAL" ]; then
            # Fallback if the user just pasted the raw SVPNCOOKIE value without the key=
            VAL="$COOKIE"
        fi

        echo "🔗 Connecting with cookie (length: ${#VAL})..."
        openfortivpn ${VPN_HOST}:${VPN_PORT:-443} \
            --cookie="$VAL" \
            ${VPN_TRUSTED_CERT:+--trusted-cert "$VPN_TRUSTED_CERT"} \
            --set-dns=1 \
            --pppd-use-peerdns=1
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
        openfortivpn -c /etc/openfortivpn/config
    fi

    EXIT_CODE=$?
    echo "⚠️ VPN Disconnected (Code: $EXIT_CODE). Reconnecting in 5 seconds..."
    sleep 5
done

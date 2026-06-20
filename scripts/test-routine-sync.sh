#!/bin/bash
# Set working directory to project root
cd "$(dirname "$0")/.."
# test-routine-sync.sh
# Script to verify the Routine Sync Scheduler functionality.

DB_CONTAINER="fasih-nexus-db"
DB_USER="fasih"
DB_NAME="fasih_dashboard"

echo "🚀 Starting Routine Sync Test..."

# 1. Rebuild and Restart RPA to apply changes
echo "🔄 Rebuilding RPA service..."
docker compose up -d --build rpa

# 2. Wait for VPN to stabilize
echo "⏳ Waiting for VPN to stabilize..."
MAX_RETRIES=20
for i in $(seq 1 $MAX_RETRIES); do
    if docker logs fasih-nexus-vpn 2>&1 | grep -q "Connected to gateway"; then
        echo "✅ VPN appears to be connected."
        # Extra wait for DNS/Routing
        sleep 10
        break
    fi
    echo "   waiting for VPN... ($i/$MAX_RETRIES)"
    sleep 5
done

# 3. Pick a survey and set interval to 1 minute
SURVEY_ID=$(docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -t -A -c "SELECT id FROM survey_configs WHERE is_active = true LIMIT 1;")
SURVEY_NAME=$(docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -t -A -c "SELECT survey_name FROM survey_configs WHERE id = '$SURVEY_ID';")

if [ -z "$SURVEY_ID" ]; then
    echo "❌ No active survey found to test."
    exit 1
fi

echo "📋 Testing with survey: $SURVEY_NAME ($SURVEY_ID)"
echo "⏱️ Setting interval to 1 minute..."
docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "UPDATE survey_configs SET interval_minutes = 1 WHERE id = '$SURVEY_ID';"

# 4. Get latest sync log ID before waiting
LAST_LOG_ID=$(docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -t -A -c "SELECT MAX(id) FROM sync_logs WHERE survey_config_id = '$SURVEY_ID';")
echo "🔍 Last Log ID before test: ${LAST_LOG_ID:-None}"

# 5. Wait for the scheduler (Scheduler waits 30s on startup + check every 60s)
echo "⏳ Waiting 120 seconds for scheduler to trigger..."
sleep 120

# 6. Check if a new log appeared
NEW_LOG=$(docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -t -A -c "SELECT id, status, notes FROM sync_logs WHERE survey_config_id = '$SURVEY_ID' AND id > '${LAST_LOG_ID:-0}' AND notes LIKE '%Automated routine sync%' ORDER BY id DESC LIMIT 1;")

if [ -n "$NEW_LOG" ]; then
    echo "✅ SUCCESS! Routine sync triggered."
    echo "📄 Log Detail: $NEW_LOG"
else
    echo "❌ FAILURE! Routine sync not triggered."
    echo "📝 Checking RPA logs for errors..."
    docker logs fasih-nexus-rpa | grep -i "scheduler" | tail -n 20
fi

# 6. Cleanup: Revert interval
echo "🧹 Cleaning up: Reverting interval to 30 minutes..."
docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "UPDATE survey_configs SET interval_minutes = 30 WHERE id = '$SURVEY_ID';"

echo "🏁 Test finished."

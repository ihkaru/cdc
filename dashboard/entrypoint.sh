#!/bin/bash
set -e

echo "🚀 Starting Dashboard Container Entrypoint..."

# 1. Wait for Postgres to be ready (optional but good practice)
# Although depends_on with healthcheck is used, sometimes the app is too fast.
# We'll rely on the existing drizzle-kit push which will fail and retry if DB is not ready.

# 2. Run Database Migrations / Sync Schema
echo "🩺 Running Self-Healing Migration Check..."
# This handles the text -> uuid migration error automatically in production
psql "$DATABASE_URL" -c "
DO \$\$ 
BEGIN 
  IF EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'survey_configs' AND column_name = 'id' AND data_type = 'text'
  ) THEN 
    RAISE NOTICE 'Legacy text ID detected. Performing automated conversion to UUID...';
    ALTER TABLE assignments DROP CONSTRAINT IF EXISTS assignments_survey_config_id_survey_configs_id_fk;
    ALTER TABLE sync_logs DROP CONSTRAINT IF EXISTS sync_logs_survey_config_id_survey_configs_id_fk;
    ALTER TABLE survey_configs ALTER COLUMN id TYPE uuid USING id::uuid;
    ALTER TABLE assignments ALTER COLUMN survey_config_id TYPE uuid USING survey_config_id::uuid;
    ALTER TABLE sync_logs ALTER COLUMN survey_config_id TYPE uuid USING survey_config_id::uuid;
    RAISE NOTICE 'Automated conversion completed successfully.';
  END IF;
END \$\$;
" || echo "   ⚠️ Self-healing check skipped (table may not exist yet or connection failed)."

echo "📦 Syncing database schema (drizzle-kit push)..."
# We use push for simplicity in this dev/stage environment.
# In strict production, we would use 'migrate'.
SYNC_SUCCESS=false
for i in {1..10}; do
  if bunx drizzle-kit push; then
    SYNC_SUCCESS=true
    break
  fi
  echo "   ⏳ DB not ready or sync failed, retrying ($i/10)..."
  sleep 5
done

if [ "$SYNC_SUCCESS" = false ]; then
  echo "❌ Database schema sync failed after 10 attempts. Exiting."
  exit 1
fi

# 3. Check if Seeding is needed
# We can check if a flag file exists or just run it (the seeder is idempotent).
echo "🌱 Running employee seeder..."
bun run server/db/seed-pegawai.ts

# 4. Start the main application
echo "🏁 Starting Elysia server..."
exec bun run server/index.ts

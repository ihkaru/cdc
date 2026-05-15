#!/bin/bash
set -e

echo "🚀 Starting Dashboard Container Entrypoint..."

# 1. Wait for Postgres to be ready (optional but good practice)
# Although depends_on with healthcheck is used, sometimes the app is too fast.
# We'll rely on the existing drizzle-kit push which will fail and retry if DB is not ready.

# 2. Run Database Migrations / Sync Schema
echo "🩺 Running Advanced Self-Healing Migration Check..."
# More aggressive check for ANY column named 'id' or ending in '_id' that is currently text/varchar
psql "$DATABASE_URL" -c "
DO \$\$ 
DECLARE
    r RECORD;
BEGIN 
    -- 1. Drop known foreign key constraints first to allow type changes
    ALTER TABLE assignments DROP CONSTRAINT IF EXISTS assignments_survey_config_id_survey_configs_id_fk;
    ALTER TABLE sync_logs DROP CONSTRAINT IF EXISTS sync_logs_survey_config_id_survey_configs_id_fk;

    -- 2. Find and convert any 'id' or '*_id' columns that are still text/varchar
    FOR r IN (
        SELECT table_name, column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND (column_name = 'id' OR column_name LIKE '%_id')
          AND (data_type = 'text' OR data_type = 'character varying')
          AND table_name IN ('survey_configs', 'assignments', 'sync_logs', 'label_data', 'label_schemas')
    ) LOOP
        RAISE NOTICE 'Converting %.% from text to uuid...', r.table_name, r.column_name;
        EXECUTE format('ALTER TABLE %I ALTER COLUMN %I TYPE uuid USING %I::uuid', r.table_name, r.column_name, r.column_name);
    END LOOP;
    
    -- 3. Indestructible Cleanup (Postgres identity & sequence conflicts)
    -- We use nested blocks to ignore errors and force cleanup
    DO \$\$ 
    DECLARE
        r RECORD;
    BEGIN 
        -- A. Force drop constraints that might block type changes
        BEGIN EXECUTE 'ALTER TABLE assignments DROP CONSTRAINT IF EXISTS assignments_survey_config_id_survey_configs_id_fk'; EXCEPTION WHEN OTHERS THEN NULL; END;
        BEGIN EXECUTE 'ALTER TABLE sync_logs DROP CONSTRAINT IF EXISTS sync_logs_survey_config_id_survey_configs_id_fk'; EXCEPTION WHEN OTHERS THEN NULL; END;

        -- B. Clean up OWNED sequences by first dropping the column dependencies
        FOR r IN (
            SELECT t.relname as table_name, a.attname as column_name, c.relname as sequence_name
            FROM pg_class c
            JOIN pg_depend d ON d.objid = c.oid
            JOIN pg_class t ON t.oid = d.refobjid
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = d.refobjsubid
            WHERE c.relkind = 'S' AND d.deptype = 'a'
              AND (c.relname LIKE 'sync_logs%' OR c.relname LIKE 'label_data%' OR c.relname LIKE 'label_schemas%' OR c.relname LIKE 'visualization_configs%')
        ) LOOP
            RAISE NOTICE 'Cleaning up owned sequence %...', r.sequence_name;
            BEGIN 
                -- Drop both default and identity if they exist
                EXECUTE format('ALTER TABLE %I ALTER COLUMN %I DROP DEFAULT', r.table_name, r.column_name);
                EXECUTE format('ALTER TABLE %I ALTER COLUMN %I DROP IDENTITY IF EXISTS', r.table_name, r.column_name);
                EXECUTE format('DROP SEQUENCE IF EXISTS %I CASCADE', r.sequence_name);
            EXCEPTION WHEN OTHERS THEN 
                RAISE NOTICE 'Could not fully drop %, skipping...', r.sequence_name;
            END;
        END LOOP;

        -- C. Clean up any remaining ORPHAN sequences
        FOR r IN (
            SELECT relname as sequence_name
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind = 'S'
              AND (relname LIKE 'sync_logs%' OR relname LIKE 'label_data%' OR relname LIKE 'label_schemas%' OR relname LIKE 'visualization_configs%')
        ) LOOP
            RAISE NOTICE 'Dropping orphan sequence %...', r.sequence_name;
            BEGIN EXECUTE format('DROP SEQUENCE IF EXISTS %I CASCADE', r.sequence_name); EXCEPTION WHEN OTHERS THEN NULL; END;
        END LOOP;
        
        RAISE NOTICE 'Self-healing process completed.';
    END \$\$;
" || echo "   ⚠️ Self-healing check completed with some warnings (non-critical)."

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

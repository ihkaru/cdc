#!/bin/bash
set -e

echo "🚀 Starting Dashboard Container Entrypoint..."

# 1. Wait for Postgres to be ready (optional but good practice)
# Although depends_on with healthcheck is used, sometimes the app is too fast.
# We'll rely on the existing drizzle-kit push which will fail and retry if DB is not ready.

# 2. Run Database Migrations / Sync Schema
echo "🩺 Running Universal Self-Healing Migration Check..."
# Blok PL/pgSQL yang lebih luas untuk menangani berbagai potensi konflik skema
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "
DO \$\$ 
DECLARE
    r RECORD;
BEGIN 
    SET statement_timeout = '60000'; -- 60 seconds
    RAISE NOTICE 'Starting universal database hardening...';

    -- A. Drop SEMUA foreign key constraints sementara (Akan dibuat ulang oleh Drizzle)
    -- Ini mencegah error 'cannot alter type because of dependency'
    FOR r IN (
        SELECT tc.table_name, tc.constraint_name
        FROM information_schema.table_constraints AS tc 
        JOIN information_schema.key_column_usage AS kcu ON tc.constraint_name = kcu.constraint_name
        WHERE constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
    ) LOOP
        EXECUTE format('ALTER TABLE %I DROP CONSTRAINT IF EXISTS %I', r.table_name, r.constraint_name);
    END LOOP;

    -- B. Konversi otomatis kolom ID yang tertinggal sebagai TEXT ke UUID
    FOR r IN (
        SELECT table_name, column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND (column_name = 'id' OR column_name LIKE '%_id')
          AND (data_type = 'text' OR data_type = 'character varying')
    ) LOOP
        RAISE NOTICE 'Auto-repairing %.% from text to uuid...', r.table_name, r.column_name;
        BEGIN
            EXECUTE format('ALTER TABLE %I ALTER COLUMN %I TYPE uuid USING %I::uuid', r.table_name, r.column_name, r.column_name);
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'Could not convert %.%, skipping...', r.table_name, r.column_name;
        END;
    END LOOP;

    -- C. Bersihkan semua sequence yatim piatu yang sering bikin error 42P07
    FOR r IN (
        SELECT relname as sequence_name
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind = 'S'
    ) LOOP
        RAISE NOTICE 'Cleaning up sequence %...', r.sequence_name;
        BEGIN EXECUTE format('DROP SEQUENCE IF EXISTS %I CASCADE', r.sequence_name); EXCEPTION WHEN OTHERS THEN NULL; END;
    END LOOP;
    
    RAISE NOTICE 'Database hardening completed.';
END \$\$;
" || echo "   ⚠️ Hardening check completed with some skip/warnings."

echo "📦 Generating & Syncing database schema..."
SYNC_SUCCESS=false
for i in {1..5}; do
  # Kita jalankan push --force agar tidak berhenti saat ada peringatan (misal data loss)
  # Gunakan --accept-all jika versi drizzle mendukung, atau biarkan default push
  if bunx drizzle-kit push; then
    SYNC_SUCCESS=true
    break
  fi
  echo "   ⏳ DB not ready or sync failed, retrying ($i/5)..."
  sleep 5
done

if [ "$SYNC_SUCCESS" = false ]; then
  echo "❌ Database schema sync failed. Trying one last time with generate pass..."
  # Fallback: jika push gagal, coba generate migration dulu baru push (force)
  bunx drizzle-kit generate || true
  bunx drizzle-kit push --force && SYNC_SUCCESS=true
fi

# 3. Check if Seeding is needed
# We can check if a flag file exists or just run it (the seeder is idempotent).
echo "🌱 Running employee seeder..."
bun run server/db/seed-pegawai.ts

# 4. Start the main application
echo "🏁 Starting Elysia server..."
exec bun run server/index.ts

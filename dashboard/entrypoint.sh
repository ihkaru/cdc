#!/bin/bash
set -e

echo "🚀 Starting Dashboard Container Entrypoint..."

# 1. Wait for Postgres to be ready (optional but good practice)
# Although depends_on with healthcheck is used, sometimes the app is too fast.
# We'll rely on the existing drizzle-kit push which will fail and retry if DB is not ready.

# 2. Run Database Migrations / Sync Schema
echo "📦 Syncing database schema (drizzle-kit push)..."
# We use push for simplicity in this dev/stage environment.
# In strict production, we would use 'migrate'.
for i in {1..10}; do
  bunx drizzle-kit push && break || echo "   ⏳ DB not ready, retrying ($i/10)..." && sleep 5
done

# 3. Check if Seeding is needed
# We can check if a flag file exists or just run it (the seeder is idempotent).
echo "🌱 Running employee seeder..."
bun run server/db/seed-pegawai.ts

# 4. Start the main application
echo "🏁 Starting Elysia server..."
exec bun run server/index.ts

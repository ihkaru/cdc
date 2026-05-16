import { defineConfig } from "drizzle-kit";

export default defineConfig({
    schema: "./server/db/schema.ts",
    out: "./server/db/migrations",
    dialect: "postgresql",
    dbCredentials: {
        url: process.env.DATABASE_URL || "postgresql://fasih:changeme@127.0.0.1:5432/fasih_dashboard",
    },
});

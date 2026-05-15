import { betterAuth } from "better-auth";
import { drizzleAdapter } from "better-auth/adapters/drizzle";
import * as schema from "./db/schema";
import { db } from "./db";

export const auth = betterAuth({
    database: drizzleAdapter(db, {
        provider: "pg",
        schema: {
            ...schema,
            user: schema.users,
            session: schema.sessions,
            account: schema.accounts,
            verification: schema.verifications,
        }
    }),
    emailAndPassword: {
        enabled: true,
        autoSignIn: true,
        minPasswordLength: 3,
    },
    baseURL: (process.env.BETTER_AUTH_URL || "http://localhost:3000") + "/api/auth",
    // RBAC Configuration
    // For now, we will handle RBAC via custom middleware using the schema we built.
    secret: process.env.BETTER_AUTH_SECRET || "fallback-secret-for-dev-only",
    trustedOrigins: [process.env.PUBLIC_BASE_URL || "http://localhost:3000"],
    advanced: {
        cookiePrefix: "cdc_auth",
    }
});

import { betterAuth } from "better-auth";
import { drizzleAdapter } from "better-auth/adapters/drizzle";
import { db } from "./db";
import * as schema from "./db/schema";

export const auth = betterAuth({
	database: drizzleAdapter(db, {
		provider: "pg",
		schema: {
			...schema,
			user: schema.users,
			session: schema.sessions,
			account: schema.accounts,
			verification: schema.verifications,
		},
	}),
	emailAndPassword: {
		enabled: true,
		autoSignIn: true,
		minPasswordLength: 3,
	},
	baseURL: `${process.env.BETTER_AUTH_URL || "http://localhost:3000"}/api/auth`,
	secret: process.env.BETTER_AUTH_SECRET || "fallback-secret-for-dev-only",
	session: {
		// Extend session to 30 days to prevent frequent logouts.
		// Default is 7 days which can feel short during active development.
		expiresIn: 60 * 60 * 24 * 30, // 30 days in seconds
		updateAge: 60 * 60 * 24, // Refresh session if older than 1 day
		// Cache session in cookie to reduce DB round-trips on every request.
		cookieCache: {
			enabled: true,
			maxAge: 60 * 5, // 5 minutes cache — balances performance vs freshness
		},
	},
	trustedOrigins: (() => {
		const publicBase = process.env.PUBLIC_BASE_URL || "http://localhost:9000";
		const dynamicOrigins = [
			publicBase,
			publicBase.replace("127.0.0.1", "localhost"),
			publicBase.replace("localhost", "127.0.0.1"),
		];
		return [
			...dynamicOrigins,
			"http://127.0.0.1:3000",
			"http://localhost:3000",
			"http://127.0.0.1:9000",
			"http://localhost:9000",
			"http://127.0.0.1:9001",
			"http://localhost:9001",
			"http://127.0.0.1:9009",
			"http://localhost:9009",
			"http://127.0.0.1:9010",
			"http://localhost:9010",
			"http://127.0.0.1:9011",
			"http://localhost:9011",
		];
	})(),
	advanced: {
		cookiePrefix: "cdc_auth",
		// Explicitly set cookie options to ensure they persist across browser sessions.
		// sameSite: "lax" is safe for same-origin requests and avoids CSRF issues.
		// secure: false is required for local HTTP development (non-HTTPS).
		defaultCookieAttributes: {
			sameSite: "lax",
			secure: false,
			httpOnly: true,
			path: "/",
		},
	},
});

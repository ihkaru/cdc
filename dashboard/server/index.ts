import { cors } from "@elysiajs/cors";
import { staticPlugin } from "@elysiajs/static";
import { Elysia } from "elysia";
import { auth } from "./auth";
import { authMiddleware, getAuthContext } from "./middleware/auth";
import { tracingMiddleware } from "./middleware/tracing";
import { assignmentsRoutes } from "./routes/assignments";
import { labelsRoutes } from "./routes/labels";
import { logsRoutes } from "./routes/logs";
import { storageRoutes } from "./routes/storage";
import { surveysRoutes } from "./routes/surveys";
import { syncRoutes } from "./routes/sync";
import { syncStateRoutes } from "./routes/sync-state";
import { visualizationsRoutes } from "./routes/visualizations";
import { logger } from "./utils/logger";

// Best practice per dokumentasi resmi better-auth:
// Gunakan .mount(auth.handler) agar semua HTTP method (GET, POST, dll)
// ditangani langsung — tidak ada konflik wildcard dengan Elysia.
// Ref: https://www.better-auth.com/docs/integrations/elysia

const loginAttempts = new Map<string, { count: number; last: number }>();

const authRoutes = new Elysia({ prefix: "/api/auth" })
	.onBeforeHandle(({ path, request, set }) => {
		if (path === "/api/auth/sign-in/email") {
			const ip = request.headers.get("x-forwarded-for") || "unknown";
			const now = Date.now();
			const attempt = loginAttempts.get(ip) || { count: 0, last: 0 };

			if (now - attempt.last < 1000) {
				// 1s cooldown between attempts
				set.status = 429;
				return { error: "Too fast. Slow down." };
			}

			if (attempt.count > 10 && now - attempt.last < 60000) {
				// Max 10 attempts per minute
				set.status = 429;
				return { error: "Too many login attempts. Try again in a minute." };
			}

			loginAttempts.set(ip, {
				count: now - attempt.last > 60000 ? 1 : attempt.count + 1,
				last: now,
			});
		}
	})
	.post("/sign-up/email", ({ set }) => {
		// Block public registration for security hardening.
		// Users should be created via admin console or direct DB insert.
		set.status = 403;
		return { error: "Public registration is disabled for security hardening." };
	})
	.get("/me/roles", ({ user, roles }: any) => {
		if (!user) return { roles: [] };
		return { user, roles };
	})
	.get("/*", async (ctx) => {
		return auth.handler(ctx.request);
	})
	.all("/*", async (ctx) => {
		return auth.handler(ctx.request);
	});

const app = new Elysia()
	.use(tracingMiddleware)
	.use(
		cors({
			credentials: true,
			origin: process.env.PUBLIC_BASE_URL || "http://127.0.0.1:3000",
			allowedHeaders: ["Content-Type", "Authorization"],
			methods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
		}),
	)
	.get("/api/health", () => ({ status: "ok", timestamp: new Date().toISOString() }))
	.use(authRoutes)
	.derive(async ({ request }) => {
		return await getAuthContext(request);
	})
	// Global Security Gate & Headers
	.onBeforeHandle(({ path, user, set, request }: any) => {
		// 1. Security Headers
		set.headers["X-Frame-Options"] = "DENY";
		set.headers["X-Content-Type-Options"] = "nosniff";
		set.headers["X-XSS-Protection"] = "1; mode=block";
		set.headers["Referrer-Policy"] = "strict-origin-when-cross-origin";

		// 2. Global Auth Check (BOLA Prevention)
		const isPublicAuth = path.startsWith("/api/auth/") || path === "/api/health";
		// Status endpoints are public — they're read-only UI indicators with no sensitive data
		const isPublicStatus =
			path === "/api/surveys/sync/status" || path === "/api/surveys/vpn/status";
		const isProtectedApi = path.startsWith("/api/") || path.startsWith("/storage/");

		if (isProtectedApi && !isPublicAuth && !isPublicStatus && !user) {
			logger.warn(
				`[Security] 401 Unauthorized ${request.method} ${path} (User: ${user ? "found" : "null"})`,
			);
			set.status = 401;
			return { error: "Unauthorized" };
		}

		if (isProtectedApi) {
			logger.info(
				`[Security] 200 Authorized ${request.method} ${path} for user ${user?.email || "unknown"}`,
			);
		}
	})
	// Protected Routes
	.use(surveysRoutes)
	.use(assignmentsRoutes)
	.use(logsRoutes)
	.use(syncRoutes)
	.use(labelsRoutes)
	.use(visualizationsRoutes)
	.use(storageRoutes)
	.use(syncStateRoutes)
	// Serve static files and fallback to index.html for SPA
	.get("*", async ({ path, set }) => {
		// IMPORTANT: Never serve index.html for API routes
		if (path.startsWith("/api/")) {
			set.status = 404;
			return { error: "API route not found" };
		}

		const filePath = path === "/" ? "/index.html" : path;
		const file = Bun.file(`client/dist/spa${filePath}`);

		if (await file.exists()) return file;

		// Return index.html for non-existent routes (SPA fallback)
		// unless it looks like an asset that SHOULD have existed
		if (path.startsWith("/assets/") || path.includes(".")) {
			return new Response("Not Found", { status: 404 });
		}

		return Bun.file("client/dist/spa/index.html");
	})
	.listen(process.env.PORT || 3000);

logger.info(`🚀 Dashboard running at http://127.0.0.1:${app.server?.port}`);

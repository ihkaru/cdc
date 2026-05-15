import { Elysia } from "elysia";
import { cors } from "@elysiajs/cors";
import { staticPlugin } from "@elysiajs/static";
import { surveysRoutes } from "./routes/surveys";
import { assignmentsRoutes } from "./routes/assignments";
import { logsRoutes } from "./routes/logs";
import { syncRoutes } from "./routes/sync";
import { labelsRoutes } from "./routes/labels";
import { visualizationsRoutes } from "./routes/visualizations";
import { storageRoutes } from "./routes/storage";
import { syncStateRoutes } from "./routes/sync-state";

import { auth } from "./auth";
import { authMiddleware } from "./middleware/auth";

// Best practice per dokumentasi resmi better-auth:
// Gunakan .mount(auth.handler) agar semua HTTP method (GET, POST, dll)
// ditangani langsung — tidak ada konflik wildcard dengan Elysia.
// Ref: https://www.better-auth.com/docs/integrations/elysia

const loginAttempts = new Map<string, { count: number, last: number }>();

const authRoutes = new Elysia({ prefix: "/api/auth" })
    .onBeforeHandle(({ path, request, set }) => {
        if (path === "/api/auth/sign-in/email") {
            const ip = request.headers.get("x-forwarded-for") || "unknown";
            const now = Date.now();
            const attempt = loginAttempts.get(ip) || { count: 0, last: 0 };
            
            if (now - attempt.last < 1000) { // 1s cooldown between attempts
                set.status = 429;
                return { error: "Too fast. Slow down." };
            }
            
            if (attempt.count > 10 && now - attempt.last < 60000) { // Max 10 attempts per minute
                set.status = 429;
                return { error: "Too many login attempts. Try again in a minute." };
            }
            
            loginAttempts.set(ip, { 
                count: now - attempt.last > 60000 ? 1 : attempt.count + 1, 
                last: now 
            });
        }
    })
    .post("/sign-up/email", ({ set }) => {
        // Block public registration for security hardening.
        // Users should be created via admin console or direct DB insert.
        set.status = 403;
        return { error: "Public registration is disabled for security hardening." };
    })
    .get("/*", async (ctx) => {
        return auth.handler(ctx.request);
    })
    .all("/*", async (ctx) => {
        return auth.handler(ctx.request);
    });

const app = new Elysia()
    .use(cors({
        credentials: true,
        origin: process.env.PUBLIC_BASE_URL || "http://localhost:3000",
        allowedHeaders: ["Content-Type", "Authorization"],
        methods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    }))
    .use(authRoutes)
    .use(authMiddleware)
    // Global Security Gate & Headers
    .onBeforeHandle(({ path, user, set }: any) => {
        // 1. Security Headers
        set.headers["X-Frame-Options"] = "DENY";
        set.headers["X-Content-Type-Options"] = "nosniff";
        set.headers["X-XSS-Protection"] = "1; mode=block";
        set.headers["Referrer-Policy"] = "strict-origin-when-cross-origin";

        // 2. Global Auth Check (BOLA Prevention)
        const isPublicAuth = path.startsWith("/api/auth/");
        const isProtectedApi = path.startsWith("/api/") || path.startsWith("/storage/");

        if (isProtectedApi && !isPublicAuth && !user) {
            console.warn(`[Security] Unauthorized access attempt to ${path}`);
            set.status = 401;
            return { error: "Unauthorized" };
        }
    })
    // Auth info helper
    .get("/api/me/roles", ({ user, roles }) => {
        if (!user) return { roles: [] };
        return { user, roles };
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

console.log(`🚀 Dashboard running at http://localhost:${app.server?.port}`);

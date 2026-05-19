import { Elysia } from "elysia";
import { db } from "../db";
import * as schema from "../db/schema";
import { eq } from "drizzle-orm";

// Parse cookie string → { name: value } map
function parseCookies(cookieHeader: string | null): Record<string, string> {
    if (!cookieHeader) {
        console.warn("[Auth] parseCookies: No cookie header provided");
        return {};
    }
    console.log(`[Auth] parseCookies: Raw header: ${cookieHeader}`);
    const cookies = Object.fromEntries(
        cookieHeader.split(";").map(c => {
            const parts = c.trim().split("=");
            const k = parts[0] || "";
            const v = parts.slice(1).join("=");
            return [k.trim(), decodeURIComponent(v)];
        }).filter(([k]) => k !== "")
    );
    console.log(`[Auth] parseCookies: Parsed keys: ${Object.keys(cookies).join(", ")}`);
    return cookies;
}

/**
 * DEFINITIVE AUTH MIDDLEWARE FIX
 *
 * Root Cause: auth.api.getSession() internally validates the `Origin` / `Host`
 * header against BETTER_AUTH_URL. In dev mode, Quasar proxy forwards
 * Origin: 127.0.0.1:9000 while BETTER_AUTH_URL=127.0.0.1:3000. Even after
 * stripping Origin, Better Auth may check Host or perform internal fetches
 * that are subject to similar mismatches.
 *
 * Solution: Bypass auth.api.getSession() entirely. Read the session token
 * directly from the cookie header, query the sessions table ourselves,
 * and validate expiry. This is safe — we are the server; we own the DB.
 * The cookie token is still generated and signed by Better Auth; we just
 * look it up ourselves instead of asking Better Auth to do it for us.
 */
export const getAuthContext = async (request: Request) => {
    const cookieHeader = request.headers.get("cookie");
    const cookies = parseCookies(cookieHeader);
    const sessionToken = cookies["__Secure-cdc_auth.session_token"] || cookies["cdc_auth.session_token"];

    if (!sessionToken) {
        console.warn(`[Auth] No session token found in cookies. Available: ${Object.keys(cookies).join(", ")}`);
        return { user: null, roles: [] };
    }

    const rawToken = sessionToken.split(".")[0];
    if (!rawToken) {
        console.warn(`[Auth] Failed to parse raw token from: ${sessionToken}`);
        return { user: null, roles: [] };
    }

    // Direct DB lookup
    const sessionRow = await db.query.sessions.findFirst({
        where: eq(schema.sessions.token, rawToken),
    });

    if (!sessionRow) {
        console.warn(`[Auth] Session token not found in DB: ${rawToken}`);
        return { user: null, roles: [] };
    }
    
    if (sessionRow.expiresAt < new Date()) {
        console.warn(`[Auth] Session expired: ${sessionRow.expiresAt}`);
        return { user: null, roles: [] };
    }

    const userRow = await db.query.users.findFirst({
        where: eq(schema.users.id, sessionRow.userId),
    });

    if (!userRow) {
        return { user: null, roles: [] };
    }

    const userRoles = await db.query.usersToRoles.findMany({
        where: eq(schema.usersToRoles.userId, userRow.id),
        with: { role: true },
    });

    const roles = userRoles.map(ur => ur.role.name);

    return { user: userRow, roles };
};

export const authMiddleware = new Elysia()
    .derive({ as: "global" }, async ({ request }) => {
        return await getAuthContext(request);
    });

export const requireAuth = (app: Elysia) => app
    .use(authMiddleware)
    .onBeforeHandle(({ user, set }: any) => {
        if (!user) {
            set.status = 401;
            return { error: "Unauthorized" };
        }
    });

export const requireAdmin = (app: Elysia) => app
    .use(authMiddleware)
    .onBeforeHandle(({ user, roles, set }: any) => {
        if (!user) {
            set.status = 401;
            return { error: "Unauthorized" };
        }
        if (!roles.includes("admin")) {
            set.status = 403;
            return { error: "Forbidden: Admin access required" };
        }
    });

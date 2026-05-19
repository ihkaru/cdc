import { Elysia } from "elysia";
import { db } from "../db";
import { surveyConfigs, systemSettings } from "../db/schema";
import { eq } from "drizzle-orm";
import { createHash, createDecipheriv } from "crypto";
import { logger } from "../utils/logger";

const RPA_URL = process.env.RPA_URL || "http://vpn:8000";
const VPN_AUTH_URL = process.env.VPN_AUTH_URL || "http://vpn:8001";

function decryptPassword(ciphertext: string): string {
    const key = process.env.ENCRYPTION_KEY || "";
    if (!key) throw new Error("ENCRYPTION_KEY not set");
    const derivedKey = createHash("sha256").update(key).digest();
    const parts = ciphertext.split(":");
    const iv = Buffer.from(parts[0]!, "hex");
    const encrypted = Buffer.from(parts[1]!, "hex");
    const decipher = createDecipheriv("aes-256-cbc", derivedKey, iv);
    return decipher.update(encrypted).toString("utf8") + decipher.final("utf8");
}

import { requireAuth } from "../middleware/auth";
import { tracingMiddleware } from "../middleware/tracing";

const lastLookup = new Map<string, number>();

export const syncRoutes = new Elysia({ prefix: "/api/surveys" })
    .use(tracingMiddleware)
    .use(requireAuth)
    .post("/:id/sync", async (ctx: any) => {
        const { params, set } = ctx;
        const traceId = ctx.traceId || "no-trace";
        const traceparent = ctx.traceparent || "";
        const log = ctx.log || logger.child({ traceId });
        const [survey] = await db
            .select()
            .from(surveyConfigs)
            .where(eq(surveyConfigs.id, params.id));

        if (!survey) {
            set.status = 404;
            return { error: "Survey not found" };
        }

        // Guard: Check if RPA is already busy
        try {
            const statusResp = await fetch(`${RPA_URL}/status`, {
                headers: {
                    "X-Trace-ID": traceId,
                    "traceparent": traceparent
                },
                signal: AbortSignal.timeout(5000)
            });
            if (statusResp.ok) {
                const status = await statusResp.json() as any;
                if (status.is_running && status.active_job?.survey_config_id === survey.id) {
                    set.status = 409;
                    return { error: "Sync for this survey is already running in background." };
                }
            }
        } catch (e) {
            log.warn("RPA status check failed, proceeding anyway...", { error: String(e) });
        }

        // Decrypt password and send to RPA
        const password = decryptPassword(survey.ssoPasswordEncrypted);

        log.info("Triggering sync in RPA engine", { survey_id: survey.id, survey_name: survey.surveyName });

        const response = await fetch(`${RPA_URL}/sync`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Trace-ID": traceId,
                "traceparent": traceparent
            },
            body: JSON.stringify({
                survey_config_id: survey.id,
                survey_name: survey.surveyName,
                sso_username: survey.ssoUsername,
                sso_password: password,
                filter_provinsi: survey.filterProvinsi || "",
                filter_kabupaten: survey.filterKabupaten || "",
                filter_rotation: survey.filterRotation || "pengawas",
            }),
            signal: AbortSignal.timeout(10000)
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            set.status = response.status === 401 ? 401 : 400;
            log.error(`RPA sync trigger failed with status ${response.status}`, { error: err });
            return { error: (err as any).detail || `RPA responded with ${response.status}` };
        }

        return await response.json();
    })

    // Get RPA sync status
    .get("/sync/status", async (ctx: any) => {
        const traceId = ctx.traceId || "no-trace";
        const traceparent = ctx.traceparent || "";
        const log = ctx.log || logger.child({ traceId });
        try {
            const response = await fetch(`${RPA_URL}/status`, { 
                headers: {
                    "X-Trace-ID": traceId,
                    "traceparent": traceparent
                },
                signal: AbortSignal.timeout(15000) 
            });
            return await response.json();
        } catch (e: any) {
            log.error("Failed to fetch RPA sync status", { error: e.message, rpa_url: `${RPA_URL}/status` });
            return { is_running: false, error: `RPA service unavailable: ${e.message}` };
        }
    })

    // Get VPN connection status from RPA
    .get("/vpn/status", async (ctx: any) => {
        const traceId = ctx.traceId || "no-trace";
        const traceparent = ctx.traceparent || "";
        const log = ctx.log || logger.child({ traceId });
        try {
            const [checkRes, statusRes] = await Promise.all([
                fetch(`${RPA_URL}/vpn/check`, { 
                    headers: {
                        "X-Trace-ID": traceId,
                        "traceparent": traceparent
                    },
                    signal: AbortSignal.timeout(10000) 
                }),
                fetch(`${RPA_URL}/status`, { 
                    headers: {
                        "X-Trace-ID": traceId,
                        "traceparent": traceparent
                    },
                    signal: AbortSignal.timeout(5000) 
                })
            ]);
            
            const vpnInfo = await checkRes.json() as any;
            const rpaInfo = await statusRes.json() as any;

            return { 
                ...vpnInfo, 
                is_fetching: rpaInfo.is_vpn_fetching 
            };
        } catch (e: any) {
            log.error("Failed to fetch VPN status from RPA", { error: e.message, rpa_url: `${RPA_URL}/vpn/check` });
            return { connected: false, error: `RPA service unavailable: ${e.message}` };
        }
    })

    // Cancel a queued sync job
    .delete("/sync/:jobId", async (ctx: any) => {
        const { params } = ctx;
        const traceId = ctx.traceId || "no-trace";
        const traceparent = ctx.traceparent || "";
        const log = ctx.log || logger.child({ traceId });
        try {
            const response = await fetch(`${RPA_URL}/sync/${params.jobId}`, {
                method: "DELETE",
                headers: {
                    "X-Trace-ID": traceId,
                    "traceparent": traceparent
                }
            });
            return await response.json();
        } catch (e: any) {
            log.error("Failed to cancel queued sync job", { error: e.message, jobId: params.jobId });
            return { error: `RPA service unavailable: ${e.message}` };
        }
    })

    // Update VPN cookie (store in PostgreSQL for VPN container to read)
    .post("/vpn/cookie", async ({ body, set }) => {
        const { cookie } = body as { cookie: string };
        if (!cookie || cookie.trim().length < 10) {
            set.status = 400;
            return { error: "Cookie is empty or too short" };
        }
        await db
            .insert(systemSettings)
            .values({ key: "vpn_cookie", value: cookie.trim(), updatedAt: new Date() })
            .onConflictDoUpdate({
                target: systemSettings.key,
                set: { value: cookie.trim(), updatedAt: new Date() },
            });
        return { success: true, message: "Cookie updated. VPN will reconnect automatically." };
    })

    // Clear VPN cookie (reverts to env var)
    .delete("/vpn/cookie", async () => {
        await db
            .delete(systemSettings)
            .where(eq(systemSettings.key, "vpn_cookie"));
        return { success: true, message: "Cookie cleared. Using env var fallback." };
    })

    // ===== FASIH Lookup (untuk wizard Add Survey) =====

    // Simple in-memory rate limiter for proxy lookups
    .onBeforeHandle(({ user, path, set }: any) => {
        if (path.includes("/fasih/")) {
            const now = Date.now();
            const last = lastLookup.get(user!.id) || 0;
            if (now - last < 5000) { // 5 seconds throttle
                set.status = 429;
                return { error: "Too many requests. Please wait 5s." };
            }
            lastLookup.set(user!.id, now);
        }
    })

    // Lookup surveys + provinces dari FASIH API (memerlukan SSO login ~15 detik)
    .post("/fasih/lookup", async ({ body, set }) => {
        const { ssoUsername, ssoPassword } = body as { ssoUsername: string; ssoPassword: string };
        
        // Input Validation
        if (!ssoUsername || !ssoUsername.includes("@bps.go.id")) {
            set.status = 400;
            return { error: "Invalid SSO Username format" };
        }

        const response = await fetch(`${RPA_URL}/lookup/metadata`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ sso_username: ssoUsername, sso_password: ssoPassword }),
            signal: AbortSignal.timeout(90000)
        });

        if (!response.ok) {
            const contentType = response.headers.get("content-type");
            let detail = `RPA error ${response.status}`;
            
            if (contentType && contentType.includes("application/json")) {
                const err = await response.json().catch(() => ({}));
                detail = (err as any).detail || detail;
            } else {
                // If RPA returns 500 HTML or plain text
                const text = await response.text().catch(() => "");
                console.error(`RPA Non-JSON Error (${response.status}):`, text.substring(0, 200));
                if (response.status === 503 || response.status === 502) {
                    detail = "RPA service is unavailable or VPN is disconnected.";
                }
            }
            set.status = response.status === 401 ? 401 : 400;
            return { error: detail };
        }
        return await response.json();
    })

    // Lookup kabupaten untuk satu provinsi
    .post("/fasih/kabupaten", async ({ body, set }) => {
        const { ssoUsername, ssoPassword, provFullCode } = body as {
            ssoUsername: string;
            ssoPassword: string;
            provFullCode: string;
        };

        // Input Validation
        if (!ssoUsername || !ssoUsername.includes("@bps.go.id")) {
            set.status = 400;
            return { error: "Invalid SSO Username format" };
        }
        if (!provFullCode || !/^\d+$/.test(provFullCode)) {
            set.status = 400;
            return { error: "Invalid Province Code format" };
        }

        const response = await fetch(`${RPA_URL}/lookup/kabupaten`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                sso_username: ssoUsername,
                sso_password: ssoPassword,
                prov_full_code: provFullCode,
            }),
            signal: AbortSignal.timeout(90000)
        });

        if (!response.ok) {
            const contentType = response.headers.get("content-type");
            let detail = `RPA error ${response.status}`;
            if (contentType && contentType.includes("application/json")) {
                const err = await response.json().catch(() => ({}));
                detail = (err as any).detail || detail;
            } else {
                if (response.status === 503 || response.status === 502) {
                    detail = "RPA service or VPN is down.";
                }
            }
            set.status = response.status === 401 ? 401 : 400;
            return { error: detail };
        }
        return await response.json();
    })
    
    // Explicitly trigger VPN auto-fetch from UI
    .post("/vpn/auto-fetch", async (ctx: any) => {
        const { set } = ctx;
        const traceId = ctx.traceId || "no-trace";
        const traceparent = ctx.traceparent || "";
        const log = ctx.log || logger.child({ traceId });
        log.info("UI Manual Trigger: VPN Auto-Fix requested");
        
        const [survey] = await db
            .select()
            .from(surveyConfigs)
            .where(eq(surveyConfigs.isActive, true))
            .limit(1);

        if (!survey) {
            set.status = 404;
            log.warn("VPN Auto-fetch failed: No active survey found to borrow credentials from");
            return { error: "No active survey to borrow credentials from" };
        }

        const password = decryptPassword(survey.ssoPasswordEncrypted);
        
        try {
            log.info("Triggering VPN auto-fetch in vpn-auth service", {
                vpn_auth_url: `${VPN_AUTH_URL}/vpn/auto-fetch`,
                sso_username: survey.ssoUsername
            });
            const fetchRes = await fetch(`${VPN_AUTH_URL}/vpn/auto-fetch`, {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json",
                    "X-Trace-ID": traceId,
                    "traceparent": traceparent
                },
                body: JSON.stringify({
                    sso_username: survey.ssoUsername,
                    sso_password: password
                }),
                signal: AbortSignal.timeout(300000)
            });

            if (!fetchRes.ok) {
                const text = await fetchRes.text().catch(() => "");
                let detail = `Auth service error ${fetchRes.status}`;
                try {
                    const err = JSON.parse(text);
                    detail = err.detail || detail;
                } catch {
                    if (text && text.length < 100) detail = text;
                }
                
                log.error(`VPN Auto-fetch failed: ${detail}`, { status: fetchRes.status });
                set.status = fetchRes.status === 401 ? 401 : 400;
                return { error: detail };
            }

            log.info("VPN Auto-fetch triggered successfully");
            return await fetchRes.json();
        } catch (e: any) {
            log.error(`VPN Auto-fetch connection failed: ${e.message}`, { error: e.message, stack: e.stack });
            set.status = 503;
            return { error: `Gagal menghubungi service VPN-Auth: ${e.message}` };
        }
    });

const RPA_API_URL = RPA_URL;

// ===== VPN Auto-Pilot Background Loop =====
// Check VPN status periodically. If disconnected, trigger RPA to auto-fetch the cookie.
const checkVpnAndFetchCookie = async () => {
    // Generate a background trace ID for this run of the auto-pilot loop
    const traceId = "autopilot-" + Math.random().toString(36).substring(2, 10);
    const log = logger.child({ traceId });

    try {
        log.info("Checking VPN status", { rpa_url: `${RPA_API_URL}/vpn/check` });
        const statusRes = await fetch(`${RPA_API_URL}/vpn/check`, { 
            headers: {
                "X-Trace-ID": traceId
            },
            signal: AbortSignal.timeout(20000) 
        }).then(r => r.json()).catch((err) => {
            log.warn("VPN check request failed", { error: err.message });
            return { connected: false };
        }) as any;

        if (!statusRes.connected) {
            log.warn("VPN Disconnected detected! Attempting auto-fetch...", { vpn_info: statusRes });
            
            // 2. Identify an active survey to borrow credentials for auto-fetch
            let survey;
            try {
                [survey] = await db
                    .select()
                    .from(surveyConfigs)
                    .where(eq(surveyConfigs.isActive, true))
                    .limit(1);
            } catch (dbErr: any) {
                if (dbErr.message?.includes('does not exist')) {
                    log.warn("Table 'survey_configs' does not exist yet. Skipping auto-pilot.");
                } else if (dbErr.message?.includes('uuid')) {
                    log.error("Database Schema Mismatch (UUID Cast Error). Please run manual migration.", { error: dbErr.message });
                } else {
                    log.error("Database error in VPN Auto-Pilot", { error: dbErr.message });
                }
                return;
            }

            if (!survey) {
                // Fallback: Check if we have Master SSO credentials in .env
                if (process.env.VPN_USER && process.env.VPN_PASS) {
                    log.info("No active survey found, but using Master SSO (VPN_USER) for bootstrap...", { sso_username: process.env.VPN_USER });
                    const fetchRes = await fetch(`${RPA_API_URL}/vpn/auto-fetch`, {
                        method: "POST",
                        headers: { 
                            "Content-Type": "application/json",
                            "X-Trace-ID": traceId
                        },
                        body: JSON.stringify({
                            sso_username: process.env.VPN_USER,
                            sso_password: process.env.VPN_PASS
                        }),
                        signal: AbortSignal.timeout(300000)
                    });
                    
                    if (fetchRes.ok) {
                        log.info("VPN bootstrap triggered successfully!");
                    } else {
                        log.error("Failed to trigger VPN bootstrap", { status: fetchRes.status });
                    }
                    return;
                }

                log.warn("No active survey found and no Master SSO (VPN_USER) configured. Cannot auto-pilot.");
                return;
            }

            log.info("Borrowing credentials from active survey for auto-pilot", { 
                sso_username: survey.ssoUsername, 
                survey_name: survey.surveyName 
            });
            const password = decryptPassword(survey.ssoPasswordEncrypted);
            
            const fetchRes = await fetch(`${RPA_API_URL}/vpn/auto-fetch`, {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json",
                    "X-Trace-ID": traceId
                },
                body: JSON.stringify({
                    sso_username: survey.ssoUsername,
                    sso_password: password
                }),
                signal: AbortSignal.timeout(300000)
            });

            if (fetchRes.ok) {
                log.info("VPN auto-fetch triggered successfully! RPA is grabbing the cookie.");
            } else {
                log.error("Failed to trigger RPA VPN auto-fetch", { status: fetchRes.status });
            }
        } else {
            log.info("VPN is connected and stable", { info: statusRes.info });
        }
    } catch (err: any) {
        log.error("Fatal Error in VPN Auto-Pilot loop", { error: err.message, stack: err.stack });
    }
};

// Check every 60 seconds
setInterval(checkVpnAndFetchCookie, 60000);
// Also run it 5 seconds after the dashboard boots up (giving time for RPA to start)
setTimeout(checkVpnAndFetchCookie, 5000);

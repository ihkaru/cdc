import { Elysia } from "elysia";
import { db } from "../db";
import { surveyConfigs, systemSettings } from "../db/schema";
import { eq } from "drizzle-orm";
import { createHash, createDecipheriv } from "crypto";

const RPA_URL = process.env.RPA_URL || "http://rpa:8000";

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

export const syncRoutes = new Elysia({ prefix: "/api/surveys" })
    // Trigger sync for a survey
    .post("/:id/sync", async ({ params }) => {
        const [survey] = await db
            .select()
            .from(surveyConfigs)
            .where(eq(surveyConfigs.id, params.id));

        if (!survey) throw new Error("Survey not found");

        // Decrypt password and send to RPA
        const password = decryptPassword(survey.ssoPasswordEncrypted);

        const response = await fetch(`${RPA_URL}/sync`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                survey_config_id: survey.id,
                survey_name: survey.surveyName,
                sso_username: survey.ssoUsername,
                sso_password: password,
                filter_provinsi: survey.filterProvinsi || "",
                filter_kabupaten: survey.filterKabupaten || "",
                filter_rotation: survey.filterRotation || "pengawas",
            }),
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error((err as any).detail || `RPA responded with ${response.status}`);
        }

        return await response.json();
    })

    // Get RPA sync status
    .get("/sync/status", async () => {
        try {
            const response = await fetch(`${RPA_URL}/status`);
            return await response.json();
        } catch {
            return { is_running: false, error: "RPA service unavailable" };
        }
    })

    // Get VPN connection status from RPA
    .get("/vpn/status", async () => {
        try {
            const response = await fetch(`${RPA_URL}/vpn/check`);
            return await response.json();
        } catch {
            return { connected: false, error: "RPA service unavailable" };
        }
    })

    // Cancel a queued sync job
    .delete("/sync/:jobId", async ({ params }) => {
        try {
            const response = await fetch(`${RPA_URL}/sync/${params.jobId}`, {
                method: "DELETE",
            });
            return await response.json();
        } catch {
            return { error: "RPA service unavailable" };
        }
    })

    // Update VPN cookie (store in PostgreSQL for VPN container to read)
    .post("/vpn/cookie", async ({ body }) => {
        const { cookie } = body as { cookie: string };
        if (!cookie || cookie.trim().length < 10) {
            throw new Error("Cookie is empty or too short");
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

    // Lookup surveys + provinces dari FASIH API (memerlukan SSO login ~15 detik)
    .post("/fasih/lookup", async ({ body }) => {
        const { ssoUsername, ssoPassword } = body as { ssoUsername: string; ssoPassword: string };
        const response = await fetch(`${RPA_URL}/lookup/metadata`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ sso_username: ssoUsername, sso_password: ssoPassword }),
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            const detail = (err as any).detail || `RPA error ${response.status}`;
            throw new Error(detail);
        }
        return await response.json();
    })

    // Lookup kabupaten untuk satu provinsi
    .post("/fasih/kabupaten", async ({ body }) => {
        const { ssoUsername, ssoPassword, provFullCode } = body as {
            ssoUsername: string;
            ssoPassword: string;
            provFullCode: string;
        };
        const response = await fetch(`${RPA_URL}/lookup/kabupaten`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                sso_username: ssoUsername,
                sso_password: ssoPassword,
                prov_full_code: provFullCode,
            }),
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error((err as any).detail || `RPA error ${response.status}`);
        }
        return await response.json();
    });


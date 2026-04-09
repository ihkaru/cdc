import { Elysia, t } from "elysia";
import { db } from "../db";
import { surveyConfigs } from "../db/schema";
import { eq, ilike, or } from "drizzle-orm";

// Simple AES encryption matching Python's crypto.py
import { createCipheriv, createDecipheriv, createHash, randomBytes } from "crypto";

function getEncryptionKey(): Buffer {
    const key = process.env.ENCRYPTION_KEY || "";
    if (!key) throw new Error("ENCRYPTION_KEY not set");
    return createHash("sha256").update(key).digest();
}

function encryptPassword(plaintext: string): string {
    const key = getEncryptionKey();
    const iv = randomBytes(16);
    const cipher = createCipheriv("aes-256-cbc", key, iv);
    const encrypted = Buffer.concat([cipher.update(plaintext, "utf8"), cipher.final()]);
    return iv.toString("hex") + ":" + encrypted.toString("hex");
}

function decryptPassword(ciphertext: string): string {
    const key = getEncryptionKey();
    const parts = ciphertext.split(":");
    if (parts.length < 2) throw new Error("Invalid encrypted format");
    const iv = Buffer.from(parts[0]!, "hex");
    const encrypted = Buffer.from(parts[1]!, "hex");
    const decipher = createDecipheriv("aes-256-cbc", key, iv);
    return decipher.update(encrypted) + decipher.final("utf8");
}

export const surveysRoutes = new Elysia({ prefix: "/api/surveys" })
    // List all surveys
    .get("/", async ({ query }) => {
        const q = query.q as string | undefined;
        let dbQuery = db.select().from(surveyConfigs);
        
        if (q) {
            const searchStr = `%${q}%`;
            // @ts-ignore - drizzle-orm type compatibility
            dbQuery = dbQuery.where(
                or(
                    ilike(surveyConfigs.surveyName, searchStr),
                    ilike(surveyConfigs.ssoUsername, searchStr),
                    ilike(surveyConfigs.filterKabupaten, searchStr)
                )
            );
        }

        const rows = await dbQuery;
        return rows.map((r) => ({
            ...r,
            ssoPasswordEncrypted: undefined, // Never expose password
        }));
    })

    // Get single survey
    .get("/:id", async ({ params }) => {
        const [row] = await db
            .select()
            .from(surveyConfigs)
            .where(eq(surveyConfigs.id, params.id));
        if (!row) throw new Error("Survey not found");
        return { ...row, ssoPasswordEncrypted: undefined };
    })

    // Create survey
    .post(
        "/",
        async ({ body }) => {
            const encrypted = encryptPassword(body.ssoPassword);
            const [created] = await db
                .insert(surveyConfigs)
                .values({
                    surveyName: body.surveyName,
                    ssoUsername: body.ssoUsername,
                    ssoPasswordEncrypted: encrypted,
                    filterProvinsi: body.filterProvinsi || "",
                    filterKabupaten: body.filterKabupaten || "",
                    filterRotation: body.filterRotation || "pengawas",
                    intervalMinutes: body.intervalMinutes || 30,
                    isActive: true,
                })
                .returning();
            return { ...created, ssoPasswordEncrypted: undefined };
        },
        {
            body: t.Object({
                surveyName: t.String(),
                ssoUsername: t.String(),
                ssoPassword: t.String(),
                filterProvinsi: t.Optional(t.String()),
                filterKabupaten: t.Optional(t.String()),
                filterRotation: t.Optional(t.String()),
                intervalMinutes: t.Optional(t.Number()),
            }),
        }
    )

    // Update survey
    .put(
        "/:id",
        async ({ params, body }) => {
            const updates: Record<string, any> = {
                surveyName: body.surveyName,
                ssoUsername: body.ssoUsername,
                filterProvinsi: body.filterProvinsi,
                filterKabupaten: body.filterKabupaten,
                filterRotation: body.filterRotation,
                intervalMinutes: body.intervalMinutes,
                isActive: body.isActive,
                updatedAt: new Date(),
            };
            // Only re-encrypt if password provided
            if (body.ssoPassword) {
                updates.ssoPasswordEncrypted = encryptPassword(body.ssoPassword);
            }

            const [updated] = await db
                .update(surveyConfigs)
                .set(updates)
                .where(eq(surveyConfigs.id, params.id))
                .returning();
            if (!updated) throw new Error("Survey not found");
            return { ...updated, ssoPasswordEncrypted: undefined };
        },
        {
            body: t.Object({
                surveyName: t.Optional(t.String()),
                ssoUsername: t.Optional(t.String()),
                ssoPassword: t.Optional(t.String()),
                filterProvinsi: t.Optional(t.String()),
                filterKabupaten: t.Optional(t.String()),
                filterRotation: t.Optional(t.String()),
                intervalMinutes: t.Optional(t.Number()),
                isActive: t.Optional(t.Boolean()),
            }),
        }
    )

    // Delete survey
    .delete("/:id", async ({ params }) => {
        await db.delete(surveyConfigs).where(eq(surveyConfigs.id, params.id));
        return { success: true };
    });

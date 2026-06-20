// Simple AES encryption matching Python's crypto.py

import { DeleteObjectsCommand } from "@aws-sdk/client-s3";
import { createCipheriv, createDecipheriv, createHash, randomBytes } from "crypto";
import { eq, ilike, or } from "drizzle-orm";
import { Elysia, t } from "elysia";
import { db } from "../db";
import { assignments, surveyConfigs } from "../db/schema";
import { s3Client } from "./storage";

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

import { requireAdmin, requireAuth } from "../middleware/auth";

export const surveysRoutes = new Elysia({ prefix: "/api/surveys" })
	.use(requireAuth)
	// List all surveys
	.get("/", async ({ query }) => {
		const q = query.q as string | undefined;
		let dbQuery = db.select().from(surveyConfigs);

		if (q) {
			const searchStr = `%${q}%`;
			// @ts-expect-error - drizzle-orm type compatibility
			dbQuery = dbQuery.where(
				or(
					ilike(surveyConfigs.surveyName, searchStr),
					ilike(surveyConfigs.ssoUsername, searchStr),
					ilike(surveyConfigs.filterKabupaten, searchStr),
				),
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
		const [row] = await db.select().from(surveyConfigs).where(eq(surveyConfigs.id, params.id));
		if (!row) throw new Error("Survey not found");
		return { ...row, ssoPasswordEncrypted: undefined };
	})

	// Create survey
	.use(requireAdmin)
	.post(
		"/",
		async ({ body }) => {
			const encrypted = encryptPassword(body.ssoPassword);
			const [created] = await db
				.insert(surveyConfigs)
				.values({
					surveyName: body.surveyName,
					bpsSurveyId: body.bpsSurveyId || "",
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
				bpsSurveyId: t.Optional(t.String()),
				ssoUsername: t.String(),
				ssoPassword: t.String(),
				filterProvinsi: t.Optional(t.String()),
				filterKabupaten: t.Optional(t.String()),
				filterRotation: t.Optional(t.String()),
				intervalMinutes: t.Optional(t.Number()),
			}),
		},
	)

	// Update survey
	.use(requireAdmin)
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
			if (body.bpsSurveyId !== undefined) {
				updates.bpsSurveyId = body.bpsSurveyId;
			}
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
				bpsSurveyId: t.Optional(t.String()),
				ssoUsername: t.Optional(t.String()),
				ssoPassword: t.Optional(t.String()),
				filterProvinsi: t.Optional(t.String()),
				filterKabupaten: t.Optional(t.String()),
				filterRotation: t.Optional(t.String()),
				intervalMinutes: t.Optional(t.Number()),
				isActive: t.Optional(t.Boolean()),
			}),
		},
	)

	// Delete survey
	.use(requireAdmin)
	.delete("/:id", async ({ params }) => {
		// 1. Fetch all associated assignments to get local image paths
		const assocAssignments = await db
			.select({ id: assignments.id, localImagePaths: assignments.localImagePaths })
			.from(assignments)
			.where(eq(assignments.surveyConfigId, params.id));

		const s3KeysToDelete: { Key: string }[] = [];
		const bucket = process.env.S3_BUCKET || "survey-images";

		for (const a of assocAssignments) {
			const paths = (a.localImagePaths as Record<string, string>) || {};
			for (const path of Object.values(paths)) {
				// path is like "survey-images/uuid/photo_key.jpg"
				const key = path.replace(`${bucket}/`, "");
				if (key) {
					s3KeysToDelete.push({ Key: key });
				}
			}
		}

		// 2. Delete from SeaweedFS in chunks of 1000 (S3 API limit)
		if (s3KeysToDelete.length > 0) {
			try {
				const CHUNK_SIZE = 1000;
				for (let i = 0; i < s3KeysToDelete.length; i += CHUNK_SIZE) {
					const chunk = s3KeysToDelete.slice(i, i + CHUNK_SIZE);
					const deleteCommand = new DeleteObjectsCommand({
						Bucket: bucket,
						Delete: { Objects: chunk },
					});
					await s3Client.send(deleteCommand);
				}
				console.log(
					`🧹 [S3 Cleanup] Deleted ${s3KeysToDelete.length} mirrored images for survey ${params.id}`,
				);
			} catch (err) {
				console.error("Failed to delete mirrored images from SeaweedFS:", err);
			}
		}

		// 3. Delete from DB (cascade deletes assignments, sync_logs, labels)
		await db.delete(surveyConfigs).where(eq(surveyConfigs.id, params.id));
		return { success: true };
	});

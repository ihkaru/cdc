// Simple AES encryption matching Python's crypto.py

import { DeleteObjectsCommand } from "@aws-sdk/client-s3";
import { createCipheriv, createDecipheriv, createHash, randomBytes } from "crypto";
import { desc, eq, ilike, inArray, or } from "drizzle-orm";
import { Elysia, t } from "elysia";
import { db } from "../db";
import { assignments, surveyConfigs, syncLogs } from "../db/schema";
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
	return `${iv.toString("hex")}:${encrypted.toString("hex")}`;
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
		const results = await Promise.all(
			rows
				.filter((r) => !r.surveyName.startsWith("[DELETING]"))
				.map(async (r) => {
					const [latestLog] = await db
						.select()
						.from(syncLogs)
						.where(eq(syncLogs.surveyConfigId, r.id))
						.orderBy(desc(syncLogs.startedAt))
						.limit(1);

					return {
						...r,
						ssoPasswordEncrypted: undefined,
						latestLog: latestLog || null,
					};
				}),
		);
		return results;
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

	// Delete survey (Asynchronous Background Job with Batch Deletion)
	.use(requireAdmin)
	.delete("/:id", async ({ params, set }) => {
		const surveyId = params.id;

		// 1. Fetch the survey first to verify it exists and get its name
		const [survey] = await db
			.select()
			.from(surveyConfigs)
			.where(eq(surveyConfigs.id, surveyId))
			.limit(1);

		if (!survey) {
			set.status = 404;
			return { error: "Survey not found" };
		}

		// 2. Mark as deleting and inactive so it gets hidden from list immediately
		// and ignored by scheduler
		const originalName = survey.surveyName;
		await db
			.update(surveyConfigs)
			.set({
				surveyName: `[DELETING] ${originalName}`,
				isActive: false,
			})
			.where(eq(surveyConfigs.id, surveyId));

		// 3. Start background batch deletion task (Do NOT await!)
		(async () => {
			console.log(
				`🧹 [Background Cleanup] Starting asynchronous deletion for survey "${originalName}" (${surveyId})...`,
			);
			const bucket = process.env.S3_BUCKET || "survey-images";
			let totalImagesDeleted = 0;
			let totalAssignmentsDeleted = 0;

			try {
				while (true) {
					// Fetch a batch of 5000 assignments to process
					const batch = await db
						.select({ id: assignments.id, localImagePaths: assignments.localImagePaths })
						.from(assignments)
						.where(eq(assignments.surveyConfigId, surveyId))
						.limit(5000);

					if (batch.length === 0) {
						break;
					}

					// Collect S3 keys to delete in this batch
					const s3KeysToDelete: { Key: string }[] = [];
					for (const a of batch) {
						const paths = (a.localImagePaths as Record<string, string>) || {};
						for (const path of Object.values(paths)) {
							const key = path.replace(`${bucket}/`, "");
							if (key) {
								s3KeysToDelete.push({ Key: key });
							}
						}
					}

					// Delete objects from SeaweedFS in chunks of 1000
					if (s3KeysToDelete.length > 0) {
						const CHUNK_SIZE = 1000;
						for (let i = 0; i < s3KeysToDelete.length; i += CHUNK_SIZE) {
							const chunk = s3KeysToDelete.slice(i, i + CHUNK_SIZE);
							const deleteCommand = new DeleteObjectsCommand({
								Bucket: bucket,
								Delete: { Objects: chunk },
							});
							await s3Client.send(deleteCommand).catch((err) => {
								console.error("Failed to delete mirrored images chunk from SeaweedFS:", err);
							});
						}
						totalImagesDeleted += s3KeysToDelete.length;
					}

					// Delete assignments batch from database
					const batchIds = batch.map((a) => a.id);
					await db.delete(assignments).where(inArray(assignments.id, batchIds));
					totalAssignmentsDeleted += batch.length;

					console.log(
						`🧹 [Background Cleanup] Processed batch: deleted ${batch.length} assignments and ${s3KeysToDelete.length} images.`,
					);
				}

				// 4. Finally delete the parent survey config (cascades remaining logs, schemas, etc.)
				await db.delete(surveyConfigs).where(eq(surveyConfigs.id, surveyId));
				console.log(
					`✅ [Background Cleanup] Successfully deleted survey "${originalName}" (${surveyId}). ` +
						`Total assignments: ${totalAssignmentsDeleted}, Total images: ${totalImagesDeleted}.`,
				);
			} catch (err) {
				console.error(`❌ [Background Cleanup] Error deleting survey "${originalName}":`, err);
			}
		})();

		// 5. Return success instantly to client
		return {
			success: true,
			message: "Proses penghapusan survey sedang berjalan di latar belakang.",
		};
	});

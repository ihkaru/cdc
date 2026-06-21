import { and, count, desc, eq, lt, sql } from "drizzle-orm";
import { Elysia, t } from "elysia";
import * as XLSX from "xlsx";
import { client, db } from "../db";
import { assignments, labelData, syncLogs } from "../db/schema";

function extractVariables(dataJson: any): Record<string, any> {
	if (!dataJson) return {};
	const dataObj = typeof dataJson === "string" ? JSON.parse(dataJson) : dataJson;
	const vars: Record<string, any> = {};

	function explore(obj: any, prefix = "", depth = 0) {
		if (!obj || typeof obj !== "object" || depth > 5) return;

		for (const k in obj) {
			const val = obj[k];
			const keyName = prefix ? `${prefix}.${k}` : k;

			if (val === null || val === undefined) continue;

			// Handle stringified JSON (common in FASIH 'data' or 'pre_defined_data' fields)
			if (typeof val === "string" && (val.startsWith("{") || val.startsWith("["))) {
				try {
					const parsed = JSON.parse(val);
					if (parsed && typeof parsed === "object") {
						explore(parsed, keyName, depth); // Explore inside parsed string content
						continue;
					}
				} catch (e) {}
			}

			if (typeof val === "object" && !Array.isArray(val)) {
				explore(val, keyName, depth + 1);
			} else if (Array.isArray(val)) {
				// FASIH Specialized: 'answers', 'predata', or 'data' arrays
				if (k === "answers" || k === "predata" || k === "data") {
					val.forEach((item: any) => {
						if (item && item.dataKey) {
							let ans = item.answer;
							// Extract URL from photo/media array if present
							if (Array.isArray(ans) && ans.length > 0 && ans[0]?.url) {
								ans = ans[0].url;
							}
							vars[item.dataKey] = ans;
						}
					});
				}
			} else {
				// Scalar values
				const isUrl = typeof val === "string" && val.startsWith("http");
				const isImageKey = /foto|image|img|photo/i.test(k);

				if (isUrl || isImageKey || depth < 2) {
					vars[keyName] = val;
				}
			}
		}
	}

	explore(dataObj);
	return vars;
}

import { requireAuth } from "../middleware/auth";

export const assignmentsRoutes = new Elysia({ prefix: "/api/surveys" })
	.use(requireAuth)
	// Get assignments for a survey (paginated — supports both offset and cursor)
	.get("/:id/assignments", async ({ params, query: queryParams }) => {
		const limit = Math.min(Number(queryParams.limit) || 50, 200);
		const cursor = queryParams.cursor as string | undefined;
		const q = queryParams.q as string | undefined;

		// Build base WHERE clause
		let baseWhere = eq(assignments.surveyConfigId, params.id);
		if (q) {
			const searchStr = `%${q}%`;
			baseWhere = and(
				baseWhere,
				sql`(${assignments.codeIdentity} ILIKE ${searchStr} OR 
                         ${assignments.currentUserUsername} ILIKE ${searchStr} OR 
                         ${assignments.assignmentStatusAlias} ILIKE ${searchStr} OR 
                         ${assignments.dataJson}::text ILIKE ${searchStr} OR 
                         ${assignments.flatData}::text ILIKE ${searchStr} OR 
                         ${labelData.data}::text ILIKE ${searchStr})`,
			)!;
		}

		// Fetch pagination parameters
		const page = Number(queryParams.page) || 1;
		const offset = (page - 1) * limit;

		// Cursor-based pagination: use dateSynced + id as composite cursor
		let whereClause = baseWhere;
		if (cursor) {
			const [cursorDate, cursorId] = cursor.split("|");
			if (cursorDate && cursorId) {
				whereClause = and(
					baseWhere,
					sql`(${assignments.dateSynced}, ${assignments.id}) < (${cursorDate}::timestamptz, ${cursorId})`,
				)!;
			}
		}

		const rows = await db
			.select({
				id: assignments.id,
				surveyConfigId: assignments.surveyConfigId,
				codeIdentity: assignments.codeIdentity,
				surveyPeriodId: assignments.surveyPeriodId,
				assignmentStatusAlias: assignments.assignmentStatusAlias,
				currentUserUsername: assignments.currentUserUsername,
				dataJson: assignments.dataJson,
				flatData: assignments.flatData,
				dateModifiedRemote: assignments.dateModifiedRemote,
				dateSynced: assignments.dateSynced,
				syncedToApi: assignments.syncedToApi,
				localImageMirrored: assignments.localImageMirrored,
				localImagePaths: assignments.localImagePaths,
				labelData: labelData.data,
				// Preserve microsecond-precision in ISO format directly from PostgreSQL to prevent cursor skipping
				dateSyncedPrecision: sql<string>`to_char(${assignments.dateSynced}, 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"')`,
			})
			.from(assignments)
			.leftJoin(
				labelData,
				and(
					eq(assignments.surveyConfigId, labelData.surveyConfigId),
					eq(assignments.codeIdentity, labelData.codeIdentity),
				),
			)
			.where(whereClause)
			.orderBy(desc(assignments.dateSynced), desc(assignments.id))
			.limit(limit + 1)
			.offset(!cursor && offset > 0 ? offset : 0);

		const hasMore = rows.length > limit;
		const records = rows.slice(0, limit).map((r) => {
			const deep = extractVariables(r.dataJson);
			return {
				...r,
				flatData: { ...deep, ...((r.flatData as object) || {}) },
				dataJson: undefined, // Hide bulky raw json from UI
			};
		});

		// Build next cursor from last row using the microsecond-precision ISO timestamp
		let nextCursor: string | null = null;
		if (hasMore && records.length > 0) {
			const lastRow = rows[limit - 1]!;
			nextCursor = `${lastRow.dateSyncedPrecision || ""}|${lastRow.id}`;
		}

		const countQuery = db.select({ count: sql`count(*)::int` }).from(assignments);

		if (q) {
			countQuery.leftJoin(
				labelData,
				and(
					eq(assignments.surveyConfigId, labelData.surveyConfigId),
					eq(assignments.codeIdentity, labelData.codeIdentity),
				),
			);
		}

		const [countResult] = await countQuery.where(baseWhere);
		const total = Number(countResult?.count || 0);

		return {
			data: records,
			pagination: {
				page,
				limit,
				total: total,
				totalPages: Math.ceil(total / limit),
				hasMore,
				nextCursor,
			},
		};
	})

	// Export assignments to CSV (Streaming)
	.get("/:id/assignments/export", async ({ params, query, request, set }) => {
		const q = query.q as string | undefined;

		// Resolve the public base URL for vault image links in the exported file.
		const baseUrl =
			process.env.PUBLIC_BASE_URL?.replace(/\/$/, "") ?? (request.headers.get("origin") || "");

		// 1. Discover dynamic keys via SQL JSONB key extraction (Avoids loading all rows to search keys)
		let dynamicKeys: string[] = [];
		let labelKeys: string[] = [];
		try {
			const assignRes = await client<{ key: string }[]>`
				SELECT DISTINCT jsonb_object_keys(flat_data) as key 
				FROM assignments 
				WHERE survey_config_id = ${params.id}::uuid
			`;
			dynamicKeys = assignRes.map((r) => r.key).sort();
		} catch (err) {
			console.error("Error discovering assignment keys:", err);
		}

		try {
			const labelRes = await client<{ key: string }[]>`
				SELECT DISTINCT jsonb_object_keys(data) as key 
				FROM label_data 
				WHERE survey_config_id = ${params.id}::uuid
			`;
			labelKeys = labelRes.map((r) => r.key).sort();
		} catch (err) {
			console.error("Error discovering label keys:", err);
		}

		// 2. Construct Headers
		const baseHeaders = [
			"ID",
			"Code Identity",
			"Status",
			"User",
			"Date Modified (Remote)",
			"Date Synced",
		];
		const headers = [...baseHeaders, ...dynamicKeys, ...labelKeys.map((k) => `[Label] ${k}`)];

		// Helper function for CSV escaping
		const escapeCSV = (val: any): string => {
			if (val === null || val === undefined) return "";
			const str = typeof val === "object" ? JSON.stringify(val) : String(val);
			if (str.includes(",") || str.includes('"') || str.includes("\n") || str.includes("\r")) {
				return `"${str.replace(/"/g, '""')}"`;
			}
			return str;
		};

		// 3. Initialize server-side cursor for fetching matching rows
		let cursor;
		if (q) {
			const searchStr = `%${q}%`;
			cursor = client`
				SELECT 
					a.id, a.code_identity, a.assignment_status_alias, a.current_user_username,
					a.date_modified_remote, a.date_synced, a.flat_data, a.data_json, a.local_image_paths,
					l.data as label_data
				FROM assignments a
				LEFT JOIN label_data l ON a.code_identity = l.code_identity AND a.survey_config_id = l.survey_config_id
				WHERE a.survey_config_id = ${params.id}::uuid
				  AND (
					a.code_identity ILIKE ${searchStr} OR 
					a.current_user_username ILIKE ${searchStr} OR 
					a.assignment_status_alias ILIKE ${searchStr} OR 
					a.data_json::text ILIKE ${searchStr} OR 
					a.flat_data::text ILIKE ${searchStr} OR 
					l.data::text ILIKE ${searchStr}
				  )
				ORDER BY a.date_synced DESC
			`.cursor(2000);
		} else {
			cursor = client`
				SELECT 
					a.id, a.code_identity, a.assignment_status_alias, a.current_user_username,
					a.date_modified_remote, a.date_synced, a.flat_data, a.data_json, a.local_image_paths,
					l.data as label_data
				FROM assignments a
				LEFT JOIN label_data l ON a.code_identity = l.code_identity AND a.survey_config_id = l.survey_config_id
				WHERE a.survey_config_id = ${params.id}::uuid
				ORDER BY a.date_synced DESC
			`.cursor(2000);
		}

		// 4. Create Web ReadableStream to stream CSV chunk-by-chunk
		const stream = new ReadableStream({
			async start(controller) {
				try {
					// Enqueue header row first
					const headerLine = `${headers.map(escapeCSV).join(",")}\n`;
					controller.enqueue(new TextEncoder().encode(headerLine));

					// Fetch and process rows in batches from database
					for await (const rows of cursor) {
						let chunk = "";
						for (const row of rows) {
							const deep = extractVariables(row.data_json);
							const flat = { ...deep, ...((row.flat_data as object) || {}) } as Record<string, any>;
							const labels = (row.label_data || {}) as Record<string, any>;
							const vaultPaths = (row.local_image_paths || {}) as Record<string, string>;

							const rowValues = [
								row.id,
								row.code_identity,
								row.assignment_status_alias,
								row.current_user_username,
								row.date_modified_remote,
								row.date_synced ? new Date(row.date_synced).toLocaleString("id-ID") : "",
								...dynamicKeys.map((k) => {
									if (vaultPaths[k]) {
										return `${baseUrl}/storage/view/${vaultPaths[k]}`;
									}
									const val = flat[k];
									return typeof val === "object" ? JSON.stringify(val) : (val ?? "");
								}),
								...labelKeys.map((k) => {
									const val = labels[k];
									return typeof val === "object" ? JSON.stringify(val) : (val ?? "");
								}),
							];

							chunk += `${rowValues.map(escapeCSV).join(",")}\n`;
						}
						// Enqueue CSV chunk to HTTP stream
						controller.enqueue(new TextEncoder().encode(chunk));
					}
					controller.close();
				} catch (err) {
					console.error("Error in CSV export stream:", err);
					controller.error(err);
				}
			},
		});

		const filename = `export_survey_${params.id.substring(0, 8)}_${new Date().toISOString().split("T")[0]}.csv`;

		return new Response(stream, {
			headers: {
				"Content-Type": "text/csv; charset=utf-8",
				"Content-Disposition": `attachment; filename="${filename}"`,
				"Transfer-Encoding": "chunked",
				"Cache-Control": "no-cache",
				Connection: "keep-alive",
			},
		});
	})

	// Get stats for a survey
	.get("/:id/stats", async ({ params }) => {
		try {
			// Query assignments counts grouped by status alias
			const rows = await db
				.select({
					status: assignments.assignmentStatusAlias,
					count: count(),
				})
				.from(assignments)
				.where(eq(assignments.surveyConfigId, params.id))
				.groupBy(assignments.assignmentStatusAlias);

			const breakdown = rows.map((r) => ({
				status: r.status || "UNKNOWN",
				count: Number(r.count || 0),
			}));

			const total = breakdown.reduce((sum, item) => sum + item.count, 0);

			// Map and classify for backwards compatibility
			let open = 0;
			let submitted = 0;
			let rejected = 0;

			for (const item of breakdown) {
				const s = item.status.toLowerCase();
				if (s.includes("open") || s.includes("draft")) {
					open += item.count;
				} else if (
					s.includes("submitted") ||
					s.includes("approved") ||
					s.includes("uploaded") ||
					s.includes("completed")
				) {
					submitted += item.count;
				} else if (s.includes("rejected") || s.includes("error") || s.includes("revoked")) {
					rejected += item.count;
				} else {
					open += item.count;
				}
			}

			// Retrieve the latest totalTargetRemote, totalScopeMetadata and bpsProgress snapshot.
			// We fetch two logs:
			// 1. Latest log overall (for totalTargetRemote + totalScopeMetadata)
			// 2. Latest log with bpsProgress != null (in case latest sync failed before analytics fetch)
			const [latestLog] = await db
				.select({
					totalTargetRemote: syncLogs.totalTargetRemote,
					totalScopeMetadata: syncLogs.totalScopeMetadata,
					bpsProgress: syncLogs.bpsProgress,
					status: syncLogs.status,
				})
				.from(syncLogs)
				.where(eq(syncLogs.surveyConfigId, params.id))
				.orderBy(desc(syncLogs.startedAt))
				.limit(1);

			// Find the most recent log that actually has bpsProgress data
			// (the latest log might have failed before calling the analytics API)
			let bpsProgressData = latestLog ? (latestLog.bpsProgress as any) : null;
			if (!bpsProgressData) {
				const [logWithProgress] = await db
					.select({
						bpsProgress: syncLogs.bpsProgress,
						totalTargetRemote: syncLogs.totalTargetRemote,
					})
					.from(syncLogs)
					.where(
						and(eq(syncLogs.surveyConfigId, params.id), sql`${syncLogs.bpsProgress} IS NOT NULL`),
					)
					.orderBy(desc(syncLogs.startedAt))
					.limit(1);
				if (logWithProgress) {
					bpsProgressData = logWithProgress.bpsProgress as any;
				}
			}

			return {
				total,
				open,
				submitted,
				rejected,
				breakdown,
				totalTargetRemote: latestLog ? Number(latestLog.totalTargetRemote || 0) : 0,
				totalScopeMetadata: latestLog ? Number(latestLog.totalScopeMetadata || 0) : 0,
				syncStatus: latestLog?.status || null,
				bpsProgress: bpsProgressData,
			};
		} catch (error) {
			console.error(`Error fetching stats for survey ${params.id}:`, error);
			return {
				total: 0,
				open: 0,
				submitted: 0,
				rejected: 0,
				breakdown: [],
				totalTargetRemote: 0,
				totalScopeMetadata: 0,
			};
		}
	})

	// Get workload per user for a survey
	.get("/:id/workload", async ({ params }) => {
		try {
			const rows = await db
				.select({
					username: assignments.currentUserUsername,
					total: count(),
					open: count(
						sql`CASE WHEN ${assignments.assignmentStatusAlias} ILIKE '%open%' OR ${assignments.assignmentStatusAlias} ILIKE '%draft%' THEN 1 END`,
					),
					rejected: count(
						sql`CASE WHEN ${assignments.assignmentStatusAlias} ILIKE '%rejected%' OR ${assignments.assignmentStatusAlias} ILIKE '%error%' THEN 1 END`,
					),
				})
				.from(assignments)
				.where(eq(assignments.surveyConfigId, params.id))
				.groupBy(assignments.currentUserUsername);

			const result = rows
				.map((r) => {
					const pending = Number(r.open || 0) + Number(r.rejected || 0);
					const totalStr = Number(r.total || 0);
					const openStr = Number(r.open || 0);
					return {
						username: r.username || "Unassigned",
						pending,
						total: totalStr,
						open: openStr,
						rejected: Number(r.rejected || 0),
						completed: totalStr - openStr,
					};
				})
				.sort((a, b) => b.pending - a.pending);

			return result;
		} catch (error) {
			console.error(`Error fetching workload for survey ${params.id}:`, error);
			return [];
		}
	});

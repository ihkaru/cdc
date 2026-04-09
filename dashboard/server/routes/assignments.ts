import { Elysia, t } from "elysia";
import { db } from "../db";
import { assignments, labelData } from "../db/schema";
import { eq, desc, sql, count, and, lt } from "drizzle-orm";
import * as XLSX from "xlsx";

function extractVariables(dataJson: any): Record<string, any> {
    if (!dataJson) return {};
    const dataObj = typeof dataJson === 'string' ? JSON.parse(dataJson) : dataJson;
    const vars: Record<string, any> = {};

    function explore(obj: any, prefix = '', depth = 0) {
        if (!obj || typeof obj !== 'object' || depth > 5) return;
        
        for (const k in obj) {
            let val = obj[k];
            const keyName = prefix ? `${prefix}.${k}` : k;
            
            if (val === null || val === undefined) continue;

            // Handle stringified JSON (common in FASIH 'data' or 'pre_defined_data' fields)
            if (typeof val === 'string' && (val.startsWith('{') || val.startsWith('['))) {
                try {
                    const parsed = JSON.parse(val);
                    if (parsed && typeof parsed === 'object') {
                        explore(parsed, keyName, depth); // Explore inside parsed string content
                        continue;
                    }
                } catch (e) {}
            }

            if (typeof val === 'object' && !Array.isArray(val)) {
                explore(val, keyName, depth + 1);
            } else if (Array.isArray(val)) {
                // FASIH Specialized: 'answers', 'predata', or 'data' arrays
                if (k === 'answers' || k === 'predata' || k === 'data') {
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
                const isUrl = typeof val === 'string' && val.startsWith('http');
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

export const assignmentsRoutes = new Elysia({ prefix: "/api/surveys" })
    // Get assignments for a survey (paginated — supports both offset and cursor)
    .get(
        "/:id/assignments",
        async ({ params, query: queryParams }) => {
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
                         ${labelData.data}::text ILIKE ${searchStr})`
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
                        sql`(${assignments.dateSynced}, ${assignments.id}) < (${cursorDate}::timestamptz, ${cursorId})`
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
                })
                .from(assignments)
                .leftJoin(
                    labelData,
                    and(
                        eq(assignments.surveyConfigId, labelData.surveyConfigId),
                        eq(assignments.codeIdentity, labelData.codeIdentity)
                    )
                )
                .where(whereClause)
                .orderBy(desc(assignments.dateSynced), desc(assignments.id))
                .limit(limit + 1)
                .offset(!cursor && offset > 0 ? offset : 0);

            const hasMore = rows.length > limit;
            const records = rows.slice(0, limit).map(r => {
                const deep = extractVariables(r.dataJson);
                return {
                    ...r,
                    flatData: { ...deep, ...(r.flatData as object || {}) },
                    dataJson: undefined // Hide bulky raw json from UI
                };
            });

            // Build next cursor from last row
            let nextCursor: string | null = null;
            if (hasMore && records.length > 0) {
                const lastRow = rows[limit - 1]!;
                nextCursor = `${lastRow.dateSynced ? new Date(lastRow.dateSynced).toISOString() : ""}|${lastRow.id}`;
            }

            const countQuery = db
                .select({ count: sql`count(*)::int` })
                .from(assignments);

            if (q) {
                countQuery.leftJoin(
                    labelData,
                    and(
                        eq(assignments.surveyConfigId, labelData.surveyConfigId),
                        eq(assignments.codeIdentity, labelData.codeIdentity)
                    )
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
        }
    )

    // Export assignments to Excel
    .get(
        "/:id/assignments/export",
        async ({ params, query, request, set }) => {
            const q = query.q as string | undefined;

            // Resolve the public base URL for vault image links in the exported file.
            // Priority: PUBLIC_BASE_URL env var → request Origin header → relative path
            const baseUrl = process.env.PUBLIC_BASE_URL?.replace(/\/$/, '')
                ?? (request.headers.get('origin') || '');

            // 1. Build base WHERE clause
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
                         ${labelData.data}::text ILIKE ${searchStr})`
                )!;
            }

            // 2. Fetch all assignments for this survey (no limit for export)
            const rows = await db
                .select({
                    id: assignments.id,
                    codeIdentity: assignments.codeIdentity,
                    surveyPeriodId: assignments.surveyPeriodId,
                    assignmentStatusAlias: assignments.assignmentStatusAlias,
                    currentUserUsername: assignments.currentUserUsername,
                    flatData: assignments.flatData,
                    dataJson: assignments.dataJson,
                    dateModifiedRemote: assignments.dateModifiedRemote,
                    dateSynced: assignments.dateSynced,
                    labelData: labelData.data,
                    localImagePaths: assignments.localImagePaths,
                })
                .from(assignments)
                .leftJoin(
                    labelData,
                    and(
                        eq(assignments.surveyConfigId, labelData.surveyConfigId),
                        eq(assignments.codeIdentity, labelData.codeIdentity)
                    )
                )
                .where(baseWhere)
                .orderBy(desc(assignments.dateSynced));

            if (!rows.length) {
                set.status = 404;
                return { error: "No data to export" };
            }

            // 3. Dynamic Header Discovery
            const dynamicKeys = new Set<string>();
            const labelKeys = new Set<string>();
            
            rows.forEach(row => {
                const deep = extractVariables(row.dataJson);
                const flat = { ...deep, ...(row.flatData as object || {}) };
                if (flat && typeof flat === 'object') {
                    Object.keys(flat).forEach(k => dynamicKeys.add(k));
                }
                if (row.labelData && typeof row.labelData === 'object') {
                    Object.keys(row.labelData).forEach(k => labelKeys.add(k));
                }
            });

            const sortedDynamicKeys = Array.from(dynamicKeys).sort();
            const sortedLabelKeys = Array.from(labelKeys).sort();

            // 4. Construct Headers
            const baseHeaders = [
                "ID", "Code Identity", "Status", "User", "Date Modified (Remote)", "Date Synced"
            ];
            const headers = [...baseHeaders, ...sortedDynamicKeys, ...sortedLabelKeys.map(k => `[Label] ${k}`)];

            // 5. Build Data Rows
            const wsData = [headers];
            
            rows.forEach(row => {
                const deep = extractVariables(row.dataJson);
                const flat = { ...deep, ...(row.flatData as object || {}) } as Record<string, any>;
                const labels = (row.labelData || {}) as Record<string, any>;
                // localImagePaths: { columnName -> "survey-images/{id}/{col}.jpg" }
                const vaultPaths = (row.localImagePaths || {}) as Record<string, string>;

                const rowValues = [
                    row.id,
                    row.codeIdentity,
                    row.assignmentStatusAlias,
                    row.currentUserUsername,
                    row.dateModifiedRemote,
                    row.dateSynced ? new Date(row.dateSynced).toLocaleString('id-ID') : "",
                    ...sortedDynamicKeys.map(k => {
                        // Replace image column value with permanent vault URL if available
                        if (vaultPaths[k]) {
                            return `${baseUrl}/storage/view/${vaultPaths[k]}`;
                        }
                        const val = flat[k];
                        return typeof val === 'object' ? JSON.stringify(val) : (val ?? "");
                    }),
                    ...sortedLabelKeys.map(k => {
                        const val = labels[k];
                        return typeof val === 'object' ? JSON.stringify(val) : (val ?? "");
                    })
                ];
                wsData.push(rowValues);
            });

            // 6. Generate Excel
            const wb = XLSX.utils.book_new();
            const ws = XLSX.utils.aoa_to_sheet(wsData);

            // Auto-width adjustment (basic)
            ws["!cols"] = headers.map(h => ({ wch: Math.max(h.length, 12) }));

            XLSX.utils.book_append_sheet(wb, ws, "Assignments");
            const buffer = XLSX.write(wb, { type: "buffer", bookType: "xlsx" });

            const filename = `export_survey_${params.id.substring(0, 8)}_${new Date().toISOString().split('T')[0]}.xlsx`;

            return new Response(buffer, {
                headers: {
                    "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "Content-Disposition": `attachment; filename="${filename}"`,
                },
            });
        }
    )

    // Get stats for a survey
    .get("/:id/stats", async ({ params, set }) => {
        try {
            const result = await db
                .select({
                    total: count(),
                    open: count(
                        sql`CASE WHEN ${assignments.assignmentStatusAlias} ILIKE '%open%' THEN 1 END`
                    ),
                    submitted: count(
                        sql`CASE WHEN ${assignments.assignmentStatusAlias} ILIKE '%submitted%' THEN 1 END`
                    ),
                    rejected: count(
                        sql`CASE WHEN ${assignments.assignmentStatusAlias} ILIKE '%rejected%' THEN 1 END`
                    ),
                })
                .from(assignments)
                .where(eq(assignments.surveyConfigId, params.id));

            const stats = result[0] || { total: 0, open: 0, submitted: 0, rejected: 0 };
            
            // Ensure all values are numbers (DB might return strings for count)
            return {
                total: Number(stats.total || 0),
                open: Number(stats.open || 0),
                submitted: Number(stats.submitted || 0),
                rejected: Number(stats.rejected || 0)
            };
        } catch (error) {
            console.error(`Error fetching stats for survey ${params.id}:`, error);
            // Fallback to empty stats instead of 500
            return { total: 0, open: 0, submitted: 0, rejected: 0 };
        }
    });

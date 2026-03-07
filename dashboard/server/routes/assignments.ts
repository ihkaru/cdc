import { Elysia, t } from "elysia";
import { db } from "../db";
import { assignments, labelData } from "../db/schema";
import { eq, desc, sql, count, and, lt } from "drizzle-orm";

export const assignmentsRoutes = new Elysia({ prefix: "/api/surveys" })
    // Get assignments for a survey (paginated — supports both offset and cursor)
    .get(
        "/:id/assignments",
        async ({ params, query }) => {
            const limit = Math.min(Number(query.limit) || 50, 200);
            const cursor = query.cursor as string | undefined;

            // Build base WHERE clause
            const baseWhere = eq(assignments.surveyConfigId, params.id);

            // Cursor-based pagination: use dateSynced + id as composite cursor
            // Format: "2026-03-04T15:03:00.234Z|some-uuid-id"
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
                    labelData: labelData.data,
                })
                .from(assignments)
                .leftJoin(
                    labelData,
                    sql`${assignments.surveyConfigId} = ${labelData.surveyConfigId} AND ${assignments.codeIdentity} = ${labelData.codeIdentity}`
                )
                .where(whereClause)
                .orderBy(desc(assignments.dateSynced), desc(assignments.id))
                .limit(limit + 1); // Fetch one extra to determine hasMore

            const hasMore = rows.length > limit;
            const data = hasMore ? rows.slice(0, limit) : rows;

            // Build next cursor from last row
            let nextCursor: string | null = null;
            if (hasMore && data.length > 0) {
                const lastRow = data[data.length - 1]!;
                nextCursor = `${lastRow.dateSynced ? new Date(lastRow.dateSynced).toISOString() : ""}|${lastRow.id}`;
            }

            // Approximate total count using pg_class statistics (O(1) instead of O(N))
            // Falls back to exact count for very small tables
            const [approx] = await db.execute(sql`
                SELECT CASE
                    WHEN c.reltuples < 1000 THEN (
                        SELECT count(*)::int FROM assignments WHERE survey_config_id = ${params.id}
                    )
                    ELSE (
                        SELECT (c.reltuples * (
                            SELECT count(*)::float / greatest(count(*)::float, 1)
                            FROM assignments
                            WHERE survey_config_id = ${params.id}
                            LIMIT 1
                        ))::int
                        FROM pg_class c WHERE c.relname = 'assignments'
                    )
                END as estimated_total
                FROM pg_class c WHERE c.relname = 'assignments'
            `) as unknown as { estimated_total: number }[];

            // Also support legacy offset pagination for backward compat
            const page = Number(query.page) || 1;

            return {
                data,
                pagination: {
                    page,
                    limit,
                    total: approx?.estimated_total || 0,
                    totalPages: Math.ceil((approx?.estimated_total || 0) / limit),
                    hasMore,
                    nextCursor,
                },
            };
        }
    )

    // Get stats for a survey
    .get("/:id/stats", async ({ params }) => {
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

        return result[0] || { total: 0, open: 0, submitted: 0, rejected: 0 };
    });

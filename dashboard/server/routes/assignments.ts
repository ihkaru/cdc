import { Elysia, t } from "elysia";
import { db } from "../db";
import { assignments, labelData } from "../db/schema";
import { eq, desc, sql, count, and, lt } from "drizzle-orm";

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
            const data = hasMore ? rows.slice(0, limit) : rows;

            // Build next cursor from last row
            let nextCursor: string | null = null;
            if (hasMore && data.length > 0) {
                const lastRow = data[data.length - 1]!;
                nextCursor = `${lastRow.dateSynced ? new Date(lastRow.dateSynced).toISOString() : ""}|${lastRow.id}`;
            }

            // Fix: Exact count for specific surveyConfigId
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
                data,
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

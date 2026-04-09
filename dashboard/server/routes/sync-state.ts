import { Elysia } from "elysia";
import { db } from "../db";
import { assignments, syncLogs } from "../db/schema";
import { eq, and, desc, sql } from "drizzle-orm";

const RPA_URL = process.env.RPA_URL || "http://vpn:8000";

export const syncStateRoutes = new Elysia({ prefix: "/api/surveys" })
    .get("/:id/sync-dashboard-state", async ({ params }) => {
        const surveyId = params.id;

        // 1. Fetch RPA Robot Status
        const robotStatusPromise = fetch(`${RPA_URL}/status`)
            .then(res => res.json())
            .catch(() => ({ is_running: false, error: "RPA service offline" }));

        // 2. Fetch Mirroring Progress
        const mirroringProgressPromise = db
            .select({
                total: sql<number>`count(*)`,
                mirrored: sql<number>`count(*) filter (where local_image_mirrored = true)`
            })
            .from(assignments)
            .where(eq(assignments.surveyConfigId, surveyId));

        // 3. Fetch Skipped Records Identifiers (Now refers to pending items actually missing images after checking, though we just show unmirrored things for debug)
        const skippedListPromise = db
            .select({
                id: assignments.id,
                codeIdentity: assignments.codeIdentity,
                status: assignments.assignmentStatusAlias,
                user: assignments.currentUserUsername
            })
            .from(assignments)
            .where(
                and(
                    eq(assignments.surveyConfigId, surveyId),
                    eq(assignments.localImageMirrored, false)
                )
            )
            .limit(50);

        // 4. Fetch Latest Logs (Last 5)
        const logsPromise = db
            .select()
            .from(syncLogs)
            .where(eq(syncLogs.surveyConfigId, surveyId))
            .orderBy(desc(syncLogs.startedAt))
            .limit(5);

        // Execute all in parallel
        const [robotStatus, [progress], skippedList, logs] = await Promise.all([
            robotStatusPromise,
            mirroringProgressPromise,
            skippedListPromise,
            logsPromise
        ]);

        return {
            robotStatus,
            mirroring: {
                total: Number(progress?.total || 0),
                mirrored: Number(progress?.mirrored || 0),
                skipped: Number(progress?.skipped || 0),
                remaining: Math.max(0, Number(progress?.total || 0) - Number(progress?.mirrored || 0) - Number(progress?.skipped || 0)),
                skippedList
            },
            logs
        };
    });

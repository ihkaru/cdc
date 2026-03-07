import { Elysia } from "elysia";
import { db } from "../db";
import { syncLogs, surveyConfigs } from "../db/schema";
import { eq, desc } from "drizzle-orm";

export const logsRoutes = new Elysia({ prefix: "/api/surveys" })
    .get("/:id/logs", async ({ params }) => {
        const rows = await db
            .select()
            .from(syncLogs)
            .where(eq(syncLogs.surveyConfigId, params.id))
            .orderBy(desc(syncLogs.startedAt))
            .limit(50);
        return rows;
    });

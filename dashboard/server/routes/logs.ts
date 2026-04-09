import { Elysia } from "elysia";
import { db } from "../db";
import { syncLogs, assignments } from "../db/schema";
import { eq, desc, sql, count, and } from "drizzle-orm";
import * as XLSX from "xlsx";

export const logsRoutes = new Elysia({ prefix: "/api/surveys" })
    .get("/:id/logs", async ({ params }) => {
        const rows = await db
            .select()
            .from(syncLogs)
            .where(eq(syncLogs.surveyConfigId, params.id))
            .orderBy(desc(syncLogs.startedAt))
            .limit(50);
        return rows;
    })

    // Get mirroring status for a survey
    .get("/:id/mirroring-status", async ({ params }) => {
        const [result] = await db
            .select({
                total: count(),
                processed: count(sql`CASE WHEN ${assignments.localImageMirrored} = true THEN 1 END`),
                pending: count(sql`CASE WHEN ${assignments.localImageMirrored} = false THEN 1 END`),
            })
            .from(assignments)
            .where(eq(assignments.surveyConfigId, params.id));
        
        return result || { total: 0, processed: 0, pending: 0 };
    })

    // Export logs to Excel
    .get("/:id/logs/export", async ({ params }) => {
        const rows = await db
            .select()
            .from(syncLogs)
            .where(eq(syncLogs.surveyConfigId, params.id))
            .orderBy(desc(syncLogs.startedAt));

        if (!rows.length) return { error: "No logs found" };

        const wsData = [
            ["ID", "Started At", "Finished At", "Status", "Fetched", "New", "Updated", "Skipped", "Failed", "Images Total", "Images Mirrored", "Notes", "Timing: Login (ms)", "Timing: Metadata (ms)", "Timing: Fetch (ms)", "Timing: Upsert (ms)", "Timing: Total (ms)"]
        ];

        rows.forEach(log => {
            const t = (log.timings as any) || {};
            wsData.push([
                log.id.toString(),
                log.startedAt ? new Date(log.startedAt).toLocaleString('id-ID') : "-",
                log.finishedAt ? new Date(log.finishedAt).toLocaleString('id-ID') : "-",
                log.status || "-",
                (log.totalFetched || 0).toString(),
                (log.totalNew || 0).toString(),
                (log.totalUpdated || 0).toString(),
                (log.totalSkipped || 0).toString(),
                (log.totalFailed || 0).toString(),
                (log.totalImages || 0).toString(),
                (log.imagesMirrored || 0).toString(),
                log.notes || "-",
                (t.login || 0).toString(),
                (t.metadata || 0).toString(),
                (t.fetch || 0).toString(),
                (t.upsert || 0).toString(),
                (t.total || 0).toString()
            ]);
        });

        const wb = XLSX.utils.book_new();
        const ws = XLSX.utils.aoa_to_sheet(wsData);
        XLSX.utils.book_append_sheet(wb, ws, "Sync Logs");
        const buffer = XLSX.write(wb, { type: "buffer", bookType: "xlsx" });

        const filename = `logs_survey_${params.id.substring(0, 8)}_${new Date().toISOString().split('T')[0]}.xlsx`;

        return new Response(buffer, {
            headers: {
                "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "Content-Disposition": `attachment; filename="${filename}"`,
            },
        });
    });

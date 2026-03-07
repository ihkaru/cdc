import { db } from "../db";
import { assignments } from "../db/schema";
import { isNotNull, isNull, eq } from "drizzle-orm";

function extractVariables(dataJson: any): Record<string, string | number> {
    const vars: Record<string, string | number> = {};
    if (!dataJson || !dataJson.content || !Array.isArray(dataJson.content.data)) {
        return vars;
    }
    for (const item of dataJson.content.data) {
        if (item.dataKey) {
            let val = item.value;
            if (typeof val === 'string' && val.trim() !== '') {
                const numeric = Number(val);
                if (!isNaN(numeric)) val = numeric;
            }
            vars[item.dataKey] = val;
        }
    }
    return vars;
}

async function runBackfill() {
    console.log("Starting backfill for flatData column...");

    // Process in batches
    const limit = 500;
    let offset = 0;
    let totalProcessed = 0;

    while (true) {
        const batch = await db
            .select({ id: assignments.id, dataJson: assignments.dataJson })
            .from(assignments)
            .where(isNull(assignments.flatData))
            .limit(limit)
            .offset(offset);

        if (batch.length === 0) break;

        for (const row of batch) {
            const flatData = extractVariables(row.dataJson);
            await db
                .update(assignments)
                .set({ flatData })
                .where(eq(assignments.id, row.id));
        }

        totalProcessed += batch.length;
        console.log(`Processed ${totalProcessed} records...`);
        // We aren't incrementing offset because we are updating rows and the next query for isNull(flatData) will pick up new ones.
    }

    console.log(`Backfill completed. Total processed: ${totalProcessed}`);
    process.exit(0);
}

runBackfill().catch(e => {
    console.error(e);
    process.exit(1);
});

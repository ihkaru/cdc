import { db } from "../db";
import { assignments } from "../db/schema";
import { eq } from "drizzle-orm";

function extractVariables(dataJson: any): Record<string, any> {
    const vars: Record<string, any> = {};
    if (!dataJson) return vars;

    const dataObj = typeof dataJson === 'string' ? JSON.parse(dataJson) : dataJson;

    for (const key in dataObj) {
        if (typeof dataObj[key] !== 'object' && typeof dataObj[key] !== 'string') {
            vars[key] = dataObj[key];
        } else if (typeof dataObj[key] === 'string') {
            const trimmed = dataObj[key].trim();
            if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) {
                vars[key] = dataObj[key];
            }
        }
    }

    if (dataObj.pre_defined_data) {
        try {
            const preObj = typeof dataObj.pre_defined_data === 'string'
                ? JSON.parse(dataObj.pre_defined_data)
                : dataObj.pre_defined_data;

            if (preObj && Array.isArray(preObj.predata)) {
                preObj.predata.forEach((item: any) => {
                    if (item && item.dataKey) vars[item.dataKey] = item.answer;
                });
            }
        } catch (e) { }
    }

    if (dataObj.content) {
        try {
            const contentObj = typeof dataObj.content === 'string'
                ? JSON.parse(dataObj.content)
                : dataObj.content;

            if (contentObj && Array.isArray(contentObj.data)) {
                contentObj.data.forEach((item: any) => {
                    if (item && item.dataKey) vars[item.dataKey] = item.answer;
                });
            }
        } catch (e) { }
    }

    return vars;
}

async function backfill() {
    console.log("Starting backfill of flat_data...");
    const limit = 500;
    let offset = 0;
    let updatedCount = 0;

    while (true) {
        const batch = await db.select({
            id: assignments.id,
            data_json: assignments.dataJson
        }).from(assignments).limit(limit).offset(offset);

        if (batch.length === 0) break;

        for (const row of batch) {
            const dataObj = (typeof row.data_json === 'string' ? JSON.parse(row.data_json) : row.data_json) || {};
            const flatData = extractVariables(dataObj);

            await db.update(assignments)
                .set({ flatData })
                .where(eq(assignments.id, row.id));

            updatedCount++;
            if (updatedCount % 50 === 0) console.log(`Updated ${updatedCount} rows...`);
        }

        offset += limit;
    }

    console.log(`Backfill complete. Total items flattened: ${updatedCount}`);
    process.exit(0);
}

backfill().catch(console.error);

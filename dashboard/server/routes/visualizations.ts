import { Elysia } from "elysia";
import { db } from "../db";
import { visualizationConfigs, labelData, labelSchemas, assignments } from "../db/schema";
import { eq, sql, and } from "drizzle-orm";

function flattenObj(obj: any, prefix = ''): Record<string, any> {
    let result: Record<string, any> = {};
    if (!obj || typeof obj !== 'object') return result;
    for (const key in obj) {
        if (obj[key] === null || obj[key] === undefined) continue;
        const newKey = prefix ? `${prefix}.${key}` : key;
        if (typeof obj[key] === 'object' && !Array.isArray(obj[key])) {
            Object.assign(result, flattenObj(obj[key], newKey));
        } else {
            result[newKey] = obj[key];
        }
    }
    return result;
}

// Extract variables from FASIH 'content.data' or 'pre_defined_data.predata' format
function extractVariables(dataJson: any): Record<string, any> {
    const vars: Record<string, any> = {};
    if (!dataJson) return vars;

    const dataObj = typeof dataJson === 'string' ? JSON.parse(dataJson) : dataJson;

    // Base root metadata
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

    // Extract from pre_defined_data
    if (dataObj.pre_defined_data) {
        try {
            const preObj = typeof dataObj.pre_defined_data === 'string'
                ? JSON.parse(dataObj.pre_defined_data)
                : dataObj.pre_defined_data;

            if (preObj && Array.isArray(preObj.predata)) {
                preObj.predata.forEach((item: any) => {
                    if (item && item.dataKey) {
                        vars[item.dataKey] = item.answer;
                    }
                });
            }
        } catch (e) {
            // ignore
        }
    }

    // Extract from content (for other survey phases)
    if (dataObj.content) {
        try {
            const contentObj = typeof dataObj.content === 'string'
                ? JSON.parse(dataObj.content)
                : dataObj.content;

            if (contentObj && Array.isArray(contentObj.data)) {
                contentObj.data.forEach((item: any) => {
                    if (item && item.dataKey) {
                        vars[item.dataKey] = item.answer;
                    }
                });
            }
        } catch (e) {
            // ignore
        }
    }

    return vars;
}

async function buildAndExecuteChartQuery(chartType: string, config: Record<string, any>, surveyId: string) {
    const sanitize = (val: string) => val ? val.replace(/'/g, "''") : "";

    const getColumnSql = (col: string) => {
        if (!col) return "NULL";
        const base = ["assignmentStatusAlias", "currentUserUsername", "dateModifiedRemote", "codeIdentity"];
        if (base.includes(col)) {
            const snake = col.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`);
            return `"assignments"."${snake}"`;
        }

        if (col === "current_user_fullname") {
            return `"assignments"."data_json"->>'current_user_fullname'`;
        }

        const safeCol = sanitize(col);
        return `COALESCE("assignments"."flat_data"->>'${safeCol}', "label_data"."data"->>'${safeCol}')`;
    };

    const getFilterSql = (filters: any[]) => {
        if (!filters || filters.length === 0) return "";
        const conditions = filters.map(f => {
            const col = getColumnSql(f.column);
            const val = sanitize(String(f.value));
            switch (f.operator) {
                case 'equals': return `${col} = '${val}'`;
                case 'not_equals': return `${col} != '${val}'`;
                case 'contains': return `LOWER(CAST(${col} AS TEXT)) LIKE LOWER('%${val}%')`;
                case 'greater_than': return `CAST(NULLIF(TRIM(CAST(${col} AS TEXT)), '') AS NUMERIC) > ${Number(val) || 0}`;
                case 'less_than': return `CAST(NULLIF(TRIM(CAST(${col} AS TEXT)), '') AS NUMERIC) < ${Number(val) || 0}`;
                default: return `${col} = '${val}'`;
            }
        });
        return ` FILTER (WHERE ${conditions.join(' AND ')})`;
    };

    const getAggregateSql = (metric: any) => {
        const colSql = getColumnSql(metric.column);
        const filterSql = getFilterSql(metric.filters);
        const agg = metric.aggregation || 'count';

        if (agg === "count") return `COUNT(${colSql})${filterSql}`; // Count non-nulls

        // Cast to numeric to allow math aggregations. Use NULLIF to avoid casting empty strings.
        const numericSql = `CAST(NULLIF(TRIM(${colSql}), '') AS NUMERIC)`;

        switch (agg) {
            case "sum": return `SUM(${numericSql})${filterSql}`;
            case "avg": return `AVG(${numericSql})${filterSql}`;
            case "min": return `MIN(${numericSql})${filterSql}`;
            case "max": return `MAX(${numericSql})${filterSql}`;
            default: return `SUM(${numericSql})${filterSql}`;
        }
    };

    // Normalize config to support multiple metrics Backward Compatibility
    let metrics: any[] = config.metrics || [];
    if (metrics.length === 0) {
        if (chartType === "scorecard") {
            metrics = [{ id: "m1", label: config.label || config.metricColumn, column: config.metricColumn, aggregation: config.aggregation }];
        } else if (chartType !== "map_point") {
            metrics = [{ id: "m1", label: config.label || config.yColumn, column: config.yColumn, aggregation: config.aggregation }];
        }
    }

    // Separate regular vs calculated metrics
    const regularMetrics = metrics.filter(m => m.type !== 'calculated');
    const calcMetrics = metrics.filter(m => m.type === 'calculated');

    // Build SELECT expressions for regular metrics
    const metricSelects = regularMetrics.map((m, idx) => {
        return `${getAggregateSql(m)} as "metric_${m.id || idx}"`;
    });

    const evaluateCalculations = (row: any) => {
        // Create context obj `{ m1: 10, m2: 5 }`
        const ctx: Record<string, number> = {};
        regularMetrics.forEach((m, idx) => {
            const key = `metric_${m.id || idx}`;
            ctx[m.id || String(idx)] = Number(row[key]) || 0;
        });

        // Evaluate calc metrics safely
        calcMetrics.forEach((cm, idx) => {
            try {
                // VERY basic expression evaluator (avoids eval)
                // Assuming simple algebraic like "m1 / m2" or "m1 * 100"
                const expr = cm.expression || "0";
                // simple replacement of variables
                let mathStr = expr;
                for (const key of Object.keys(ctx).sort((a, b) => b.length - a.length)) {
                    mathStr = mathStr.replace(new RegExp(`\\b${key}\\b`, 'g'), String(ctx[key]));
                }
                const result = new Function(`return ${mathStr}`)();
                row[`metric_${cm.id || idx}`] = Number(result) || 0;
            } catch {
                row[`metric_${cm.id || idx}`] = 0;
            }
        });
        return row;
    };


    if (chartType === "scorecard") {
        const query = sql`
            SELECT 
                ${sql.raw(metricSelects.join(', \n                '))},
                COUNT(*) as "total_rows_count"
            FROM assignments
            LEFT JOIN label_data ON assignments.code_identity = label_data.code_identity AND assignments.survey_config_id = label_data.survey_config_id
            WHERE assignments.survey_config_id = ${surveyId}
        `;

        const queryRes = await db.execute(query) as unknown as Record<string, unknown>[];
        let row = queryRes[0] as any || {};
        row = evaluateCalculations(row);

        const primaryMetric = metrics[0];
        const valCol = `metric_${primaryMetric.id || 0}`;

        return {
            type: "scorecard",
            value: Number(row[valCol]) || 0,
            label: primaryMetric.label,
            count: Number(row.total_rows_count) || 0,
            all_metrics: row,
        };
    }

    if (chartType === "map_point") {
        const { latColumn, lngColumn, colorBy, popupFields } = config;

        if (!latColumn || !lngColumn) {
            return { error: "latColumn and lngColumn are required for map_point" };
        }

        const latSql = getColumnSql(latColumn);
        const lngSql = getColumnSql(lngColumn);
        const colorSql = colorBy ? getColumnSql(colorBy) : "NULL";

        // Additional fields to show in popups — {column, label}[] alias pairs
        // Accepts both string[] (legacy) and {column, label}[] (new format)
        const rawPopupFields: any[] = Array.isArray(popupFields) ? popupFields : [];
        const extraPopupFields = rawPopupFields
            .filter(f => f != null)
            .map((f, i) => ({
                column: typeof f === 'string' ? f : (f.column || ''),
                label: typeof f === 'string' ? f : (f.label || f.column || ''),
                idx: i
            }))
            .filter(f => f.column);

        const popupSelects = extraPopupFields.map(f => {
            const colSql = getColumnSql(f.column);
            return `${colSql} as "popup_${f.idx}_${sanitize(f.column)}"`;
        });

        // Build SELECT list
        const popupSelectsStr = popupSelects.length > 0 ? `, ${popupSelects.join(', ')}` : '';

        const groupByAliases = ['"lng"', '"lat"', '"color_val"'];
        extraPopupFields.forEach(f => {
            groupByAliases.push(`"popup_${f.idx}_${sanitize(f.column)}"`);
        });

        // Always append row count so front-end circle-radius sizing has a metric_count
        const metricRawStr = metricSelects.length > 0
            ? sql.raw(`${metricSelects.join(',\n                ')}, COUNT(*)::int as "metric_count"`)
            : sql.raw(`COUNT(*)::int as "metric_count"`);

        const query = sql`
            SELECT 
                ROUND(CAST(NULLIF(TRIM(CAST(${sql.raw(lngSql)} AS TEXT)), '') AS NUMERIC), 4) as "lng",
                ROUND(CAST(NULLIF(TRIM(CAST(${sql.raw(latSql)} AS TEXT)), '') AS NUMERIC), 4) as "lat",
                ${sql.raw(colorSql)} as "color_val"${sql.raw(popupSelectsStr)},
                ${metricRawStr}
            FROM assignments
            LEFT JOIN label_data ON assignments.code_identity = label_data.code_identity AND assignments.survey_config_id = label_data.survey_config_id
            WHERE assignments.survey_config_id = ${surveyId} 
              AND NULLIF(TRIM(CAST(${sql.raw(lngSql)} AS TEXT)), '') IS NOT NULL
              AND NULLIF(TRIM(CAST(${sql.raw(latSql)} AS TEXT)), '') IS NOT NULL
              AND NOT (ROUND(CAST(NULLIF(TRIM(CAST(${sql.raw(lngSql)} AS TEXT)), '') AS NUMERIC), 6) = 0
                  AND ROUND(CAST(NULLIF(TRIM(CAST(${sql.raw(latSql)} AS TEXT)), '') AS NUMERIC), 6) = 0)
            GROUP BY ${sql.raw(groupByAliases.join(', '))}
        `;

        const queryRes = await db.execute(query) as unknown as Record<string, unknown>[];

        // Attach the popup field metadata for the frontend to use when rendering labels
        const popupFieldMeta = extraPopupFields.map(f => ({
            key: `popup_${f.idx}_${sanitize(f.column)}`,
            label: f.label  // The user-provided alias label
        }));

        let res = queryRes.map(row => evaluateCalculations(row as any));

        return {
            type: "map_point",
            popupFieldMeta,
            data: res
        };
    }

    if (chartType === "bar_vertical" || chartType === "bar_horizontal" || chartType === "data_table") {
        const { xColumn, groupBy } = config;

        const catSql = getColumnSql(xColumn);
        const groupSql = groupBy ? getColumnSql(groupBy) : "NULL";

        const query = sql`
            SELECT 
                ${sql.raw(`COALESCE(${catSql}, 'Unknown')`)} as "category",
                ${sql.raw(groupBy ? `COALESCE(${groupSql}, 'Unknown')` : "NULL")} as "group_val",
                ${sql.raw(metricSelects.join(', \n                '))}
            FROM assignments
            LEFT JOIN label_data ON assignments.code_identity = label_data.code_identity AND assignments.survey_config_id = label_data.survey_config_id
            WHERE assignments.survey_config_id = ${surveyId}
            GROUP BY "category"${sql.raw(groupBy ? ', "group_val"' : '')}
            ORDER BY "category" ASC
        `;

        const queryRes = await db.execute(query) as unknown as Record<string, unknown>[];

        // Post-process calculated metrics
        let res = queryRes.map(row => evaluateCalculations(row as any));

        if (chartType === "data_table") {
            const columns = [
                { name: 'category', label: xColumn, align: 'left', field: 'category', sortable: true },
                ...(groupBy ? [{ name: 'group_val', label: groupBy, align: 'left', field: 'group_val', sortable: true }] : []),
                ...metrics.map((m, i) => ({
                    name: `metric_${m.id || i}`,
                    label: m.label || m.id,
                    align: 'right',
                    field: `metric_${m.id || i}`,
                    sortable: true
                }))
            ];
            return {
                type: "data_table",
                columns,
                rows: res
            };
        }

        if (groupBy) {
            // Ensure single metric for grouped bar chart (simplicity), or multi-metric without group_val
            const targetMetric = metrics[0];
            const valCol = `metric_${targetMetric.id || 0}`;

            const seriesMap = new Map<string, Map<string, number>>();
            const categories = new Set<string>();

            for (const row of res as any[]) {
                const xVal = String(row.category);
                const gVal = String(row.group_val);
                const val = Number(row[valCol]) || 0;

                categories.add(xVal);
                if (!seriesMap.has(gVal)) seriesMap.set(gVal, new Map());
                seriesMap.get(gVal)!.set(xVal, val);
            }

            const categoryArr = Array.from(categories).sort();
            const series = Array.from(seriesMap.entries()).map(([name, dataMap]) => ({
                name,
                data: categoryArr.map(cat => dataMap.get(cat) ?? 0),
            }));

            return {
                type: chartType,
                categories: categoryArr,
                series,
            };
        } else {
            const categories = [];
            const rowsArray = res as any[];
            for (const row of rowsArray) {
                categories.push(String(row.category));
            }

            const series = metrics.map((m, i) => {
                const valCol = `metric_${m.id || i}`;
                return {
                    name: m.label || m.id,
                    data: rowsArray.map(r => Number(r[valCol]) || 0)
                };
            });

            return {
                type: chartType,
                categories,
                series,
            };
        }
    }

    return { error: "Unknown chart type" };
}

export const visualizationsRoutes = new Elysia({ prefix: "/api/surveys" })

    // List all visualization configs for a survey
    .get("/:id/visualizations", async ({ params }) => {
        const rows = await db
            .select()
            .from(visualizationConfigs)
            .where(eq(visualizationConfigs.surveyConfigId, params.id))
            .orderBy(visualizationConfigs.sortOrder);
        return rows;
    })

    // Get comprehensive schema for visualizations (assignments + labels)
    .get("/:id/visualizations/schema", async ({ params }) => {
        const columns = new Map<string, "dimension" | "measure">();

        // 1. Label schemas if exist
        const [labelSchemaRow] = await db
            .select()
            .from(labelSchemas)
            .where(eq(labelSchemas.surveyConfigId, params.id))
            .limit(1);

        if (labelSchemaRow && Array.isArray(labelSchemaRow.columns)) {
            for (const col of labelSchemaRow.columns as any[]) {
                columns.set(col.name, col.type);
            }
        }

        // 2. Base assignment columns
        columns.set("assignmentStatusAlias", "dimension");
        columns.set("currentUserUsername", "dimension");
        columns.set("dateModifiedRemote", "dimension");
        columns.set("codeIdentity", "dimension");
        columns.set("current_user_fullname", "dimension");

        // 3. Inspect assignments flatData
        const assignmentSamples = await db
            .select({ flatData: assignments.flatData })
            .from(assignments)
            .where(eq(assignments.surveyConfigId, params.id))
            .limit(150);

        const dataValues = new Map<string, any[]>();
        for (const row of assignmentSamples) {
            const vars = (row.flatData as Record<string, any>) || {};
            for (const key in vars) {
                if (!dataValues.has(key)) dataValues.set(key, []);
                dataValues.get(key)!.push(vars[key]);
            }
        }

        // Collect sample value per column (first non-empty, non-array, non-object scalar)
        const sampleValues = new Map<string, string>();
        for (const [key, values] of dataValues.entries()) {
            const sample = values.find(v =>
                v !== null && v !== undefined &&
                typeof v !== 'object' &&
                String(v).trim() !== ''
            );
            if (sample !== undefined) sampleValues.set(key, String(sample));
        }

        for (const [key, values] of dataValues.entries()) {
            if (columns.has(key)) continue;

            const nonEmpty = values.filter(v => v !== null && v !== undefined && String(v).trim() !== "");
            if (nonEmpty.length === 0) {
                columns.set(key, "dimension");
                continue;
            }
            const numericCount = nonEmpty.filter(v => typeof v === 'number' || (typeof v === 'string' && !isNaN(Number(v)))).length;
            const type = numericCount / nonEmpty.length > 0.8 ? "measure" : "dimension";
            columns.set(key, type);
        }

        // Sort columns alphabetically
        const sortedColumns = Array.from(columns.entries())
            .map(([name, type]) => ({ name, type, sample: sampleValues.get(name) ?? null }))
            .sort((a, b) => a.name.localeCompare(b.name));

        return { columns: sortedColumns };
    })

    // Create a new visualization config
    .post("/:id/visualizations", async ({ params, body, set }) => {
        try {
            const { name, chartType, config } = body as {
                name: string;
                chartType: string;
                config: Record<string, any>;
            };

            if (!name || !chartType || !config) {
                set.status = 400;
                return { error: "name, chartType, and config are required" };
            }

            const validTypes = ["scorecard", "bar_vertical", "bar_horizontal", "data_table", "map_point"];
            if (!validTypes.includes(chartType)) {
                set.status = 400;
                return { error: `chartType must be one of: ${validTypes.join(", ")}` };
            }

            // Get next sort order
            const [last] = await db
                .select({ maxSort: sql<number>`COALESCE(MAX(${visualizationConfigs.sortOrder}), 0)` })
                .from(visualizationConfigs)
                .where(eq(visualizationConfigs.surveyConfigId, params.id));

            const [inserted] = await db.insert(visualizationConfigs).values({
                surveyConfigId: params.id,
                name,
                chartType,
                config,
                sortOrder: (last?.maxSort || 0) + 1,
            }).returning();

            return inserted;
        } catch (e: any) {
            set.status = 500;
            return { error: e.message };
        }
    })

    // Reorder visualizations
    .put("/:id/visualizations/reorder", async ({ params, body, set }) => {
        try {
            const items = body as { id: number; sortOrder: number }[];
            if (!Array.isArray(items)) {
                set.status = 400;
                return { error: "Expected an array of {id, sortOrder}" };
            }

            // Execute batch update within a transaction to guarantee consistency
            await db.transaction(async (tx) => {
                for (const item of items) {
                    await tx
                        .update(visualizationConfigs)
                        .set({ sortOrder: item.sortOrder })
                        .where(
                            and(
                                eq(visualizationConfigs.id, item.id),
                                eq(visualizationConfigs.surveyConfigId, params.id)
                            )
                        );
                }
            });

            return { success: true };
        } catch (e: any) {
            set.status = 500;
            return { error: e.message };
        }
    })

    // Update a visualization config
    .put("/:id/visualizations/:vizId", async ({ params, body, set }) => {
        try {
            const vizId = Number(params.vizId);
            const { name, chartType, config } = body as {
                name?: string;
                chartType?: string;
                config?: Record<string, any>;
            };

            const updates: Record<string, any> = {};
            if (name) updates.name = name;
            if (chartType) updates.chartType = chartType;
            if (config) updates.config = config;

            const [updated] = await db
                .update(visualizationConfigs)
                .set(updates)
                .where(
                    and(
                        eq(visualizationConfigs.id, vizId),
                        eq(visualizationConfigs.surveyConfigId, params.id)
                    )
                )
                .returning();

            if (!updated) {
                set.status = 404;
                return { error: "Visualization not found" };
            }

            return updated;
        } catch (e: any) {
            set.status = 500;
            return { error: e.message };
        }
    })

    // Generate preview data without saving
    .post("/:id/visualizations/preview", async ({ params, body, set }) => {
        try {
            const { chartType, config } = body as {
                chartType: string;
                config: Record<string, any>;
            };

            if (!chartType || !config) {
                set.status = 400;
                return { error: "chartType and config are required" };
            }

            return await buildAndExecuteChartQuery(chartType, config, params.id);
        } catch (e: any) {
            set.status = 500;
            return { error: e.message };
        }
    })

    // Delete a visualization config
    .delete("/:id/visualizations/:vizId", async ({ params }) => {
        const vizId = Number(params.vizId);
        await db
            .delete(visualizationConfigs)
            .where(
                and(
                    eq(visualizationConfigs.id, vizId),
                    eq(visualizationConfigs.surveyConfigId, params.id)
                )
            );
        return { success: true };
    })

    // Get aggregated data for a visualization
    .get("/:id/visualizations/:vizId/data", async ({ params, set }) => {
        const vizId = Number(params.vizId);

        // Get the viz config
        const [viz] = await db
            .select()
            .from(visualizationConfigs)
            .where(
                and(
                    eq(visualizationConfigs.id, vizId),
                    eq(visualizationConfigs.surveyConfigId, params.id)
                )
            );

        if (!viz) {
            set.status = 404;
            return { error: "Visualization not found" };
        }

        const config = viz.config as Record<string, any>;

        return await buildAndExecuteChartQuery(viz.chartType, config, params.id);
    })

    // Generate an AI context prompt with schema and data samples
    .get("/:id/visualizations/ai-context", async ({ params, set }) => {
        try {
            // 1. Get schema
            const columns = new Map<string, string>();

            const [labelSchemaRow] = await db
                .select()
                .from(labelSchemas)
                .where(eq(labelSchemas.surveyConfigId, params.id))
                .limit(1);

            if (labelSchemaRow && Array.isArray(labelSchemaRow.columns)) {
                for (const col of labelSchemaRow.columns as any[]) {
                    columns.set(col.name, col.type);
                }
            }

            columns.set("assignmentStatusAlias", "dimension");
            columns.set("currentUserUsername", "dimension");
            columns.set("dateModifiedRemote", "dimension");
            columns.set("codeIdentity", "dimension");
            columns.set("current_user_fullname", "dimension");

            // 2. Get samples
            const samples = await db
                .select({
                    assignmentStatusAlias: assignments.assignmentStatusAlias,
                    currentUserUsername: assignments.currentUserUsername,
                    dateModifiedRemote: assignments.dateModifiedRemote,
                    codeIdentity: assignments.codeIdentity,
                    flatData: assignments.flatData,
                    data_json: assignments.dataJson,
                    labelData: labelData.data
                })
                .from(assignments)
                .leftJoin(labelData, and(
                    eq(assignments.codeIdentity, labelData.codeIdentity),
                    eq(assignments.surveyConfigId, labelData.surveyConfigId)
                ))
                .where(eq(assignments.surveyConfigId, params.id))
                .limit(3);

            const sampleRows = samples.map(s => {
                let dataJsonObj: any = {};
                try {
                    dataJsonObj = (typeof s.data_json === 'string' ? JSON.parse(s.data_json) : s.data_json) || {};
                } catch (e) { /* ignore invalid json string like 'Failed queued' */ }
                const extractedFields = extractVariables(dataJsonObj);

                const row: any = {
                    assignmentStatusAlias: s.assignmentStatusAlias,
                    currentUserUsername: s.currentUserUsername,
                    dateModifiedRemote: s.dateModifiedRemote,
                    codeIdentity: s.codeIdentity,
                    current_user_fullname: dataJsonObj?.current_user_fullname,
                    ...extractedFields,
                    ...((s.flatData as object) || {}),
                    ...((s.labelData as object) || {})
                };
                return row;
            });

            // Add dynamic columns found in sample rows
            for (const row of sampleRows) {
                for (const key of Object.keys(row)) {
                    if (!columns.has(key) && key !== 'data_json') {
                        columns.set(key, typeof row[key] === 'number' ? 'measure' : 'dimension');
                    }
                }
            }

            const schemaDict = Array.from(columns.entries()).map(([k, v]) => `- \`${k}\`: ${v}`).join('\n');

            const markdown = `You are an expert Data Analyst & BI Developer. I need your help to configure a JSON object for a Custom Visualization dashboard using Quasar/Vue and ECharts.

### Data Dictionary
Available columns and their detected types:
${schemaDict}

### Data Samples (3 Rows)
Here's what the raw flat data actually looks like:
\`\`\`json
${JSON.stringify(sampleRows, null, 2)}
\`\`\`

### The Task
Write a JSON configuration object that represents my request. The JSON must follow this exact structure:
\`\`\`json
[
  {
    "name": "Name of the visualization",
    "chartType": "data_table", // Options: "scorecard", "data_table", "bar_vertical", "bar_horizontal"
    "config": {
      "xColumn": "Main grouping dimension column name (leave empty string for scorecard)",
      "groupBy": "Optional secondary grouping column name (or null)",
      "metrics": [
        {
          "id": "m0",
          "type": "regular", // "regular" or "calculated"
          "column": "Column name to calculate",
          "aggregation": "count", // "count", "sum", "avg", "min", "max"
          "label": "Metric title to display",
          "color": "#e74c3c", // Optional hex color code for the chart metric (make it visually stunning)
          "filters": [
            // Optional conditional filters
            { "column": "colName", "operator": "equals", "value": "someValue" } // operators: equals, not_equals, contains, greater_than, less_than
          ]
        },
        {
          "id": "m1",
          "type": "calculated",
          "expression": "(m0 / m1) * 100", // pure JS mathematical eval based on metric ids
          "label": "Calculated Title",
          "color": "#3498db" // Optional hex color code (use harmonious palettes)
        }
      ]
    }
  }
  {
    "name": "Map Visualization Example",
    "chartType": "map_point", // WebGL map rendering for coordinates
    "config": {
      "latColumn": "latitude_column_name",   // must be a numeric column with lat values
      "lngColumn": "longitude_column_name",  // must be a numeric column with lng values
      "colorBy": "status_column", // Optional: column whose distinct values define marker colors
      "colorRules": [
        { "value": "Selesai", "color": "#2ecc71" },
        { "value": "Proses", "color": "#f1c40f" }
      ],
      "popupFields": [
        // List of {column, label} alias pairs shown in the popup when user clicks a marker.
        // 'label' is the human-readable display name shown in the popup (alias for technical column name).
        { "column": "nama_kepala_keluarga", "label": "Nama Kepala Keluarga" },
        { "column": "alamat", "label": "Alamat" },
        { "column": "kecamatan", "label": "Kecamatan" }
      ],
      "metrics": [
         // Typically just one COUNT metric for map bubbles radius weighting
        { "id": "m0", "type": "regular", "column": "_id", "aggregation": "count" }
      ]
    }
  }
]
\`\`\`

You can generate more than one visualization at a time by simply adding more objects to the root JSON Array.
Please ask me what I want to visualize, then respond ONLY with the JSON code block that fulfills my request.`;

            return { markdown };
        } catch (e: any) {
            console.error("AI Context Error:", e);
            set.status = 500;
            return { error: e.message, stack: e.stack };
        }
    });

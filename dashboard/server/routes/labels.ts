import { Elysia } from "elysia";
import { db } from "../db";
import { labelSchemas, labelData, assignments } from "../db/schema";
import { eq, and, sql } from "drizzle-orm";
import * as XLSX from "xlsx";

interface ColumnDef {
    name: string;
    type: "dimension" | "measure";
}

function detectColumnType(values: any[]): "dimension" | "measure" {
    const nonEmpty = values.filter(v => v !== null && v !== undefined && String(v).trim() !== "");
    if (nonEmpty.length === 0) return "dimension";
    const numericCount = nonEmpty.filter(v => !isNaN(Number(v))).length;
    // If >80% of non-empty values are numeric, treat as measure
    return numericCount / nonEmpty.length > 0.8 ? "measure" : "dimension";
}

export const labelsRoutes = new Elysia({ prefix: "/api/surveys" })

    // Get label schema for a survey
    .get("/:id/labels/schema", async ({ params }) => {
        const rows = await db
            .select()
            .from(labelSchemas)
            .where(eq(labelSchemas.surveyConfigId, params.id))
            .limit(1);
        return rows[0] || new Response("null", { headers: { "Content-Type": "application/json" } });
    })

    // Get all label data for a survey
    .get("/:id/labels", async ({ params, query }) => {
        const page = Number(query?.page) || 1;
        const limit = Math.min(Number(query?.limit) || 50, 200);
        const offset = (page - 1) * limit;

        const [rows, [total]] = await Promise.all([
            db
                .select()
                .from(labelData)
                .where(eq(labelData.surveyConfigId, params.id))
                .limit(limit)
                .offset(offset),
            db
                .select({ count: sql<number>`count(*)::int` })
                .from(labelData)
                .where(eq(labelData.surveyConfigId, params.id)),
        ]);

        return {
            data: rows,
            pagination: { page, limit, total: total?.count || 0 },
        };
    })

    // Download Excel template with existing code identities pre-filled
    .get("/:id/labels/template", async ({ params, set }) => {
        // Get all unique code identities for this survey (chunked for large datasets)
        const codeRows = await db
            .select({ codeIdentity: assignments.codeIdentity })
            .from(assignments)
            .where(eq(assignments.surveyConfigId, params.id))
            .groupBy(assignments.codeIdentity)
            .orderBy(assignments.codeIdentity);

        // Get existing schema and data (chunked to avoid memory overload)
        const schemaRows = await db
            .select()
            .from(labelSchemas)
            .where(eq(labelSchemas.surveyConfigId, params.id))
            .limit(1);

        // Build dataMap incrementally in chunks instead of loading all at once
        const dataMap = new Map<string, Record<string, any>>();
        const CHUNK_SIZE = 1000;
        let offset = 0;
        while (true) {
            const chunk = await db
                .select()
                .from(labelData)
                .where(eq(labelData.surveyConfigId, params.id))
                .limit(CHUNK_SIZE)
                .offset(offset);
            if (chunk.length === 0) break;
            for (const d of chunk) {
                dataMap.set(d.codeIdentity, d.data as Record<string, any>);
            }
            offset += CHUNK_SIZE;
            if (chunk.length < CHUNK_SIZE) break;
        }

        // Build headers: code_identity + any existing schema columns
        const schema = schemaRows[0];
        const extraColumns: string[] = schema
            ? (schema.columns as ColumnDef[]).map(c => c.name)
            : [];

        const headers = ["code_identity", ...extraColumns];

        // Build data rows
        const wsData = [
            headers,
            ...codeRows.map(r => {
                const existing = dataMap.get(r.codeIdentity || "") || {};
                return [
                    r.codeIdentity,
                    ...extraColumns.map(col => existing[col] ?? ""),
                ];
            }),
        ];

        const wb = XLSX.utils.book_new();
        const ws = XLSX.utils.aoa_to_sheet(wsData);

        // Set column widths
        ws["!cols"] = headers.map(() => ({ wch: 20 }));

        XLSX.utils.book_append_sheet(wb, ws, "Labels");

        const buffer = XLSX.write(wb, { type: "buffer", bookType: "xlsx" });

        return new Response(buffer, {
            headers: {
                "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "Content-Disposition": `attachment; filename="label_template.xlsx"`,
            },
        });
    })

    // Upload Excel with multi-column labels
    .post("/:id/labels/upload", async ({ params, body, set }) => {
        try {
            const formData = body as { file: File };
            const file = formData.file;

            if (!file) {
                set.status = 400;
                return { error: "No file uploaded" };
            }

            const arrayBuffer = await file.arrayBuffer();
            const wb = XLSX.read(arrayBuffer, { type: "array" });
            const ws = wb.Sheets[wb.SheetNames[0]!]!;
            const data: any[] = XLSX.utils.sheet_to_json(ws);

            if (!data.length) {
                set.status = 400;
                return { error: "File kosong atau format salah. Pastikan ada kolom 'code_identity'" };
            }

            // Validate: must have code_identity column
            const firstRow = data[0];
            if (!("code_identity" in firstRow)) {
                set.status = 400;
                return { error: "Kolom pertama harus 'code_identity'" };
            }

            // Detect extra columns (everything except code_identity)
            const allColumns = Object.keys(firstRow).filter(k => k !== "code_identity");

            if (allColumns.length === 0) {
                set.status = 400;
                return { error: "Tambahkan minimal 1 kolom selain 'code_identity'" };
            }

            // Auto-detect column types
            const columnDefs: ColumnDef[] = allColumns.map(colName => {
                const values = data.map(row => row[colName]);
                return { name: colName, type: detectColumnType(values) };
            });

            // Filter valid rows (must have code_identity)
            const validRows = data.filter((row: any) => row.code_identity && String(row.code_identity).trim());

            if (!validRows.length) {
                set.status = 400;
                return { error: "Tidak ada baris dengan code_identity yang terisi" };
            }

            // Delete existing schema and data for this survey
            await db.delete(labelSchemas).where(eq(labelSchemas.surveyConfigId, params.id));
            await db.delete(labelData).where(eq(labelData.surveyConfigId, params.id));

            // Insert new schema
            await db.insert(labelSchemas).values({
                surveyConfigId: params.id,
                columns: columnDefs,
            });

            // Insert data rows
            const toInsert = validRows.map((row: any) => {
                const rowData: Record<string, any> = {};
                for (const col of allColumns) {
                    const val = row[col];
                    if (val !== null && val !== undefined && String(val).trim() !== "") {
                        // Store numeric values as numbers
                        const colDef = columnDefs.find(c => c.name === col);
                        rowData[col] = colDef?.type === "measure" && !isNaN(Number(val))
                            ? Number(val)
                            : String(val).trim();
                    }
                }
                return {
                    surveyConfigId: params.id,
                    codeIdentity: String(row.code_identity).trim(),
                    data: rowData,
                };
            });

            // Batch insert in chunks of 500 for memory efficiency at scale
            const BATCH_SIZE = 500;
            for (let i = 0; i < toInsert.length; i += BATCH_SIZE) {
                const batch = toInsert.slice(i, i + BATCH_SIZE);
                await db.insert(labelData).values(batch);
            }

            return {
                success: true,
                message: `${toInsert.length} baris dengan ${allColumns.length} kolom berhasil diupload`,
                count: toInsert.length,
                columns: columnDefs,
            };
        } catch (e: any) {
            set.status = 500;
            return { error: e.message || "Gagal memproses file" };
        }
    })

    // Delete all labels and schema for a survey
    .delete("/:id/labels", async ({ params }) => {
        await db.delete(labelData).where(eq(labelData.surveyConfigId, params.id));
        await db.delete(labelSchemas).where(eq(labelSchemas.surveyConfigId, params.id));
        return { success: true, message: "Semua label dan schema dihapus" };
    });

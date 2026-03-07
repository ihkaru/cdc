import { pgTable, text, integer, boolean, timestamp, uuid, jsonb, index } from "drizzle-orm/pg-core";

export const surveyConfigs = pgTable("survey_configs", {
  id: uuid("id").primaryKey().defaultRandom(),
  surveyName: text("survey_name").notNull(),
  ssoUsername: text("sso_username").notNull(),
  ssoPasswordEncrypted: text("sso_password_encrypted").notNull(),
  filterProvinsi: text("filter_provinsi").default(""),
  filterKabupaten: text("filter_kabupaten").default(""),
  filterRotation: text("filter_rotation").default("pengawas"),
  intervalMinutes: integer("interval_minutes").default(30),
  isActive: boolean("is_active").default(true),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
});

export const assignments = pgTable("assignments", {
  id: text("id").primaryKey(),
  surveyConfigId: uuid("survey_config_id").references(() => surveyConfigs.id, { onDelete: "cascade" }),
  codeIdentity: text("code_identity"),
  surveyPeriodId: text("survey_period_id"),
  assignmentStatusAlias: text("assignment_status_alias"),
  currentUserUsername: text("current_user_username"),
  dataJson: jsonb("data_json"),
  flatData: jsonb("flat_data"),
  dateModifiedRemote: text("date_modified_remote"),
  dateSynced: timestamp("date_synced", { withTimezone: true }).defaultNow(),
  syncedToApi: boolean("synced_to_api").default(false),
}, (table) => [
  index("idx_assignments_survey_config_id").on(table.surveyConfigId),
  index("idx_assignments_survey_date").on(table.surveyConfigId, table.dateSynced),
  index("idx_assignments_survey_code").on(table.surveyConfigId, table.codeIdentity),
  index("idx_assignments_survey_status").on(table.surveyConfigId, table.assignmentStatusAlias),
  index("idx_assignments_synced").on(table.syncedToApi),
]);

export const syncLogs = pgTable("sync_logs", {
  id: integer("id").primaryKey().generatedAlwaysAsIdentity(),
  surveyConfigId: uuid("survey_config_id").references(() => surveyConfigs.id, { onDelete: "cascade" }),
  startedAt: timestamp("started_at", { withTimezone: true }),
  finishedAt: timestamp("finished_at", { withTimezone: true }),
  totalFetched: integer("total_fetched").default(0),
  totalNew: integer("total_new").default(0),
  totalUpdated: integer("total_updated").default(0),
  totalSkipped: integer("total_skipped").default(0),
  totalFailed: integer("total_failed").default(0),
  status: text("status").default("running"),
  notes: text("notes"),
}, (table) => [
  index("idx_sync_logs_survey").on(table.surveyConfigId),
  index("idx_sync_logs_status").on(table.status),
]);

export const labelSchemas = pgTable("label_schemas", {
  id: integer("id").primaryKey().generatedAlwaysAsIdentity(),
  surveyConfigId: uuid("survey_config_id")
    .references(() => surveyConfigs.id, { onDelete: "cascade" }).notNull(),
  columns: jsonb("columns").notNull(),
  // columns: [{ name: "wilayah", type: "dimension" }, { name: "target", type: "measure" }]
  uploadedAt: timestamp("uploaded_at", { withTimezone: true }).defaultNow(),
});

export const labelData = pgTable("label_data", {
  id: integer("id").primaryKey().generatedAlwaysAsIdentity(),
  surveyConfigId: uuid("survey_config_id")
    .references(() => surveyConfigs.id, { onDelete: "cascade" }).notNull(),
  codeIdentity: text("code_identity").notNull(),
  data: jsonb("data").notNull(),
  // data: { "wilayah": "Jawa Barat", "target": 100, "skor": 85 }
}, (table) => [
  index("idx_label_data_survey_code").on(table.surveyConfigId, table.codeIdentity),
]);

export const visualizationConfigs = pgTable("visualization_configs", {
  id: integer("id").primaryKey().generatedAlwaysAsIdentity(),
  surveyConfigId: uuid("survey_config_id")
    .references(() => surveyConfigs.id, { onDelete: "cascade" }).notNull(),
  name: text("name").notNull(),
  chartType: text("chart_type").notNull(), // "scorecard" | "bar_vertical" | "bar_horizontal"
  config: jsonb("config").notNull(),
  // Scorecard: { metricColumn, aggregation, label }
  // Bar: { xColumn, yColumn, aggregation, groupBy? }
  sortOrder: integer("sort_order").default(0),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
});

// Key-value store for system-wide settings (e.g. VPN cookie)
export const systemSettings = pgTable("system_settings", {
  key: text("key").primaryKey(),
  value: text("value").notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
});

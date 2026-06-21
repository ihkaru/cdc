import { relations } from "drizzle-orm";
import {
	boolean,
	index,
	integer,
	jsonb,
	pgTable,
	primaryKey,
	text,
	timestamp,
	uuid,
} from "drizzle-orm/pg-core";

// --- EXISTING TABLES ---

export const surveyConfigs = pgTable("survey_configs", {
	id: uuid("id").primaryKey().defaultRandom(),
	surveyName: text("survey_name").notNull(),
	bpsSurveyId: text("bps_survey_id"),
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

export const assignments = pgTable(
	"assignments",
	{
		id: uuid("id").primaryKey(),
		surveyConfigId: uuid("survey_config_id").references(() => surveyConfigs.id, {
			onDelete: "cascade",
		}),
		codeIdentity: text("code_identity"),
		surveyPeriodId: uuid("survey_period_id"),
		assignmentStatusAlias: text("assignment_status_alias"),
		currentUserUsername: text("current_user_username"),
		dataJson: jsonb("data_json"),
		flatData: jsonb("flat_data"),
		dateModifiedRemote: text("date_modified_remote"),
		dateSynced: timestamp("date_synced", { withTimezone: true }).defaultNow(),
		syncedToApi: boolean("synced_to_api").default(false),
		localImageMirrored: boolean("local_image_mirrored").default(false),
		localImagePaths: jsonb("local_image_paths").default({}),
		syncLogId: integer("sync_log_id").references(() => syncLogs.id, { onDelete: "set null" }),
	},
	(table) => [
		index("idx_assignments_survey_config_id").on(table.surveyConfigId),
		index("idx_assignments_survey_date").on(table.surveyConfigId, table.dateSynced),
		index("idx_assignments_survey_code").on(table.surveyConfigId, table.codeIdentity),
		index("idx_assignments_survey_status").on(table.surveyConfigId, table.assignmentStatusAlias),
		index("idx_assignments_synced").on(table.syncedToApi),
	],
);

export const syncLogs = pgTable(
	"sync_logs",
	{
		id: integer("id").primaryKey().generatedAlwaysAsIdentity(),
		surveyConfigId: uuid("survey_config_id").references(() => surveyConfigs.id, {
			onDelete: "cascade",
		}),
		startedAt: timestamp("started_at", { withTimezone: true }),
		finishedAt: timestamp("finished_at", { withTimezone: true }),
		totalFetched: integer("total_fetched").default(0),
		totalNew: integer("total_new").default(0),
		totalUpdated: integer("total_updated").default(0),
		totalSkipped: integer("total_skipped").default(0),
		totalFailed: integer("total_failed").default(0),
		totalImages: integer("total_images").default(0),
		imagesMirrored: integer("images_mirrored").default(0),
		totalTargetRemote: integer("total_target_remote").default(0),
		status: text("status").default("running"),
		notes: text("notes"),
		timings: jsonb("timings"),
	},
	(table) => [
		index("idx_sync_logs_survey").on(table.surveyConfigId),
		index("idx_sync_logs_status").on(table.status),
	],
);

export const labelSchemas = pgTable("label_schemas", {
	id: integer("id").primaryKey().generatedAlwaysAsIdentity(),
	surveyConfigId: uuid("survey_config_id")
		.references(() => surveyConfigs.id, { onDelete: "cascade" })
		.notNull(),
	columns: jsonb("columns").notNull(),
	uploadedAt: timestamp("uploaded_at", { withTimezone: true }).defaultNow(),
});

export const labelData = pgTable(
	"label_data",
	{
		id: integer("id").primaryKey().generatedAlwaysAsIdentity(),
		surveyConfigId: uuid("survey_config_id")
			.references(() => surveyConfigs.id, { onDelete: "cascade" })
			.notNull(),
		codeIdentity: text("code_identity").notNull(),
		data: jsonb("data").notNull(),
	},
	(table) => [index("idx_label_data_survey_code").on(table.surveyConfigId, table.codeIdentity)],
);

export const visualizationConfigs = pgTable("visualization_configs", {
	id: integer("id").primaryKey().generatedAlwaysAsIdentity(),
	surveyConfigId: uuid("survey_config_id")
		.references(() => surveyConfigs.id, { onDelete: "cascade" })
		.notNull(),
	name: text("name").notNull(),
	chartType: text("chart_type").notNull(),
	config: jsonb("config").notNull(),
	sortOrder: integer("sort_order").default(0),
	createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
});

export const systemSettings = pgTable("system_settings", {
	key: text("key").primaryKey(),
	value: text("value").notNull(),
	updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
});

// --- AUTH & RBAC TABLES ---

export const users = pgTable("users", {
	id: text("id").primaryKey(),
	name: text("name").notNull(),
	email: text("email").notNull().unique(),
	emailVerified: boolean("email_verified").notNull().default(false),
	image: text("image"),
	createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
	updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

export const sessions = pgTable("sessions", {
	id: text("id").primaryKey(),
	userId: text("user_id")
		.notNull()
		.references(() => users.id, { onDelete: "cascade" }),
	token: text("token").notNull().unique(),
	expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
	ipAddress: text("ip_address"),
	userAgent: text("user_agent"),
	createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
	updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

export const accounts = pgTable("accounts", {
	id: text("id").primaryKey(),
	userId: text("user_id")
		.notNull()
		.references(() => users.id, { onDelete: "cascade" }),
	accountId: text("account_id").notNull(),
	providerId: text("provider_id").notNull(),
	accessToken: text("access_token"),
	refreshToken: text("refresh_token"),
	accessTokenExpiresAt: timestamp("access_token_expires_at", { withTimezone: true }),
	refreshTokenExpiresAt: timestamp("refresh_token_expires_at", { withTimezone: true }),
	scope: text("scope"),
	password: text("password"),
	createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
	updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

export const verifications = pgTable("verifications", {
	id: text("id").primaryKey(),
	identifier: text("identifier").notNull(),
	value: text("value").notNull(),
	expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
	createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
	updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

// --- RBAC ---

export const roles = pgTable("roles", {
	id: text("id").primaryKey(),
	name: text("name").notNull().unique(), // e.g. "admin", "user"
	description: text("description"),
	createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
});

export const permissions = pgTable("permissions", {
	id: text("id").primaryKey(),
	name: text("name").notNull().unique(), // e.g. "survey:write", "user:manage"
	description: text("description"),
	createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
});

export const usersToRoles = pgTable(
	"users_to_roles",
	{
		userId: text("user_id")
			.notNull()
			.references(() => users.id, { onDelete: "cascade" }),
		roleId: text("role_id")
			.notNull()
			.references(() => roles.id, { onDelete: "cascade" }),
	},
	(t) => ({
		pk: primaryKey({ columns: [t.userId, t.roleId] }),
	}),
);

export const rolesToPermissions = pgTable(
	"roles_to_permissions",
	{
		roleId: text("role_id")
			.notNull()
			.references(() => roles.id, { onDelete: "cascade" }),
		permissionId: text("permission_id")
			.notNull()
			.references(() => permissions.id, { onDelete: "cascade" }),
	},
	(t) => ({
		pk: primaryKey({ columns: [t.roleId, t.permissionId] }),
	}),
);

// --- RELATIONS ---

export const usersRelations = relations(users, ({ many }) => ({
	roles: many(usersToRoles),
}));

export const rolesRelations = relations(roles, ({ many }) => ({
	users: many(usersToRoles),
	permissions: many(rolesToPermissions),
}));

export const permissionsRelations = relations(permissions, ({ many }) => ({
	roles: many(rolesToPermissions),
}));

export const usersToRolesRelations = relations(usersToRoles, ({ one }) => ({
	user: one(users, { fields: [usersToRoles.userId], references: [users.id] }),
	role: one(roles, { fields: [usersToRoles.roleId], references: [roles.id] }),
}));

export const rolesToPermissionsRelations = relations(rolesToPermissions, ({ one }) => ({
	role: one(roles, { fields: [rolesToPermissions.roleId], references: [roles.id] }),
	permission: one(permissions, {
		fields: [rolesToPermissions.permissionId],
		references: [permissions.id],
	}),
}));

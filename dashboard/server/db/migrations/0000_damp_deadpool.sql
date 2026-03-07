CREATE TABLE "assignment_labels" (
	"id" integer PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "assignment_labels_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 START WITH 1 CACHE 1),
	"survey_config_id" uuid NOT NULL,
	"code_identity" text NOT NULL,
	"label" text NOT NULL
);
--> statement-breakpoint
CREATE TABLE "assignments" (
	"id" text PRIMARY KEY NOT NULL,
	"survey_config_id" uuid,
	"code_identity" text,
	"survey_period_id" text,
	"assignment_status_alias" text,
	"current_user_username" text,
	"data_json" jsonb,
	"date_modified_remote" text,
	"date_synced" timestamp with time zone DEFAULT now(),
	"synced_to_api" boolean DEFAULT false
);
--> statement-breakpoint
CREATE TABLE "survey_configs" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"survey_name" text NOT NULL,
	"sso_username" text NOT NULL,
	"sso_password_encrypted" text NOT NULL,
	"filter_provinsi" text DEFAULT '',
	"filter_kabupaten" text DEFAULT '',
	"filter_rotation" text DEFAULT 'pengawas',
	"interval_minutes" integer DEFAULT 30,
	"is_active" boolean DEFAULT true,
	"created_at" timestamp with time zone DEFAULT now(),
	"updated_at" timestamp with time zone DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE "sync_logs" (
	"id" integer PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "sync_logs_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 START WITH 1 CACHE 1),
	"survey_config_id" uuid,
	"started_at" timestamp with time zone,
	"finished_at" timestamp with time zone,
	"total_fetched" integer DEFAULT 0,
	"total_new" integer DEFAULT 0,
	"total_updated" integer DEFAULT 0,
	"total_skipped" integer DEFAULT 0,
	"total_failed" integer DEFAULT 0,
	"status" text DEFAULT 'running',
	"notes" text
);
--> statement-breakpoint
ALTER TABLE "assignment_labels" ADD CONSTRAINT "assignment_labels_survey_config_id_survey_configs_id_fk" FOREIGN KEY ("survey_config_id") REFERENCES "public"."survey_configs"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "assignments" ADD CONSTRAINT "assignments_survey_config_id_survey_configs_id_fk" FOREIGN KEY ("survey_config_id") REFERENCES "public"."survey_configs"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "sync_logs" ADD CONSTRAINT "sync_logs_survey_config_id_survey_configs_id_fk" FOREIGN KEY ("survey_config_id") REFERENCES "public"."survey_configs"("id") ON DELETE cascade ON UPDATE no action;
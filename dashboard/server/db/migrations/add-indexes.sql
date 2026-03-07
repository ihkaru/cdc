-- Migration: Add performance indexes for 5M+ rows
-- Run with: docker compose exec postgres psql -U fasih -d fasih_dashboard -f /path/to/this.sql
-- Uses CONCURRENTLY to avoid blocking writes during index creation

-- Assignments table (heaviest table, 5M+ rows expected)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_assignments_survey_config_id ON assignments(survey_config_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_assignments_survey_date ON assignments(survey_config_id, date_synced);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_assignments_survey_code ON assignments(survey_config_id, code_identity);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_assignments_survey_status ON assignments(survey_config_id, assignment_status_alias);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_assignments_synced ON assignments(synced_to_api);

-- Label data table
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_label_data_survey_code ON label_data(survey_config_id, code_identity);

-- Sync logs table
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sync_logs_survey ON sync_logs(survey_config_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sync_logs_status ON sync_logs(status);

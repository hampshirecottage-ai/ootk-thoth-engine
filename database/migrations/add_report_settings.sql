-- Lets the web app give each saved reading its own report link (/report/<session_id>).
-- Stores the reading's settings and drawn card titles with the session. Safe to re-run.
ALTER TABLE tarot_sessions ADD COLUMN IF NOT EXISTS report_settings jsonb;

-- Index for opening a saved report by its link (/report/<link>).
-- Without it every report page reads the whole tarot_sessions table, so it slows down as
-- readings accumulate (about 100 ms at 33,000 saved readings, growing linearly).
-- Safe to run more than once.
CREATE INDEX IF NOT EXISTS idx_sessions_report_link
    ON tarot_sessions ((report_settings->>'link'));

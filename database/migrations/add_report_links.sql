-- Gives saved web readings from before report links were random a random link, then lists
-- every reading's report address. Old /report/<number> addresses stop working.
-- Safe to re-run: readings that already have a link keep it. Needs PostgreSQL 13+.
UPDATE tarot_sessions
SET report_settings = report_settings
    || jsonb_build_object('link', replace(gen_random_uuid()::text, '-', ''))
WHERE report_settings IS NOT NULL AND NOT report_settings ? 'link';

SELECT session_id, report_settings->>'topic' AS topic, '/report/' || (report_settings->>'link') AS report
FROM tarot_sessions
WHERE report_settings ? 'link'
ORDER BY session_id;

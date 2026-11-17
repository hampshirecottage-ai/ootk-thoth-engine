-- Drops the testimonials table, left over from the testimonials feature retired in November 2026.
-- Nothing in the app reads or writes it. Safe to run more than once.
--
-- BEFORE RUNNING THIS:
--   1. Take a Neon snapshot of the production branch (or a pg_dump). Neon only keeps 6 hours of
--      history, so the snapshot is the only way back after that.
--   2. Copy out anything you want to keep. On 17 Nov 2026 the table held one approved
--      testimonial. To see it, run this on its own first:
--        SELECT testimonial_id, created_at, name, body, approved FROM testimonials ORDER BY created_at;
--
-- Then run the lines below. No app restart is needed (the app never loads this table).

DROP TABLE IF EXISTS testimonials;

-- Check: this should return no rows.
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'testimonials';

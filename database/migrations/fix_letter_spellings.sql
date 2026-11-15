-- Hebrew letter spellings of 2026-11-15: four Liber 777 rows spelled their letter the old way
-- (Hé, Vau, Pé, Tau) while the rest of the site, and the same pages, say Heh, Vav, Peh and
-- Tav. The Star's card page, for one, showed "ה (Hé)" two lines above "Path 15, Heh (ה)".
-- Only the name in brackets changes; the Hebrew character stays.
--
--   Path 15, Window:  ה (Hé)   -> ה (Heh)
--   Path 16, Nail:    ו (Vau)  -> ו (Vav)
--   Path 27, Mouth:   פ (Pé)   -> פ (Peh)
--   Path 32, Cross:   ת (Tau)  -> ת (Tav)
--
-- Safe to re-run: every statement sets absolute values. After running it, restart the
-- Render service, because the card tables are loaded once at start-up.

BEGIN;

UPDATE correspondences SET hebrew_letter = 'ה (Heh)' WHERE key_scale = 15;
UPDATE correspondences SET hebrew_letter = 'ו (Vav)' WHERE key_scale = 16;
UPDATE correspondences SET hebrew_letter = 'פ (Peh)' WHERE key_scale = 27;
UPDATE correspondences SET hebrew_letter = 'ת (Tav)' WHERE key_scale = 32;

COMMIT;

-- Check: should list 15 ה (Heh), 16 ו (Vav), 27 פ (Peh), 32 ת (Tav).
SELECT key_scale, hebrew_letter FROM correspondences WHERE key_scale IN (15, 16, 27, 32) ORDER BY key_scale;

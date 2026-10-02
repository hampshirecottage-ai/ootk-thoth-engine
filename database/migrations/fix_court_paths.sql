-- Court cards on the same paths as their Thoth Majors, and four court descriptions.
-- Safe to re-run: every statement sets absolute values. Run after fix_correspondences.sql.
--
--  1. The Thoth deck swaps Tzaddi and Heh: the Emperor (Aries) sits on 28 and the Star
--     (Aquarius) on 15. Courts sit on the path of their main sign, so the Queen of Wands
--     (mostly Aries) moves to 28 and the Prince of Swords (mostly Aquarius) to 15. Before,
--     they followed the older Golden Dawn letters and shared the opposite Major's path.
--  2. Descriptions that named the wrong sign: Knight of Wands (Sagittarius, not Aries),
--     Queen of Wands (Aries, not Cancer/Pisces), Prince of Wands (Leo) and Knight of Cups
--     (Pisces, not Scorpio).

BEGIN;

UPDATE thoth_cards SET key_scale = 28 WHERE title = 'Queen of Wands';
UPDATE thoth_cards SET key_scale = 15 WHERE title = 'Prince of Swords';

UPDATE thoth_cards AS tc SET description = v.description
FROM (VALUES
    ('Knight of Wands', 'Fire of Fire. Sagittarius attribution.'),
    ('Queen of Wands', 'Water of Fire. Aries attribution.'),
    ('Prince of Wands', 'Air of Fire. Leo attribution.'),
    ('Knight of Cups', 'Fire of Water. Pisces attribution.')
) AS v(title, description)
WHERE tc.title = v.title;

COMMIT;

-- Correspondence audit of 2026-10-04: Cube of Space edges for Teth, Yod, Lamed, Nun, Samekh and
-- Ayin, clearer axis names, and the French/Egyptian attributions of the Magus and Priestess.
-- Safe to re-run: every statement sets absolute values.
--
-- The twelve simple letters now follow Paul Case's Cube of Space, which takes Sepher
-- Yetzirah 5:2 (Westcott's order of the twelve diagonal boundaries): Heh north-east, Vav
-- south-east, Zain east-above, Cheth east-below, Teth north-above, Yod north-below, Lamed
-- north-west, Nun south-west, Samekh west-above, Ayin west-below, Tzaddi south-above,
-- Qoph south-below. Before, Teth and Yod sat on the west verticals, Lamed and Nun on the
-- west face and Samekh and Ayin on the north face, which matches no version of the text.
-- The three mother axes keep their places; only their names now say which way they run.
--
-- French/Egyptian attributions: rows 3-21 give the card's own sign, planet or element, but
-- the Magus (French 1) showed 'Air / Magus Spirit' (the Fool's element) and the Priestess
-- (French 2) 'Mercury' (the Magus's planet). They now read Mercury and Moon like the rest.

BEGIN;

UPDATE correspondences AS c SET spatial_dimension = v.place
FROM (VALUES
    (11, 'Vertical Axis (above to below)'),
    (23, 'Horizontal Axis (east to west)'),
    (31, 'Longitudinal Axis (north to south)'),
    (19, 'Upper-North Edge'),
    (20, 'Lower-North Edge'),
    (22, 'North-West Edge'),
    (24, 'South-West Edge'),
    (25, 'Upper-West Edge'),
    (26, 'Lower-West Edge')
) AS v(key_scale, place)
WHERE c.key_scale = v.key_scale;

UPDATE correspondences SET attribution_french = 'Mercury' WHERE key_scale = 1;
UPDATE correspondences SET attribution_french = 'Moon'    WHERE key_scale = 2;

COMMIT;

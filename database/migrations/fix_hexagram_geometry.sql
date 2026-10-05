-- The hexagram rows of spread_position_geometry still held the old layout (Mars right-bottom,
-- Venus at the bottom, Sun left-top, Moon in the centre). The engine draws the Golden Dawn
-- hexagram from ootk.spreads, so this brings the table into line with it. The engine does not
-- read this table, so readings are unchanged. Safe to re-run: every statement sets absolute values.

BEGIN;

UPDATE spread_position_geometry AS g
SET position_name = v.position_name, pos_x = v.pos_x, pos_y = v.pos_y, pos_z = 0, polar_angle_deg = v.angle
FROM (VALUES
    (1, 'Saturn (Top Apex)', 0.0, 1.0, 90.0),
    (2, 'Jupiter (Right Top)', 0.866, 0.5, 30.0),
    (3, 'Mars (Left Top)', -0.866, 0.5, 150.0),
    (4, 'Venus (Right Bottom)', 0.866, -0.5, 330.0),
    (5, 'Mercury (Left Bottom)', -0.866, -0.5, 210.0),
    (6, 'Sun (Center Core)', 0.0, 0.0, 0.0),
    (7, 'Moon (Bottom Apex)', 0.0, -1.0, 270.0)
) AS v(position_index, position_name, pos_x, pos_y, angle)
WHERE g.spread_key = '6' AND g.position_index = v.position_index;

COMMIT;

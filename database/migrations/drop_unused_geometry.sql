-- Removes stored geometry the app never reads. Safe to run more than once; no saved readings
-- are touched.
--
-- correspondences.platonic_solid, solid_faces, solid_vertices, dual_solid and topological_role
-- were filled by the old add_platonic_topology.sql, by Hebrew letter. The app works these out
-- from each card's element instead (analysis.apply_card_solid), and the stored values disagreed
-- with the site for 45 of the 78 cards. spread_position_geometry held two spreads' layouts;
-- every layout comes from ootk/spreads.py. idx_cards_fts indexed a card search that doesn't exist.
BEGIN;

ALTER TABLE correspondences
    DROP COLUMN IF EXISTS platonic_solid,
    DROP COLUMN IF EXISTS solid_faces,
    DROP COLUMN IF EXISTS solid_vertices,
    DROP COLUMN IF EXISTS dual_solid,
    DROP COLUMN IF EXISTS topological_role;

DROP TABLE IF EXISTS spread_position_geometry;

DROP INDEX IF EXISTS idx_cards_fts;

COMMIT;

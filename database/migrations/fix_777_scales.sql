-- Liber 777 fix of 2026-11-01: the Prince (Emperor) scale, Yetziratic titles and a few other
-- 777 values in correspondences.attributions. Safe to re-run: every statement sets absolute values.
--
-- Prince scale (column XVII): from Netzach on, each row held a later row's colour. Netzach
-- held Netzach + Hod run together, Hod held Yesod's, Malkuth held Aleph + Beth, Aleph held
-- Gimel's and so on, two to three rows late, ending with the Spirit and Earth colours on
-- Resh and Shin. emperor_scale_hex follows the corrected name (approximate swatches).
-- Yetziratic titles (32 Paths of Wisdom): the word "Intelligence" had been replaced by the
-- row's own name ("Hand of Will" for "Intelligence of Will").
-- Also: Malkuth's Queen scale (four colours, not just Citrine), the Princess scale of
-- Daleth and Peh, and the geomantic figures Puer and Amissio (were "Peur", "Amission").
-- The King Scale, the only scale the prompt uses today, was already right and is unchanged.

BEGIN;

UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'White brilliance', 'emperor_scale_hex', '#FFFFFF', 'paths_of_sepher_yetzirah', 'Admirable or Hidden Intelligence') WHERE key_scale = 1;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Blue pearl grey, like mother-of-pearl', 'emperor_scale_hex', '#8DA399', 'paths_of_sepher_yetzirah', 'Illuminating Intelligence') WHERE key_scale = 2;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Dark brown', 'emperor_scale_hex', '#654321', 'paths_of_sepher_yetzirah', 'Sanctifying Intelligence') WHERE key_scale = 3;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Deep purple', 'emperor_scale_hex', '#9932CC', 'paths_of_sepher_yetzirah', 'Measuring, Cohesive or Receptacular Intelligence') WHERE key_scale = 4;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Bright scarlet', 'emperor_scale_hex', '#FF2400', 'paths_of_sepher_yetzirah', 'Radical Intelligence') WHERE key_scale = 5;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Rich salmon', 'emperor_scale_hex', '#FF8C69', 'paths_of_sepher_yetzirah', 'Intelligence of the Mediating Influence') WHERE key_scale = 6;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Bright yellow green', 'emperor_scale_hex', '#9ACD32', 'paths_of_sepher_yetzirah', 'Hidden (Occult) Intelligence') WHERE key_scale = 7;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Red-russet', 'emperor_scale_hex', '#80461B', 'paths_of_sepher_yetzirah', 'Absolute (Perfect) Intelligence') WHERE key_scale = 8;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Very dark purple', 'emperor_scale_hex', '#330066', 'paths_of_sepher_yetzirah', 'Pure (Clear) Intelligence') WHERE key_scale = 9;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('queen_scale_colors', 'Citrine, olive, russet and black', 'emperor_scale_colors', 'As Queen scale, but flecked with gold', 'emperor_scale_hex', '#E4D00A', 'paths_of_sepher_yetzirah', 'Resplendent Intelligence') WHERE key_scale = 10;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Blue emerald green', 'emperor_scale_hex', '#00A693', 'paths_of_sepher_yetzirah', 'Scintillating Intelligence') WHERE key_scale = 11;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Grey', 'emperor_scale_hex', '#808080', 'paths_of_sepher_yetzirah', 'Intelligence of Transparency') WHERE key_scale = 12;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Cold pale blue', 'emperor_scale_hex', '#AECBF0', 'paths_of_sepher_yetzirah', 'Uniting Intelligence') WHERE key_scale = 13;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Early spring green', 'emperor_scale_hex', '#00FF7F', 'paths_of_sepher_yetzirah', 'Illuminating Intelligence', 'empress_scale_colors', 'Bright rose or cerise, rayed pale green') WHERE key_scale = 14;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Brilliant flame', 'emperor_scale_hex', '#E25822', 'paths_of_sepher_yetzirah', 'Constituting Intelligence', 'lineal_figures_and_geomancy', 'Puer*') WHERE key_scale = 15;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Deep warm olive', 'emperor_scale_hex', '#58423F', 'paths_of_sepher_yetzirah', 'Triumphal or Eternal Intelligence', 'lineal_figures_and_geomancy', 'Amissio*') WHERE key_scale = 16;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'New yellow leather', 'emperor_scale_hex', '#D9B86C', 'paths_of_sepher_yetzirah', 'Disposing Intelligence') WHERE key_scale = 17;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Rich bright russet', 'emperor_scale_hex', '#D93C30', 'paths_of_sepher_yetzirah', 'Intelligence of the House of Influence') WHERE key_scale = 18;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Grey', 'emperor_scale_hex', '#808080', 'paths_of_sepher_yetzirah', 'Intelligence of all the Activities of the Spiritual Being') WHERE key_scale = 19;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Green grey', 'emperor_scale_hex', '#8A9A8A', 'paths_of_sepher_yetzirah', 'Intelligence of Will') WHERE key_scale = 20;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Rich purple', 'emperor_scale_hex', '#A040A0', 'paths_of_sepher_yetzirah', 'Intelligence of Conciliation') WHERE key_scale = 21;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Deep blue-green', 'emperor_scale_hex', '#006994', 'paths_of_sepher_yetzirah', 'Faithful Intelligence') WHERE key_scale = 22;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Deep olive-green', 'emperor_scale_hex', '#556B2F', 'paths_of_sepher_yetzirah', 'Stable Intelligence') WHERE key_scale = 23;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Very dark brown', 'emperor_scale_hex', '#321414', 'paths_of_sepher_yetzirah', 'Imaginative Intelligence') WHERE key_scale = 24;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Green', 'emperor_scale_hex', '#008000', 'paths_of_sepher_yetzirah', 'Intelligence of Probation (Tentative)') WHERE key_scale = 25;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Blue black', 'emperor_scale_hex', '#000080', 'paths_of_sepher_yetzirah', 'Renovating Intelligence') WHERE key_scale = 26;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Venetian red', 'emperor_scale_hex', '#C80815', 'paths_of_sepher_yetzirah', 'Exciting Intelligence', 'empress_scale_colors', 'Bright red, rayed azure or emerald') WHERE key_scale = 27;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Bluish mauve', 'emperor_scale_hex', '#9370DB', 'paths_of_sepher_yetzirah', 'Natural Intelligence') WHERE key_scale = 28;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Light translucent pinkish brown', 'emperor_scale_hex', '#E8C6B0', 'paths_of_sepher_yetzirah', 'Corporeal Intelligence') WHERE key_scale = 29;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Rich amber', 'emperor_scale_hex', '#FFBF00', 'paths_of_sepher_yetzirah', 'Collecting Intelligence') WHERE key_scale = 30;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Scarlet, flecked gold', 'emperor_scale_hex', '#FF2400', 'paths_of_sepher_yetzirah', 'Perpetual Intelligence') WHERE key_scale = 31;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('emperor_scale_colors', 'Blue black', 'emperor_scale_hex', '#000080', 'paths_of_sepher_yetzirah', 'Administrative Intelligence') WHERE key_scale = 32;

COMMIT;

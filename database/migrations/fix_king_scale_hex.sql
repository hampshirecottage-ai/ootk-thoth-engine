-- King Scale swatches of 2026-11-13: three signs had the wrong hex in
-- correspondences.attributions.king_scale_hex. The colour names (king_scale_color) were
-- already right; only the swatch drawn on the site was off.
--
--   Path 19, Teth, Leo:     "Yellow, greenish"        #ADFF2F (Virgo's swatch) -> #DFFF00
--   Path 24, Nun, Scorpio:  "Green blue"              #006400 (dark green)     -> #0D98BA
--   Path 29, Qoph, Pisces:  "Crimson (ultra violet)"  #8A2BE2 (blue violet)    -> #DC143C
--
-- Safe to re-run: every statement sets absolute values. After running it, restart the
-- Render service, because the card tables are loaded once at start-up.

BEGIN;

UPDATE correspondences SET attributions = attributions || jsonb_build_object('king_scale_hex', '#DFFF00') WHERE key_scale = 19;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('king_scale_hex', '#0D98BA') WHERE key_scale = 24;
UPDATE correspondences SET attributions = attributions || jsonb_build_object('king_scale_hex', '#DC143C') WHERE key_scale = 29;

COMMIT;

-- Check: should list 19 #DFFF00, 20 #ADFF2F, 24 #0D98BA, 29 #DC143C.
SELECT key_scale, king_scale_color, attributions ->> 'king_scale_hex' AS king_scale_hex
FROM correspondences WHERE key_scale IN (19, 20, 24, 29) ORDER BY key_scale;

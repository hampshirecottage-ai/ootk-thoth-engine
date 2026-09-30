-- Migration: Add French/Egyptian mapping support to correspondences table
ALTER TABLE correspondences 
ADD COLUMN IF NOT EXISTS hebrew_letter_french VARCHAR(10) DEFAULT 'N/A',
ADD COLUMN IF NOT EXISTS path_or_sephira_french VARCHAR(50),
ADD COLUMN IF NOT EXISTS attribution_french VARCHAR(100);

-- Update Major Arcana mappings for French/Egyptian System (I = Aleph, II = Beth, ..., Fool Shin/Unnumbered)
UPDATE correspondences SET hebrew_letter_french = 'Aleph (א)', path_or_sephira_french = 'Path 11 (Kether-Chokmah)', attribution_french = 'Air / Magus Spirit' WHERE key_scale = 1; -- The Magician
UPDATE correspondences SET hebrew_letter_french = 'Beth (ב)', path_or_sephira_french = 'Path 12 (Kether-Binah)', attribution_french = 'Mercury' WHERE key_scale = 2; -- High Priestess
UPDATE correspondences SET hebrew_letter_french = 'Gimel (ג)', path_or_sephira_french = 'Path 13 (Chokmah-Binah)', attribution_french = 'Venus' WHERE key_scale = 3; -- Empress
UPDATE correspondences SET hebrew_letter_french = 'Daleth (ד)', path_or_sephira_french = 'Path 14 (Chokmah-Tiphareth)', attribution_french = 'Aries' WHERE key_scale = 4; -- Emperor
UPDATE correspondences SET hebrew_letter_french = 'Heh (ה)', path_or_sephira_french = 'Path 15 (Chokmah-Chesed)', attribution_french = 'Taurus' WHERE key_scale = 5; -- Hierophant
UPDATE correspondences SET hebrew_letter_french = 'Vav (ו)', path_or_sephira_french = 'Path 16 (Binah-Tiphareth)', attribution_french = 'Gemini' WHERE key_scale = 6; -- Lovers
UPDATE correspondences SET hebrew_letter_french = 'Zain (ז)', path_or_sephira_french = 'Path 17 (Binah-Geburah)', attribution_french = 'Cancer' WHERE key_scale = 7; -- Chariot
UPDATE correspondences SET hebrew_letter_french = 'Cheth (ח)', path_or_sephira_french = 'Path 18 (Chesed-Geburah)', attribution_french = 'Strength / Leo' WHERE key_scale = 8; -- Strength (French Position 8)
UPDATE correspondences SET hebrew_letter_french = 'Teth (ט)', path_or_sephira_french = 'Path 19 (Chesed-Tiphareth)', attribution_french = 'Virgo' WHERE key_scale = 9; -- Hermit
UPDATE correspondences SET hebrew_letter_french = 'Yod (י)', path_or_sephira_french = 'Path 20 (Chesed-Netzach)', attribution_french = 'Jupiter' WHERE key_scale = 10; -- Wheel of Fortune
UPDATE correspondences SET hebrew_letter_french = 'Kaph (כ)', path_or_sephira_french = 'Path 21 (Geburah-Tiphareth)', attribution_french = 'Justice / Libra' WHERE key_scale = 11; -- Justice (French Position 11)
UPDATE correspondences SET hebrew_letter_french = 'Lamed (ל)', path_or_sephira_french = 'Path 22 (Geburah-Hod)', attribution_french = 'Water' WHERE key_scale = 12; -- Hanged Man
UPDATE correspondences SET hebrew_letter_french = 'Mem (מ)', path_or_sephira_french = 'Path 23 (Tiphareth-Netzach)', attribution_french = 'Scorpio' WHERE key_scale = 13; -- Death
UPDATE correspondences SET hebrew_letter_french = 'Nun (נ)', path_or_sephira_french = 'Path 24 (Tiphareth-Hod)', attribution_french = 'Sagittarius' WHERE key_scale = 14; -- Temperance
UPDATE correspondences SET hebrew_letter_french = 'Samekh (ס)', path_or_sephira_french = 'Path 25 (Tiphareth-Yesod)', attribution_french = 'Capricorn' WHERE key_scale = 15; -- Devil
UPDATE correspondences SET hebrew_letter_french = 'Ayin (ע)', path_or_sephira_french = 'Path 26 (Chesed-Hod)', attribution_french = 'Mars' WHERE key_scale = 16; -- Tower
UPDATE correspondences SET hebrew_letter_french = 'Peh (פ)', path_or_sephira_french = 'Path 27 (Netzach-Hod)', attribution_french = 'Aquarius' WHERE key_scale = 17; -- Star
UPDATE correspondences SET hebrew_letter_french = 'Tzaddi (צ)', path_or_sephira_french = 'Path 28 (Netzach-Yesod)', attribution_french = 'Pisces' WHERE key_scale = 18; -- Moon
UPDATE correspondences SET hebrew_letter_french = 'Qoph (ק)', path_or_sephira_french = 'Path 29 (Netzach-Malkuth)', attribution_french = 'Sun' WHERE key_scale = 19; -- Sun
UPDATE correspondences SET hebrew_letter_french = 'Resh (ר)', path_or_sephira_french = 'Path 30 (Hod-Malkuth)', attribution_french = 'Fire / Spirit' WHERE key_scale = 20; -- Judgment
UPDATE correspondences SET hebrew_letter_french = 'Shin (ש)', path_or_sephira_french = 'Path 31 (Yesod-Malkuth)', attribution_french = 'Unnumbered / Primeval Spirit' WHERE key_scale = 0; -- The Fool
UPDATE correspondences SET hebrew_letter_french = 'Tav (ת)', path_or_sephira_french = 'Path 32 (Malkuth-Universe)', attribution_french = 'Saturn / Earth' WHERE key_scale = 21; -- The World

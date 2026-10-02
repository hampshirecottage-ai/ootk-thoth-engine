-- Fixes correspondence errors found in the seed 777-77 French/Egyptian run.
-- Safe to re-run: every statement sets absolute values.
--
--  1. French numbering: Thoth keeps the Marseille order (VIII Adjustment, XI Lust), so in the
--     Levi/Papus sequence Adjustment is French 8 (Cheth) and Lust is French 11 (Kaph).
--     The earlier migration used the Waite swap and gave Adjustment Kaph and Lust Cheth.
--  2. French path labels: the "Path N (A-B)" text skipped path 13 (Kether-Tiphareth), so every
--     label from 13 on named the next path's Sephiroth. Labels now use the standard tree
--     (same endpoints as analysis.GD_PATH_ENDPOINTS).
--  3. correspondences.french_path: the key_scale of the path carrying the French letter. The
--     French query joins on it so spatial type, Platonic solid and King Scale colour follow
--     the French letter instead of the card's Golden Dawn letter.
--  4. thoth_cards.attribution: card-level attribution for Minors and Courts. Pips get their
--     Book of Thoth decan (6 of Disks = Moon in Taurus) instead of their Sephira's element;
--     Courts get their element-of-element title and zodiacal span.
--  5. Court key_scale: every Knight, Queen and Prince sits on the sign holding 20 degrees of
--     its span; every Princess on her suit's element letter. Nine courts were inconsistent.
--  6. Golden Dawn rows: planetary letters showed '...' as attribution, Cheth (Cancer) was
--     tagged Air, Chokmah and Binah were both 'Root of Air', and Mem was spelled 'Maim'.

BEGIN;

-- 1. French numbers for the two swapped Majors
UPDATE thoth_cards SET french_number = 8  WHERE title = 'VIII - Adjustment';
UPDATE thoth_cards SET french_number = 11 WHERE title = 'XI - Lust';
UPDATE correspondences SET attribution_french = 'Justice / Libra' WHERE key_scale = 8;
UPDATE correspondences SET attribution_french = 'Strength / Leo'  WHERE key_scale = 11;

-- 2 + 3. French path labels and the path that carries each French letter
ALTER TABLE correspondences ADD COLUMN IF NOT EXISTS french_path integer;

UPDATE correspondences AS c
SET path_or_sephira_french = v.label, french_path = v.path
FROM (VALUES
    (0,  31, 'Path 31 (Hod-Malkuth)'),        -- Fool: Shin
    (1,  11, 'Path 11 (Kether-Chokmah)'),     -- Magus: Aleph
    (2,  12, 'Path 12 (Kether-Binah)'),       -- Priestess: Beth
    (3,  13, 'Path 13 (Kether-Tiphareth)'),   -- Empress: Gimel
    (4,  14, 'Path 14 (Chokmah-Binah)'),      -- Emperor: Daleth
    (5,  15, 'Path 15 (Chokmah-Tiphareth)'),  -- Hierophant: Heh
    (6,  16, 'Path 16 (Chokmah-Chesed)'),     -- Lovers: Vav
    (7,  17, 'Path 17 (Binah-Tiphareth)'),    -- Chariot: Zain
    (8,  18, 'Path 18 (Binah-Geburah)'),      -- Justice / Adjustment: Cheth
    (9,  19, 'Path 19 (Chesed-Geburah)'),     -- Hermit: Teth
    (10, 20, 'Path 20 (Chesed-Tiphareth)'),   -- Fortune: Yod
    (11, 21, 'Path 21 (Chesed-Netzach)'),     -- Strength / Lust: Kaph
    (12, 22, 'Path 22 (Geburah-Tiphareth)'),  -- Hanged Man: Lamed
    (13, 23, 'Path 23 (Geburah-Hod)'),        -- Death: Mem
    (14, 24, 'Path 24 (Tiphareth-Netzach)'),  -- Art: Nun
    (15, 25, 'Path 25 (Tiphareth-Yesod)'),    -- Devil: Samekh
    (16, 26, 'Path 26 (Tiphareth-Hod)'),      -- Tower: Ayin
    (17, 27, 'Path 27 (Netzach-Hod)'),        -- Star: Peh
    (18, 28, 'Path 28 (Netzach-Yesod)'),      -- Moon: Tzaddi
    (19, 29, 'Path 29 (Netzach-Malkuth)'),    -- Sun: Qoph
    (20, 30, 'Path 30 (Hod-Yesod)'),          -- Aeon: Resh
    (21, 32, 'Path 32 (Yesod-Malkuth)')       -- Universe: Tav
) AS v(key_scale, path, label)
WHERE c.key_scale = v.key_scale;

-- 4. Card-level attributions for Minors and Courts
ALTER TABLE thoth_cards ADD COLUMN IF NOT EXISTS attribution varchar(100);

UPDATE thoth_cards AS t SET attribution = v.attr
FROM (VALUES
    ('Ace of Wands', 'Root of the Powers of Fire'),
    ('2 of Wands - Dominion', 'Mars in Aries'),
    ('3 of Wands - Virtue', 'Sun in Aries'),
    ('4 of Wands - Completion', 'Venus in Aries'),
    ('5 of Wands - Strife', 'Saturn in Leo'),
    ('6 of Wands - Victory', 'Jupiter in Leo'),
    ('7 of Wands - Valour', 'Mars in Leo'),
    ('8 of Wands - Swiftness', 'Mercury in Sagittarius'),
    ('9 of Wands - Strength', 'Moon in Sagittarius'),
    ('10 of Wands - Oppression', 'Saturn in Sagittarius'),
    ('Ace of Cups', 'Root of the Powers of Water'),
    ('2 of Cups - Love', 'Venus in Cancer'),
    ('3 of Cups - Abundance', 'Mercury in Cancer'),
    ('4 of Cups - Luxury', 'Moon in Cancer'),
    ('5 of Cups - Disappointment', 'Mars in Scorpio'),
    ('6 of Cups - Pleasure', 'Sun in Scorpio'),
    ('7 of Cups - Debauch', 'Venus in Scorpio'),
    ('8 of Cups - Indolence', 'Saturn in Pisces'),
    ('9 of Cups - Happiness', 'Jupiter in Pisces'),
    ('10 of Cups - Satiety', 'Mars in Pisces'),
    ('Ace of Swords', 'Root of the Powers of Air'),
    ('2 of Swords - Peace', 'Moon in Libra'),
    ('3 of Swords - Sorrow', 'Saturn in Libra'),
    ('4 of Swords - Truce', 'Jupiter in Libra'),
    ('5 of Swords - Defeat', 'Venus in Aquarius'),
    ('6 of Swords - Science', 'Mercury in Aquarius'),
    ('7 of Swords - Futility', 'Moon in Aquarius'),
    ('8 of Swords - Interference', 'Jupiter in Gemini'),
    ('9 of Swords - Cruelty', 'Mars in Gemini'),
    ('10 of Swords - Ruin', 'Sun in Gemini'),
    ('Ace of Disks', 'Root of the Powers of Earth'),
    ('2 of Disks - Change', 'Jupiter in Capricorn'),
    ('3 of Disks - Works', 'Mars in Capricorn'),
    ('4 of Disks - Power', 'Sun in Capricorn'),
    ('5 of Disks - Worry', 'Mercury in Taurus'),
    ('6 of Disks - Success', 'Moon in Taurus'),
    ('7 of Disks - Failure', 'Saturn in Taurus'),
    ('8 of Disks - Prudence', 'Sun in Virgo'),
    ('9 of Disks - Gain', 'Venus in Virgo'),
    ('10 of Disks - Wealth', 'Mercury in Virgo'),
    ('Knight of Wands', 'Fire of Fire - 20° Scorpio to 20° Sagittarius'),
    ('Queen of Wands', 'Water of Fire - 20° Pisces to 20° Aries'),
    ('Prince of Wands', 'Air of Fire - 20° Cancer to 20° Leo'),
    ('Princess of Wands', 'Earth of Fire - Cancer, Leo, Virgo quadrant'),
    ('Knight of Cups', 'Fire of Water - 20° Aquarius to 20° Pisces'),
    ('Queen of Cups', 'Water of Water - 20° Gemini to 20° Cancer'),
    ('Prince of Cups', 'Air of Water - 20° Libra to 20° Scorpio'),
    ('Princess of Cups', 'Earth of Water - Libra, Scorpio, Sagittarius quadrant'),
    ('Knight of Swords', 'Fire of Air - 20° Taurus to 20° Gemini'),
    ('Queen of Swords', 'Water of Air - 20° Virgo to 20° Libra'),
    ('Prince of Swords', 'Air of Air - 20° Capricorn to 20° Aquarius'),
    ('Princess of Swords', 'Earth of Air - Capricorn, Aquarius, Pisces quadrant'),
    ('Knight of Disks', 'Fire of Earth - 20° Leo to 20° Virgo'),
    ('Queen of Disks', 'Water of Earth - 20° Sagittarius to 20° Capricorn'),
    ('Prince of Disks', 'Air of Earth - 20° Aries to 20° Taurus'),
    ('Princess of Disks', 'Earth of Earth - Aries, Taurus, Gemini quadrant')
) AS v(title, attr)
WHERE t.title = v.title;

-- 5. Court key_scale: the sign holding 20 degrees of the span, on the path its Thoth Major
--    uses (the Thoth swap: Aries on 28 = Tzaddi with the Emperor, Aquarius on 15 = Heh with
--    the Star); Princesses on their element's letter.
UPDATE thoth_cards AS t SET key_scale = v.ks
FROM (VALUES
    ('Knight of Wands', 25),    -- Sagittarius (Samekh)
    ('Queen of Wands', 28),     -- Aries (Tzaddi, with the Emperor)
    ('Prince of Wands', 19),    -- Leo (Teth)
    ('Princess of Wands', 31),  -- Fire (Shin)
    ('Knight of Cups', 29),     -- Pisces (Qoph)
    ('Queen of Cups', 18),      -- Cancer (Cheth)
    ('Prince of Cups', 24),     -- Scorpio (Nun)
    ('Princess of Cups', 23),   -- Water (Mem)
    ('Knight of Swords', 17),   -- Gemini (Zain)
    ('Queen of Swords', 22),    -- Libra (Lamed)
    ('Prince of Swords', 15),   -- Aquarius (Heh, with the Star)
    ('Princess of Swords', 11), -- Air (Aleph)
    ('Knight of Disks', 20),    -- Virgo (Yod)
    ('Queen of Disks', 26),     -- Capricorn (Ayin)
    ('Prince of Disks', 16),    -- Taurus (Vau)
    ('Princess of Disks', 32)   -- Earth (Tau)
) AS v(title, ks)
WHERE t.title = v.title;

-- 6. Golden Dawn row fixes
UPDATE correspondences AS c SET element_or_planet_or_sign = v.attr
FROM (VALUES
    (2,  'Root of 🜂'),    -- Chokmah: Root of Fire
    (3,  'Root of 🜄'),    -- Binah: Root of Water
    (12, 'Mercury'),       -- Beth
    (13, 'Moon'),          -- Gimel
    (14, 'Venus'),         -- Daleth
    (18, 'Mars - 🜄'),     -- Cheth (Cancer, Water), matching Nun and Qoph
    (21, 'Jupiter'),       -- Kaph
    (27, 'Mars'),          -- Peh
    (30, 'Sun'),           -- Resh
    (32, 'Saturn - 🜃')    -- Tav (Saturn / Earth)
) AS v(key_scale, attr)
WHERE c.key_scale = v.key_scale;

UPDATE correspondences SET hebrew_letter = 'מ (Mem)' WHERE key_scale = 23;

COMMIT;

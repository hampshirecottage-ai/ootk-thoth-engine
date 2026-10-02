-- Card-level attributions for the Majors, and the Universe's path name.
-- Safe to re-run: every statement sets absolute values. Run after fix_correspondences.sql.
--
--  1. thoth_cards.attribution for the Majors: the card's own sign, planet or element
--     (Lust = Leo). Without it the Attribution field fell back to the letter's row in
--     correspondences, which holds the triplicity rulers of the sign's element
--     ('Sun - 🜂 - Jupiter' for Lust, only 'Mars - 🜄' for the Water signs). Being card-level,
--     it also keeps the Thoth swap right: the Emperor sits on Tzaddi but stays Aries, and
--     the Star sits on Heh but stays Aquarius.
--  2. Path 32 (Tav) is named 'Cross', not 'Tau (as Egyptian)'.

BEGIN;

UPDATE thoth_cards AS tc SET attribution = v.attribution
FROM (VALUES
    ('0 - The Fool', 'Air'),            ('I - The Magus', 'Mercury'),
    ('II - The Priestess', 'Moon'),     ('III - The Empress', 'Venus'),
    ('IV - The Emperor', 'Aries'),      ('V - The Hierophant', 'Taurus'),
    ('VI - The Lovers', 'Gemini'),      ('VII - The Chariot', 'Cancer'),
    ('VIII - Adjustment', 'Libra'),     ('IX - The Hermit', 'Virgo'),
    ('X - Fortune', 'Jupiter'),         ('XI - Lust', 'Leo'),
    ('XII - The Hanged Man', 'Water'),  ('XIII - Death', 'Scorpio'),
    ('XIV - Art', 'Sagittarius'),       ('XV - The Devil', 'Capricorn'),
    ('XVI - The Tower', 'Mars'),        ('XVII - The Star', 'Aquarius'),
    ('XVIII - The Moon', 'Pisces'),     ('XIX - The Sun', 'Sun'),
    ('XX - The Aeon', 'Fire / Spirit'), ('XXI - The Universe', 'Saturn / Earth')
) AS v(title, attribution)
WHERE tc.title = v.title;

UPDATE correspondences SET name = 'Cross' WHERE key_scale = 32;

COMMIT;

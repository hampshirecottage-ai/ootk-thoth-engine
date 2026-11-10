"""Scoring rules shared by every analysis: elemental dignities and aspects.

This is the one place these values live; analysis and spreads both read from it.
"""
from collections import namedtuple

# ---------- Elemental dignities (Book T) ----------
# Book T: "Swords are inimical to Pentacles; Wands to Cups. Swords are friendly with Cups
# and Wands; Wands are friendly with Swords and Pentacles." So each element is contrary
# to its opposite and friendly with the other two; a card beside its own element is strong.
CONTRARY_ELEMENTS = {"Fire": "Water", "Water": "Fire", "Air": "Earth", "Earth": "Air"}

DIGNITY_SAME = 2         # same element: strongly dignified
DIGNITY_FRIENDLY = 1     # friendly elements
DIGNITY_CONTRARY = -2    # contrary elements: ill-dignified
DIGNITY_NEUTRAL = 0      # Spirit on either side (analysis gives an unmapped card Spirit)


def element_dignity(elem1, elem2):
    """Book T dignity between two elements. Returns (score, relationship label)."""
    if elem1 == "Spirit" or elem2 == "Spirit":
        return DIGNITY_NEUTRAL, "Neutral / Spiritual Synthesis"
    if elem1 == elem2:
        return DIGNITY_SAME, f"Strong / Same Element ({elem1} + {elem2})"
    if CONTRARY_ELEMENTS.get(elem1) == elem2:
        return DIGNITY_CONTRARY, f"Contrary / Ill-Dignified ({elem1} + {elem2})"
    return DIGNITY_FRIENDLY, f"Friendly ({elem1} + {elem2})"


# ---------- Aspects ----------
Aspect = namedtuple("Aspect", "name angle score nature")

ASPECTS = (
    Aspect("Conjunction", 0.0,   2,  "Direct Focus / Synthesis"),
    Aspect("Sextile",     60.0,  1,  "Harmonic Alignment / Opportunity"),
    Aspect("Square",      90.0,  -2, "Dynamic Tension / Quadrature Friction"),
    Aspect("Trine",       120.0, 2,  "Equilateral Flow / Resonance"),
    Aspect("Quincunx",    150.0, -1, "Inconjunct / Forced Adjustment"),
    Aspect("Opposition",  180.0, -1, "Polar Complement / Axis Tension"),
)
ASPECTS_BY_NAME = {a.name: a for a in ASPECTS}

# Orbs (degrees either side of exact) differ by context, because the inputs differ:
# - layout: hand-drawn spread layouts, where positions only roughly sit on an aspect angle
# - ring:   houses / signs / decans rings, which sit on exact multiples of 10 or 30 degrees
# - decan:  traditional orbs between decan centres
ORBS = {
    "layout": {"Conjunction": 15, "Sextile": 10, "Square": 10, "Trine": 10,
               "Quincunx": 5, "Opposition": 15},
    "ring":   {name: 1.0 for name in ASPECTS_BY_NAME},
    "decan":  {"Conjunction": 6, "Sextile": 5, "Square": 6, "Trine": 6,
               "Quincunx": 6, "Opposition": 6},
}


def separation(angle_deg):
    """Shortest angular distance on the circle, 0-180."""
    norm = abs(angle_deg) % 360
    return 360 - norm if norm > 180 else norm


def find_aspect(angle_deg, context, allowed=None):
    """The aspect `angle_deg` falls within, using `context`'s orbs, or None.

    `allowed` optionally limits the search to some aspect names.
    """
    sep = separation(angle_deg)
    for aspect in ASPECTS:
        if allowed is not None and aspect.name not in allowed:
            continue
        if abs(sep - aspect.angle) <= ORBS[context][aspect.name]:
            return aspect
    return None


def aspect_label(aspect):
    """'Trine (120°)'."""
    return f"{aspect.name} ({aspect.angle:g}°)"

# ---------- Geomantic figures (Golden Dawn) ----------
# The Golden Dawn's figure for each sign, as in Liber 777's "Lineal Figures and Geomancy"
# column. Caput and Cauda Draconis take no sign, so no card carries them.
GEOMANTIC_FIGURES = {
    "Aries": "Puer", "Taurus": "Amissio", "Gemini": "Albus", "Cancer": "Populus and Via",
    "Leo": "Fortuna Major and Fortuna Minor", "Virgo": "Conjunctio", "Libra": "Puella",
    "Scorpio": "Rubeus", "Sagittarius": "Acquisitio", "Capricorn": "Carcer",
    "Aquarius": "Tristitia", "Pisces": "Laetitia",
}

# ---------- Planetary dignity (essential dignity of a planet in a sign) ----------
# The classical scheme with the seven planets of the decans, as Crowley uses it in the Book of
# Thoth (e.g. 3 of Wands: Sun exalted in Aries). Signs with no classical exaltation or fall
# have none here. Mercury is both ruler and exalted in Virgo, and both in detriment and fall
# in Pisces.
PLANET_RULERS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon", "Leo": "Sun",
    "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars", "Sagittarius": "Jupiter",
    "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}
PLANET_EXALTATIONS = {
    "Aries": "Sun", "Taurus": "Moon", "Cancer": "Jupiter", "Virgo": "Mercury",
    "Libra": "Saturn", "Capricorn": "Mars", "Pisces": "Venus",
}
_OPPOSITE_SIGN = {
    "Aries": "Libra", "Taurus": "Scorpio", "Gemini": "Sagittarius", "Cancer": "Capricorn",
    "Leo": "Aquarius", "Virgo": "Pisces", "Libra": "Aries", "Scorpio": "Taurus",
    "Sagittarius": "Gemini", "Capricorn": "Cancer", "Aquarius": "Leo", "Pisces": "Virgo",
}
def planet_dignities(planet, sign):
    """List of "ruler", "exalted", "detriment", "fall" for planet in sign (often empty)."""
    if sign not in PLANET_RULERS:
        return []
    opposite = _OPPOSITE_SIGN[sign]
    found = []
    if PLANET_RULERS[sign] == planet:
        found.append("ruler")
    if PLANET_EXALTATIONS.get(sign) == planet:
        found.append("exalted")
    if PLANET_RULERS[opposite] == planet:
        found.append("detriment")
    if PLANET_EXALTATIONS.get(opposite) == planet:
        found.append("fall")
    return found

_DIGNITY_LABELS = {
    ("ruler",): "rules this sign (strong)",
    ("exalted",): "exalted (strong)",
    ("ruler", "exalted"): "rules this sign and is exalted (strong)",
    ("detriment",): "in detriment (weakened)",
    ("fall",): "in fall (weakest)",
    ("detriment", "fall"): "in detriment and fall (weakest)",
}

def planet_dignity_note(attribution):
    """ "exalted (strong)" for "Sun in Aries" (the Attribution line already names the planet and
    sign), or None when the attribution is not "Planet in Sign" or the planet has no dignity or
    debility there."""
    planet, sep, sign = (attribution or "").partition(" in ")
    found = planet_dignities(planet.strip(), sign.strip()) if sep else []
    return _DIGNITY_LABELS.get(tuple(found))

# ---------- Book T counts ----------
# Book T reads three or four cards of one rank in a reading, and a lead of Trumps, court
# cards, Aces or one suit. These are the rank names the counts use (Thoth court titles).
RANK_PLURALS = {
    "1": "Aces", "2": "Twos", "3": "Threes", "4": "Fours", "5": "Fives", "6": "Sixes",
    "7": "Sevens", "8": "Eights", "9": "Nines", "10": "Tens",
    "Knight": "Knights", "Queen": "Queens", "Prince": "Princes", "Princess": "Princesses",
}
SUIT_ORDER = ("Wands", "Cups", "Swords", "Disks")

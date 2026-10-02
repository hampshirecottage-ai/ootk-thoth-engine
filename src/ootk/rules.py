"""Scoring rules shared by every analysis: elemental dignities and aspects.

This is the one place these values live; analysis, spreads and decans all read from it.
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
DIGNITY_NEUTRAL = 0      # Spirit (or an unmapped card) on either side


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

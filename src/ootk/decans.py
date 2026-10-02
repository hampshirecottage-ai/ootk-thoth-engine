"""
decan_aspects.py

Astrological Decan & Planetary Aspect Engine for the Thoth Tarot.
Evaluates ecliptic longitudes, planetary decan rulers, and angular aspects
between Minor Arcana cards (2-10) in accordance with Crowley's Book of Thoth.
"""

DECAN_MAP = {
    # FIRE SUIT (Wands)
    "2 of Wands":  {"sign": "Aries",       "decan": 1, "ruler": "Mars",    "center_deg": 5},
    "3 of Wands":  {"sign": "Aries",       "decan": 2, "ruler": "Sun",     "center_deg": 15},
    "4 of Wands":  {"sign": "Aries",       "decan": 3, "ruler": "Venus",   "center_deg": 25},
    "5 of Wands":  {"sign": "Leo",         "decan": 1, "ruler": "Saturn",  "center_deg": 125},
    "6 of Wands":  {"sign": "Leo",         "decan": 2, "ruler": "Jupiter", "center_deg": 135},
    "7 of Wands":  {"sign": "Leo",         "decan": 3, "ruler": "Mars",    "center_deg": 145},
    "8 of Wands":  {"sign": "Sagittarius", "decan": 1, "ruler": "Mercury", "center_deg": 245},
    "9 of Wands":  {"sign": "Sagittarius", "decan": 2, "ruler": "Moon",    "center_deg": 255},
    "10 of Wands": {"sign": "Sagittarius", "decan": 3, "ruler": "Saturn",  "center_deg": 265},

    # WATER SUIT (Cups)
    "2 of Cups":  {"sign": "Cancer",      "decan": 1, "ruler": "Venus",   "center_deg": 95},
    "3 of Cups":  {"sign": "Cancer",      "decan": 2, "ruler": "Mercury", "center_deg": 105},
    "4 of Cups":  {"sign": "Cancer",      "decan": 3, "ruler": "Moon",    "center_deg": 115},
    "5 of Cups":  {"sign": "Scorpio",     "decan": 1, "ruler": "Mars",    "center_deg": 215},
    "6 of Cups":  {"sign": "Scorpio",     "decan": 2, "ruler": "Sun",     "center_deg": 225},
    "7 of Cups":  {"sign": "Scorpio",     "decan": 3, "ruler": "Venus",   "center_deg": 235},
    "8 of Cups":  {"sign": "Pisces",      "decan": 1, "ruler": "Saturn",  "center_deg": 335},
    "9 of Cups":  {"sign": "Pisces",      "decan": 2, "ruler": "Jupiter", "center_deg": 345},
    "10 of Cups": {"sign": "Pisces",      "decan": 3, "ruler": "Mars",    "center_deg": 355},

    # AIR SUIT (Swords)
    "2 of Swords":  {"sign": "Libra",       "decan": 1, "ruler": "Moon",    "center_deg": 185},
    "3 of Swords":  {"sign": "Libra",       "decan": 2, "ruler": "Saturn",  "center_deg": 195},
    "4 of Swords":  {"sign": "Libra",       "decan": 3, "ruler": "Jupiter", "center_deg": 205},
    "5 of Swords":  {"sign": "Aquarius",    "decan": 1, "ruler": "Venus",   "center_deg": 305},
    "6 of Swords":  {"sign": "Aquarius",    "decan": 2, "ruler": "Mercury", "center_deg": 315},
    "7 of Swords":  {"sign": "Aquarius",    "decan": 3, "ruler": "Moon",    "center_deg": 325},
    "8 of Swords":  {"sign": "Gemini",      "decan": 1, "ruler": "Jupiter", "center_deg": 65},
    "9 of Swords":  {"sign": "Gemini",      "decan": 2, "ruler": "Mars",    "center_deg": 75},
    "10 of Swords": {"sign": "Gemini",      "decan": 3, "ruler": "Sun",     "center_deg": 85},

    # EARTH SUIT (Disks)
    "2 of Disks":  {"sign": "Capricorn",   "decan": 1, "ruler": "Jupiter", "center_deg": 275},
    "3 of Disks":  {"sign": "Capricorn",   "decan": 2, "ruler": "Mars",    "center_deg": 285},
    "4 of Disks":  {"sign": "Capricorn",   "decan": 3, "ruler": "Sun",     "center_deg": 295},
    "5 of Disks":  {"sign": "Taurus",      "decan": 1, "ruler": "Mercury", "center_deg": 35},
    "6 of Disks":  {"sign": "Taurus",      "decan": 2, "ruler": "Moon",    "center_deg": 45},
    "7 of Disks":  {"sign": "Taurus",      "decan": 3, "ruler": "Saturn",  "center_deg": 55},
    "8 of Disks":  {"sign": "Virgo",       "decan": 1, "ruler": "Sun",     "center_deg": 155},
    "9 of Disks":  {"sign": "Virgo",       "decan": 2, "ruler": "Venus",   "center_deg": 165},
    "10 of Disks": {"sign": "Virgo",       "decan": 3, "ruler": "Mercury", "center_deg": 175},
}

MAJOR_ASPECTS = [
    {"name": "Conjunction", "target_deg": 0,   "orb": 6, "score": 2,  "nature": "Concentrated Focus / Synthesis"},
    {"name": "Sextile",     "target_deg": 60,  "orb": 5, "score": 1,  "nature": "Harmonic Opportunity / Active Flow"},
    {"name": "Square",      "target_deg": 90,  "orb": 6, "score": -2, "nature": "Quadrature Friction / Challenge"},
    {"name": "Trine",       "target_deg": 120, "orb": 6, "score": 2,  "nature": "Elemental Resonance / Unimpeded Power"},
    {"name": "Opposition",  "target_deg": 180, "orb": 6, "score": -2, "nature": "Polar Tension / Axis Challenge"}
]

# Friendships / Hostilities among classical Decan Rulers
PLANETARY_RELATIONS = {
    ("Sun", "Jupiter"): 1,  ("Sun", "Mars"): 1,    ("Sun", "Saturn"): -2,
    ("Venus", "Mars"): 1,   ("Venus", "Saturn"): -1,
    ("Moon", "Venus"): 1,   ("Moon", "Saturn"): -2,
    ("Saturn", "Mars"): -2
}


def calculate_ecliptic_delta(deg1: float, deg2: float) -> float:
    """Calculates the shortest angular distance along the 360-degree ecliptic circle."""
    delta = abs(deg1 - deg2) % 360
    return delta if delta <= 180 else 360 - delta


def evaluate_decan_aspect(card_a_title: str, card_b_title: str):
    """
    Evaluates astrological aspect between two cards if both exist in the Decan map.
    Returns aspect dictionary or None if one or both cards are non-decan (Majors/Courts).
    """
    if card_a_title not in DECAN_MAP or card_b_title not in DECAN_MAP:
        return None

    d1 = DECAN_MAP[card_a_title]
    d2 = DECAN_MAP[card_b_title]

    delta = calculate_ecliptic_delta(d1["center_deg"], d2["center_deg"])

    matched_aspect = None
    for aspect in MAJOR_ASPECTS:
        if abs(delta - aspect["target_deg"]) <= aspect["orb"]:
            matched_aspect = aspect
            break

    if not matched_aspect:
        return None

    # Calculate planetary modifier
    p_pair = (d1["ruler"], d2["ruler"])
    p_pair_rev = (d2["ruler"], d1["ruler"])
    p_mod = PLANETARY_RELATIONS.get(p_pair, PLANETARY_RELATIONS.get(p_pair_rev, 0))

    composite_score = matched_aspect["score"] + p_mod

    return {
        "card_a": card_a_title,
        "card_b": card_b_title,
        "decan_a": f"{d1['ruler']} in {d1['sign']} (Decan {d1['decan']})",
        "decan_b": f"{d2['ruler']} in {d2['sign']} (Decan {d2['decan']})",
        "delta_deg": round(delta, 1),
        "aspect_name": matched_aspect["name"],
        "nature": matched_aspect["nature"],
        "planetary_synergy": p_mod,
        "composite_score": composite_score
    }


def analyze_spread_decan_aspects(spread_results: list) -> list:
    """
    Scans a drawn spread for adjacent and major positional pairwise Decan aspects.
    """
    aspect_reports = []
    n = len(spread_results)

    for i in range(n - 1):
        c1 = spread_results[i]
        c2 = spread_results[i + 1]

        title1 = c1["card_data"]["title"]
        title2 = c2["card_data"]["title"]

        res = evaluate_decan_aspect(title1, title2)
        if res:
            res["positions"] = f"Pos {c1['position_number']} <-> Pos {c2['position_number']}"
            aspect_reports.append(res)

    return aspect_reports

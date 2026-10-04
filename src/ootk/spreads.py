"""Spread definitions, layout coordinates and operation segments."""
import math
import re

from ootk.rules import ASPECTS_BY_NAME, aspect_label

ZODIAC_SIGNS = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
                "Sagittarius", "Capricorn", "Aquarius", "Pisces")
_SIGN_SUITS = {"Fire": "Wands", "Earth": "Disks", "Air": "Swords", "Water": "Cups"}
_CHALDEAN = ("Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon")

def _decan_labels():
    """'Decan 1: Mars in Aries (2 of Wands)' ... 'Decan 36: Mars in Pisces (10 of Cups)'.

    Rulers run in Chaldean order from Mars at 0 deg Aries; each sign's three decans are its
    suit's 2-4 (cardinal), 5-7 (fixed) or 8-10 (mutable), as in the Book of Thoth.
    """
    elements = ("Fire", "Earth", "Air", "Water")
    labels = []
    for i in range(36):
        sign_idx, third = divmod(i, 3)
        ruler = _CHALDEAN[(2 + i) % 7]
        pip = 2 + 3 * (sign_idx % 3) + third
        suit = _SIGN_SUITS[elements[sign_idx % 4]]
        labels.append(f"Decan {i + 1}: {ruler} in {ZODIAC_SIGNS[sign_idx]} ({pip} of {suit})")
    return labels

SPREADS = {
    "1": {"name": "Single Card / Daily Operations", "positions": ["Core Theme / Focus"]},
    "2": {"name": "Dyad (Polarity & Dynamics)", "positions": ["Active Force (Thesis)", "Receptive / Resistance Force (Antithesis)"]},
    "3": {"name": "Triad (Timeline & Motion)", "positions": ["Past / Root Cause", "Present / Active Dynamics", "Future / Manifest Result"]},
    "4": {
        "name": "Sub-Elemental Quadrant Cross (Elemental Sub-Division)",
        "positions": [
            "1. Yod of Yod (Fire of Fire - Pure Flash)",
            "2. Heh of Yod (Water of Fire - Emotional Will)",
            "3. Vav of Yod (Air of Fire - Directed Focus)",
            "4. Heh Final of Yod (Earth of Fire - Physicalized Action)"
        ]
    },
    "5": {
        "name": "Tetragrammaton Spread (4 Elemental Vectors)",
        "positions": [
            "Atziluth / Yod (Fire - Creative Spark)", 
            "Briah / Heh (Water - Mental/Emotional Container)", 
            "Yetzirah / Vav (Air - Formative Processing)", 
            "Assiah / Heh Final (Earth - Material Result)"
        ]
    },
    "6": {
        "name": "Hexagram Spread (Planetary Operations & Macrocosm)",
        "positions": [
            "1. Saturn (Top Apex / Form, Constraints & Karma)",
            "2. Jupiter (Right Top / Expansion, Luck & Growth)",
            "3. Mars (Left Top / Drive, Severity & Force)",
            "4. Venus (Right Bottom / Harmony, Affection & Value)",
            "5. Mercury (Left Bottom / Intellect, Logic & Communication)",
            "6. Sun (Center Core / Core Vitality, Identity & Spirit)",
            "7. Moon (Bottom Apex / Subconscious, Instinct & Foundation)"
        ]
    },
    "7": {
        "name": "Tree of Life Layout (10 Sephiroth Mapping)",
        "positions": [
            "1. Kether (Crown / Primary Impulse)",
            "2. Chokmah (Wisdom / Dynamic Force)",
            "3. Binah (Understanding / Structural Form)",
            "4. Chesed (Mercy / Expansion)",
            "5. Geburah (Severity / Action & Severity)",
            "6. Tiphareth (Beauty / Harmony & Core Self)",
            "7. Netzach (Victory / Emotions & Instinct)",
            "8. Hod (Splendor / Intellect & Logic)",
            "9. Yesod (Foundation / Subconscious & Astral)",
            "10. Malkuth (Kingdom / Manifest World)"
        ]
    },
    "8": {
        # Not the classic OOTK First Operation, which splits the whole deck into four IHVH
        # piles and reads the pile holding the significator.
        "name": "15-Card Heap (OOTK Op 1 variant, not the IHVH four-pile split)",
        "positions": [
            "1. Significator / Core Nature of Question",
            "2. Development of Question (Left Pair A)", "3. Development of Question (Left Pair B)",
            "4. Further Outcome (Right Pair A)", "5. Further Outcome (Right Pair B)",
            "6. Unexpected / External Factors (Center Pair A)", "7. Unexpected / External Factors (Center Pair B)",
            "8. Psychological / Subconscious Basis (Base Left A)", "9. Psychological / Subconscious Basis (Base Left B)",
            "10. Environmental / Material Basis (Base Right A)", "11. Environmental / Material Basis (Base Right B)",
            "12. Final Synthesis / Karma (Top Apex A)", "13. Final Synthesis / Karma (Top Apex B)",
            "14. Key Counter-Balance / Receptivity", "15. Ultimate Climax / Resolution"
        ]
    },
    "9": {
        "name": "OOTK - Second Operation (12 Astrological Houses)",
        "positions": [
            "1. First House (Ascendant / Physical Self)", "2. Second House (Finances & Values)",
            "3. Third House (Local Mind & Travel)", "4. Fourth House (Home & Roots)",
            "5. Fifth House (Creativity & Will)", "6. Sixth House (Health & Work)",
            "7. Seventh House (Partnerships)", "8. Eighth House (Shared Assets & Death)",
            "9. Ninth House (Philosophy & Higher Mind)", "10. Tenth House (Career & Public Standing)",
            "11. Eleventh House (Alliances & Hopes)", "12. Twelfth House (Subconscious & Hidden)"
        ]
    },
    "10": {
        "name": "OOTK - Third Operation (12 Zodiacal Signs)",
        "positions": [
            "1. Aries", "2. Taurus", "3. Gemini", "4. Cancer", "5. Leo", "6. Virgo",
            "7. Libra", "8. Scorpio", "9. Sagittarius", "10. Capricorn", "11. Aquarius", "12. Pisces"
        ]
    },
    "11": {
        "name": "OOTK - Fourth Operation (36 Zodiacal Decans)",
        "positions": _decan_labels()
    },
    "12": {
        "name": "Complete Opening of the Key (OOTK) - 4-Operation Master Pipeline",
        "operations": ["8", "9", "10", "11"]
    }
}

def spread_positions(spread_key):
    """Ordered position labels for a spread; a master pipeline's are tagged '[Op n] '."""
    spread = SPREADS[spread_key]
    if "operations" in spread:
        return [f"[Op {n}] {p}" for n, op_key in enumerate(spread["operations"], start=1)
                for p in SPREADS[op_key]["positions"]]
    return list(spread.get("positions", []))

def _ring(n, start_deg=0.0, step_deg=None):
    """n points on the unit circle, counter-clockwise from start_deg."""
    step = step_deg if step_deg is not None else 360.0 / n
    return [
        (round(math.cos(math.radians(start_deg + i * step)), 3),
         round(math.sin(math.radians(start_deg + i * step)), 3))
        for i in range(n)
    ]

SPREAD_DEFAULT_COORDINATES = {
    "1": [(0.0, 0.0)],
    "2": [(-0.5, 0.0), (0.5, 0.0)],
    "3": [(-1.0, 0.0), (0.0, 0.0), (1.0, 0.0)],
    "4": [(0.0, 1.0), (1.0, 0.0), (0.0, -1.0), (-1.0, 0.0)],
    "5": [(0.0, 1.0), (1.0, 0.0), (-1.0, 0.0), (0.0, -1.0)],
    # Golden Dawn hexagram, planets placed as on the Tree of Life: Saturn (Binah) at the top,
    # Jupiter and Venus on the right, Mars and Mercury on the left, Moon (Yesod) at the
    # bottom and the Sun (Tiphareth) in the centre.
    "6": [(0.0, 1.0), (0.866, 0.5), (-0.866, 0.5), (0.866, -0.5), (-0.866, -0.5), (0.0, 0.0), (0.0, -1.0)],
    "10": [
        (1.0, 0.0), (0.866, 0.5), (0.5, 0.866), (0.0, 1.0),
        (-0.5, 0.866), (-0.866, 0.5), (-1.0, 0.0), (-0.866, -0.5),
        (-0.5, -0.866), (0.0, -1.0), (0.5, -0.866), (0.866, -0.5)
    ],
    # OOTK Op 1: schematic heap (x right, y up). Significator at centre, development pair
    # left, outcome pair right, external-factors pair just above the significator,
    # psychological and environmental pairs along the base, karma pair at the apex,
    # counter-balance just below the significator, climax above the apex.
    # This is a drawing convention, not a canonical layout - edit freely.
    "8": [
        (0.0, 0.0),
        (-2.25, 0.0), (-1.75, 0.0),
        (1.75, 0.0), (2.25, 0.0),
        (-0.25, 0.75), (0.25, 0.75),
        (-1.25, -1.5), (-0.75, -1.5),
        (0.75, -1.5), (1.25, -1.5),
        (-0.25, 2.0), (0.25, 2.0),
        (0.0, -0.75),
        (0.0, 3.0)
    ],
    # OOTK Op 2: chart wheel, house 1 at 9 o'clock (180 deg), houses running counter-clockwise
    # (house 4 at the bottom, house 7 at 3 o'clock, house 10 at the top).
    "9": _ring(12, start_deg=180.0, step_deg=30.0),
    # OOTK Op 4: 36 decans, 10 deg apart, counter-clockwise from 0 deg (Aries 0).
    "11": _ring(36, start_deg=0.0, step_deg=10.0),
}

# Ring layouts (houses, zodiac, decans) are paired by aspect, not by neighbour: consecutive
# positions on a ring always sit the same angle apart, so neighbour geometry carries no
# information. Each position is instead paired with every position it stands in an exact
# major aspect to. Trim a layout's tuple to shorten the report (e.g. decans: Trine and
# Opposition only).
# Report order for ring aspects; names, angles, scores and descriptions come from ootk.rules.
RING_ASPECTS = tuple(
    (a.name, aspect_label(a), a.angle, a.nature, a.score)
    for a in (ASPECTS_BY_NAME[n] for n in ("Opposition", "Square", "Trine", "Sextile"))
)
_ALL_RING_ASPECTS = ("Opposition", "Square", "Trine", "Sextile")
RING_LAYOUT_ASPECTS = {
    "9": _ALL_RING_ASPECTS,    # 12 houses
    "10": _ALL_RING_ASPECTS,   # 12 zodiac signs
    "11": _ALL_RING_ASPECTS,   # 36 decans
}

# Heap layouts are not wheels: their coordinates are a drawing convention, so the angle two
# positions make around the middle of the drawing says nothing about the cards. Neighbouring
# pairs side by side in one heap would read as a 0.8 deg "Conjunction" (+2). Pairs on these
# layouts keep their distance but take no aspect and no modifier.
HEAP_LAYOUTS = {"8"}   # OOTK Op 1

OP_TAG = re.compile(r"^\[Op (\d+)\]")

def spread_segments(spread_results, spread_key):
    """Splits a drawn spread into independent segments: (layout_key, start, end, name).

    A master pipeline (spread with an 'operations' list) yields one segment per operation,
    keyed to that operation's own spread so pairings and geometry never cross operation
    boundaries. Any other spread is a single segment.
    """
    ops = SPREADS.get(spread_key, {}).get("operations")
    if not ops:
        return [(spread_key, 0, len(spread_results), None)]

    segments = []
    for idx, item in enumerate(spread_results):
        m = OP_TAG.match(item["position_name"])
        op_num = int(m.group(1)) if m else 0
        if segments and segments[-1][4] == op_num:
            segments[-1][2] = idx + 1
        else:
            key = ops[op_num - 1] if 1 <= op_num <= len(ops) else None
            name = f"Operation {op_num}: {SPREADS[key]['name']}" if key else None
            segments.append([key, idx, idx + 1, name, op_num])
    return [(k, s_, e_, n_) for k, s_, e_, n_, _ in segments]

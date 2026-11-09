"""Spread definitions, layout coordinates and operation segments."""
import math
import re

from ootk.rules import ASPECTS_BY_NAME, aspect_label

ZODIAC_SIGNS = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
                "Sagittarius", "Capricorn", "Aquarius", "Pisces")
_SIGN_SUITS = {"Fire": "Wands", "Earth": "Disks", "Air": "Swords", "Water": "Cups"}
_CHALDEAN = ("Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon")

# Book T counts the decans from the Royal Star of Leo (Regulus, 0 deg Leo), so the Fourth
# Operation's wheel opens on Saturn in Leo (5 of Wands). This is the index of that decan
# counted from 0 deg Aries, the frame atlas.py and analysis.card_home use.
DECAN_START = 12

def _decan_labels():
    """'Decan 1: Saturn in Leo (5 of Wands)' ... 'Decan 36: Moon in Cancer (4 of Cups)'.

    Rulers run in Chaldean order from Mars at 0 deg Aries; each sign's three decans are its
    suit's 2-4 (cardinal), 5-7 (fixed) or 8-10 (mutable). The wheel starts at DECAN_START.
    """
    elements = ("Fire", "Earth", "Air", "Water")
    labels = []
    for p in range(36):
        i = (p + DECAN_START) % 36
        sign_idx, third = divmod(i, 3)
        ruler = _CHALDEAN[(2 + i) % 7]
        pip = 2 + 3 * (sign_idx % 3) + third
        suit = _SIGN_SUITS[elements[sign_idx % 4]]
        labels.append(f"Decan {p + 1}: {ruler} in {ZODIAC_SIGNS[sign_idx]} ({pip} of {suit})")
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
            "3. Vau of Yod (Air of Fire - Directed Focus)",
            "4. Heh Final of Yod (Earth of Fire - Physicalized Action)"
        ]
    },
    "5": {
        "name": "Tetragrammaton Spread (4 Elemental Vectors)",
        "positions": [
            "Atziluth / Yod (Fire - Creative Spark)", 
            "Briah / Heh (Water - Mental/Emotional Container)", 
            "Yetzirah / Vau (Air - Formative Processing)", 
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
    },
    # Key 13 is Book T (BOOK_T_KEY below), kept out of SPREADS.
    # A.E. Waite's "Ancient Celtic Method" (The Pictorial Key to the Tarot, 1911): the cross of
    # six round the matter, then the staff of four laid upwards on its right.
    "14": {
        "name": "Celtic Cross (Waite, 10 cards)",
        "positions": [
            "1. What Covers (the matter now and its atmosphere)",
            "2. What Crosses (the obstacle or opposing force)",
            "3. What Crowns (the aim, or the best that can come of it)",
            "4. What Is Beneath (the foundation, what is already in hand)",
            "5. What Is Behind (the influence now passing)",
            "6. What Is Before (the influence coming next)",
            "7. The Querent (their own attitude and part)",
            "8. Their House (surroundings and other people)",
            "9. Hopes and Fears",
            "10. What Will Come (the outcome)"
        ]
    },
    # A six-card relationship spread: the two people side by side, what joins and what divides
    # them between, then the advice and where the relationship is heading.
    "15": {
        "name": "Relationship (6 cards)",
        "positions": [
            "1. You (your side: what you bring and how you feel)",
            "2. Them (their side: what they bring and how they feel)",
            "3. What Joins You (the common ground and the bond)",
            "4. What Divides You (the friction or what keeps you apart)",
            "5. Advice (what would help)",
            "6. Where It Is Heading (the likely course of the relationship)"
        ]
    },
    # The common modern six-card spread in two rows of three: the situation along the top
    # (past, present, near future), what acts on it along the bottom, ending on the outcome.
    "16": {
        "name": "Two Rows of Three (6 cards)",
        "positions": [
            "1. Past (what led here)",
            "2. Present (where the matter stands now)",
            "3. Near Future (what is coming next)",
            "4. What Stands in the Way (the obstacle or challenge)",
            "5. Advice (what would help)",
            "6. Outcome (where it is likely to end)"
        ]
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
    # Spreads 4 and 5 both run Yod, Heh, Vav, Heh final, so they share one cross: Yod at the
    # top, Heh on the right, Vav on the left, Heh final at the bottom.
    "4": [(0.0, 1.0), (1.0, 0.0), (-1.0, 0.0), (0.0, -1.0)],
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
    # OOTK Op 4: 36 decans, 10 deg apart, counter-clockwise from 0 deg, where decan 1 (0 deg Leo)
    # sits. Only the angles between positions are scored, so where the ring starts is free.
    "11": _ring(36, start_deg=0.0, step_deg=10.0),
    # Celtic Cross: card 2 lies across card 1 (drawn a little lower and to the right so both
    # show), the crown above, the foundation below, the past on the left, the future on the
    # right, and the staff (7 at the bottom to 10 at the top) on the far right.
    # A drawing convention only: the cross's pairs are named, not angled (NAMED_PAIR_LAYOUTS).
    "14": [
        (0.0, 0.0), (0.3, -0.3),
        (0.0, 1.4), (0.0, -1.4),
        (-1.2, 0.0), (1.2, 0.0),
        (2.6, -1.95), (2.6, -0.65), (2.6, 0.65), (2.6, 1.95)
    ],
    # Relationship: you on the left, them on the right, what joins you above and what divides
    # you below, then advice and where it is heading in a column on the far right.
    # A drawing convention only: its pairs are named, not angled (NAMED_PAIR_LAYOUTS).
    "15": [
        (-1.2, 0.0), (1.2, 0.0),
        (0.0, 1.1), (0.0, -1.1),
        (2.6, -0.65), (2.6, 0.65)
    ],
    # Two rows of three: the situation (1-3) along the top, what acts on it (4-6) below.
    # A drawing convention only: its pairs are named, not angled (NAMED_PAIR_LAYOUTS).
    "16": [
        (-1.2, 0.6), (0.0, 0.6), (1.2, 0.6),
        (-1.2, -0.6), (0.0, -0.6), (1.2, -0.6)
    ],
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

# Which cards of a heap are scored together for elemental dignity (0-based, within the
# operation). Op 1's positions are named in pairs (Left Pair A and B, ...), so each named pair
# is scored as one; the significator is scored with the two single cards that answer it, the
# Counter-Balance (14) and the Climax (15). Deal order alone would also join cards of
# different groups (3 with 4, 5 with 6, ...).
#
# The Celtic Cross is read the same way: the card that covers with the card that crosses it,
# the crown with what is beneath (the vertical axis), what is behind with what is before (the
# time axis), the staff from 7 up to 10, and the matter now (1) with what will come (10).
# Deal order would join unrelated places (2 with 3, 4 with 5, 6 with 7).
#
# The Relationship spread pairs you with them, what joins you with what divides you, and the
# advice with where it is heading. Deal order would join them with what joins you, and so on.
#
# Two rows of three pairs each card with the one beside it in its row and the one below it:
# the past with what stands in the way, the present with the advice, the near future with
# the outcome. Deal order would join the near future (3) to what stands in the way (4).
HEAP_PAIRS = {
    "8": ((1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12), (0, 13), (0, 14)),
    "14": ((0, 1), (2, 3), (4, 5), (6, 7), (7, 8), (8, 9), (0, 9)),
    "15": ((0, 1), (2, 3), (4, 5)),
    "16": ((0, 1), (1, 2), (3, 4), (4, 5), (0, 3), (1, 4), (2, 5)),
}

# Layouts whose pairs are named (HEAP_PAIRS) rather than measured: their drawing coordinates
# are not a wheel, so their pairs keep their distance but take no aspect and no modifier.
# Value: the (aspect name, description) their pairs carry in the spatial section.
NAMED_PAIR_LAYOUTS = {
    "8": ("Heap Pair", "Paired in the heap; a heap has no angular relation"),
    "14": ("Cross Pair", "Paired in the Celtic Cross; its places make no angular relation"),
    "15": ("Relationship Pair", "Paired in the Relationship spread; its places make no angular relation"),
    "16": ("Row Pair", "Paired in two rows of three; its places make no angular relation"),
}
CELTIC_CROSS_KEY = "14"
RELATIONSHIP_KEY = "15"
TWO_ROWS_KEY = "16"

# Tree of Life layouts: positions are the ten Sephiroth in order, so cards are scored along
# the 22 paths that join them (Binah and Chesed, 3 and 4, share no path).
TREE_LAYOUTS = {"7"}

OP_TAG = re.compile(r"^\[Op (\d+)\]")

# Book T's own Opening of the Key (ootk.book_t): five operations, each reading only the pile
# that holds the Significator, so its positions depend on the draw and it is kept out of
# SPREADS (whose positions are fixed). Each operation's positions start with the
# Significator and go rightwards round the pile, so Book T's pairs (the cards either side
# of the Significator, then those outside them) depend only on the pile's size.
BOOK_T_KEY = "13"
BOOK_T_SPREAD = {"name": "Book T Opening of the Key (counting and pairing, 5 operations)"}
BOOK_T_LAYOUT = "book_t"
BOOK_T_OP_NAMES = {
    1: "Operation 1: The Four Packs (I H V H)",
    2: "Operation 2: The Twelve Houses",
    3: "Operation 3: The Twelve Signs",
    4: "Operation 4: The Ring of Thirty-Six",
    5: "Operation 5: The Ten Sephiroth",
}

def book_t_pairs(n):
    """Book T's pairs in a pile of n laid out from the Significator (0) rightwards: the cards
    either side of it, then those outside them. (left, right) index pairs."""
    return [(n - k, k) for k in range(1, n) if k < n - k]

def spread_segments(spread_results, spread_key):
    """Splits a drawn spread into independent segments: (layout_key, start, end, name).

    A master pipeline (spread with an 'operations' list) yields one segment per operation,
    keyed to that operation's own spread so pairings and geometry never cross operation
    boundaries. Any other spread is a single segment.
    """
    if spread_key == BOOK_T_KEY:
        segments = []
        for idx, item in enumerate(spread_results):
            m = OP_TAG.match(item["position_name"])
            name = BOOK_T_OP_NAMES.get(int(m.group(1)) if m else 0)
            if segments and segments[-1][3] == name:
                segments[-1][2] = idx + 1
            else:
                segments.append([BOOK_T_LAYOUT, idx, idx + 1, name])
        return [tuple(s_) for s_ in segments]
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

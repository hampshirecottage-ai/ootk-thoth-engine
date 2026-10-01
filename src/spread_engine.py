import os
import sys
import json
import math
import re
import html
import argparse
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
from src.prng_shuffler import shuffle_deck
CONFIG_PATH = BASE_DIR / "config" / "config.json"

DB_ENV_VARS = {
    "dbname": "DB_NAME", "user": "DB_USER", "password": "DB_PASSWORD",
    "host": "DB_HOST", "port": "DB_PORT",
}

def load_db_config():
    """Loads database credentials from config/config.json with environment variable overrides."""
    config = {
        "dbname": os.getenv("DB_NAME", "my_tarot_db"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", ""),
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432"))
    }
    
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                json_data = json.load(f)
                db_json = json_data.get("database", {})
                for key in config:
                    # config.json only fills a value when the matching env var is unset
                    if key in db_json and not os.getenv(DB_ENV_VARS[key]):
                        config[key] = db_json[key]
        except Exception as e:
            print(f"[WARN] Failed to read {CONFIG_PATH}: {e}")
            
    return config

DB_CONFIG = load_db_config()

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
            "3. Mars (Right Bottom / Drive, Severity & Force)",
            "4. Venus (Bottom Apex / Harmony, Affection & Value)",
            "5. Mercury (Left Bottom / Intellect, Logic & Communication)",
            "6. Sun (Left Top / Core Vitality, Identity & Spirit)",
            "7. Moon (Center Core / Subconscious, Instinct & Foundation)"
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
        "name": "OOTK - First Operation (15-Card Active Heap)",
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
        "positions": [f"Decan {i}" for i in range(1, 37)]
    },
    "12": {
        "name": "Complete Opening of the Key (OOTK) - 4-Operation Master Pipeline",
        "operations": ["8", "9", "10", "11"]
    }
}

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
    "6": [(0.0, 1.0), (0.866, 0.5), (0.866, -0.5), (0.0, -1.0), (-0.866, -0.5), (-0.866, 0.5), (0.0, 0.0)],
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
RING_ASPECTS = (
    ("Opposition", "Opposition (180°)", 180.0, "Polar Complement / Axis Tension", -1),
    ("Square",     "Square (90°)",      90.0,  "Dynamic Tension / Quadrature Friction", -2),
    ("Trine",      "Trine (120°)",      120.0, "Equilateral Flow / Resonance", 2),
    ("Sextile",    "Sextile (60°)",     60.0,  "Harmonic Alignment / Opportunity", 1),
)
RING_ASPECT_ORB = 1.0  # degrees; ring layouts sit on exact multiples of 10 or 30 degrees
_ALL_RING_ASPECTS = ("Opposition", "Square", "Trine", "Sextile")
RING_LAYOUT_ASPECTS = {
    "9": _ALL_RING_ASPECTS,    # 12 houses
    "10": _ALL_RING_ASPECTS,   # 12 zodiac signs
    "11": _ALL_RING_ASPECTS,   # 36 decans
}

def parse_args():
    parser = argparse.ArgumentParser(description="Thoth Tarot & Liber 777 Calculation Engine")
    parser.add_argument("--topic", type=str, help="Query or topic intent string", default=None)
    parser.add_argument("--seed", type=str, help="PRNG numeric seed for deterministic draws", default=None)
    parser.add_argument("--significator", type=str, help="Significator card title", default="Knight of Swords")
    parser.add_argument("--spread", type=str, help="Spread key (1-12)", default=None)
    parser.add_argument("--framework", type=str, choices=["auto", "light_descent", "soul_formation", "life_path", "post_mortem"], default="auto", help="Override Macro Conceptual Framework")
    parser.add_argument("--mapping", type=str, choices=["golden_dawn", "french_egyptian"], default="golden_dawn", help="Tarot-Kabbalah Mapping Scheme")
    parser.add_argument("--html", action="store_true", help="Auto-generate HTML report in output/")
    return parser.parse_args()

def get_db_connection():
    try:
        conn = psycopg.connect(**DB_CONFIG, row_factory=dict_row)
        return conn
    except Exception as e:
        print(f"[ERROR] Database connection failed: {e}")
        sys.exit(1)

def fetch_all_cards(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT card_id, title, arcana_type, key_scale FROM thoth_cards ORDER BY card_id ASC;")
        return cur.fetchall()

def fetch_card_correspondences(conn, title, system="golden_dawn"):
    """Looks up one card's correspondences.

    GD data (spatial, platonic, colours, GD letter) joins on the card's key_scale.
    French/Egyptian data joins separately (alias cf) because the French table is indexed
    by French card number (0-21 for Majors), not by the Golden Dawn path number. Majors use
    thoth_cards.french_number; Minors share their number with key_scale (1-10); Courts have
    no French row and fall back to GD values.
    """
    query = """
    SELECT
        tc.card_id,
        tc.title,
        tc.arcana_type,
        tc.suit,
        tc.number_or_rank,
        tc.description,
        tc.key_scale,
        CASE WHEN %(sys)s = 'french_egyptian' AND cf.path_or_sephira_french IS NOT NULL
             THEN cf.path_or_sephira_french ELSE c.name END AS path_or_sephira,
        CASE WHEN %(sys)s = 'french_egyptian' AND cf.hebrew_letter_french IS NOT NULL
             THEN cf.hebrew_letter_french ELSE COALESCE(c.hebrew_letter, 'N/A') END AS hebrew_letter,
        c.hebrew_letter AS gd_hebrew_letter,
        cf.hebrew_letter_french AS french_hebrew_letter,
        CASE WHEN %(sys)s = 'french_egyptian' AND cf.attribution_french IS NOT NULL
             THEN cf.attribution_french ELSE c.element_or_planet_or_sign END AS attribution,
        c.element_or_planet_or_sign AS element,
        c.king_scale_color,
        c.attributions,
        c.spatial_type,
        c.spatial_dimension,
        c.platonic_solid,
        c.solid_faces,
        c.solid_vertices,
        c.dual_solid,
        c.topological_role
    FROM thoth_cards tc
    LEFT JOIN correspondences c  ON c.key_scale = tc.key_scale
    LEFT JOIN correspondences cf ON cf.key_scale = CASE
            WHEN tc.arcana_type = 'Major' THEN tc.french_number
            WHEN tc.arcana_type = 'Minor' THEN tc.key_scale
        END
    WHERE tc.title = %(title)s;
    """
    with conn.cursor() as cur:
        cur.execute(query, {"sys": system, "title": title})
        return cur.fetchone()

ELEMENT_WORDS = {"fire": "Fire", "water": "Water", "air": "Air", "earth": "Earth"}
SUIT_ELEMENTS = {"wands": "Fire", "cups": "Water", "swords": "Air", "disks": "Earth", "pentacles": "Earth"}
ZODIAC_ELEMENTS = {
    "aries": "Fire", "leo": "Fire", "sagittarius": "Fire",
    "taurus": "Earth", "virgo": "Earth", "capricorn": "Earth",
    "gemini": "Air", "libra": "Air", "aquarius": "Air",
    "cancer": "Water", "scorpio": "Water", "pisces": "Water",
}
# Planet-only attributions, used as a fallback when parsing attribution text.
PLANET_ELEMENTS = {
    "sun": "Fire", "mars": "Fire", "jupiter": "Fire",
    "moon": "Water", "venus": "Earth", "mercury": "Air", "saturn": "Earth",
}

# Explicit Thoth elemental assignment for the Majors. Independent of the active mapping
# system, so French/Egyptian attribution strings (glyph-only, "...", planet lists) can no
# longer distort element counts or dignity scores.
MAJOR_ELEMENTS = {
    "The Fool": "Air", "The Magus": "Air", "The Priestess": "Water",
    "The Empress": "Earth", "The Emperor": "Fire", "The Hierophant": "Earth",
    "The Lovers": "Air", "The Chariot": "Water", "Adjustment": "Air",
    "The Hermit": "Earth", "Fortune": "Fire", "Lust": "Fire",
    "The Hanged Man": "Water", "Death": "Water", "Art": "Fire",
    "The Devil": "Earth", "The Tower": "Fire", "The Star": "Air",
    "The Moon": "Water", "The Sun": "Fire", "The Aeon": "Fire",
    "The Universe": "Earth",
}

def derive_primary_element(card_data):
    """Suit wins; otherwise the first element, zodiac sign or planet word found in the
    attribution, then the title. Whole-word matching, so 'chair' never reads as 'air'."""
    if not card_data:
        return "Spirit"
    suit = str(card_data.get("suit") or "").lower()
    for word, elem in SUIT_ELEMENTS.items():
        if word.rstrip("s") in suit:
            return elem

    if card_data.get("arcana_type") == "Major":
        name = str(card_data.get("title") or "").split(" - ", 1)[-1].strip()
        if name in MAJOR_ELEMENTS:
            return MAJOR_ELEMENTS[name]

    lookup = {**ELEMENT_WORDS, **ZODIAC_ELEMENTS, **PLANET_ELEMENTS}
    for field in ("attribution", "title"):
        for token in re.findall(r"[a-z]+", str(card_data.get(field) or "").lower()):
            if token in lookup:
                return lookup[token]
    return "Spirit"

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

def calculate_elemental_dignities(spread_results, spread_key=None):
    """Pairwise dignity between consecutive cards, never across an operation boundary."""
    dignity_matrix = []
    if len(spread_results) < 2:
        return dignity_matrix

    for _layout, seg_start, seg_end, seg_name in spread_segments(spread_results, spread_key):
        for i in range(seg_start, seg_end - 1):
            c1 = spread_results[i]
            c2 = spread_results[i + 1]

            elem1 = derive_primary_element(c1["card_data"])
            elem2 = derive_primary_element(c2["card_data"])

            if elem1 == "Spirit" or elem2 == "Spirit":
                score = 0
                rel = "Neutral / Spiritual Synthesis"
            elif elem1 == elem2:
                score = 1
                rel = f"Direct Reinforcement ({elem1} + {elem2})"
            elif (elem1 == "Fire" and elem2 == "Air") or (elem1 == "Air" and elem2 == "Fire"):
                score = 2
                rel = "Active Attraction / Combustion (Fire + Air)"
            elif (elem1 == "Water" and elem2 == "Earth") or (elem1 == "Earth" and elem2 == "Water"):
                score = 2
                rel = "Active Nourishment / Receptivity (Water + Earth)"
            elif (elem1 == "Fire" and elem2 == "Water") or (elem1 == "Water" and elem2 == "Fire"):
                score = -2
                rel = "Active Hostility / Extinction (Fire + Water)"
            elif (elem1 == "Air" and elem2 == "Earth") or (elem1 == "Earth" and elem2 == "Air"):
                score = -2
                rel = "Active Hostility / Resistance (Air + Earth)"
            else:
                score = 0
                rel = f"Passive / Neutral ({elem1} + {elem2})"

            dignity_matrix.append({
                "pair": f"Pos {c1['position_number']} ({c1['card_data']['title']}) <-> Pos {c2['position_number']} ({c2['card_data']['title']})",
                "score": score,
                "relationship": rel,
                "from_index": i,
                "to_index": i + 1,
                "segment_name": seg_name,
            })

    return dignity_matrix

def analyze_elemental_balance(spread_results):
    element_counts = {"Fire": 0, "Water": 0, "Air": 0, "Earth": 0, "Spirit": 0}
    for item in spread_results:
        elem = derive_primary_element(item["card_data"])
        element_counts[elem] += 1
    return element_counts

def calculate_spatial_aspect(angle_deg):
    norm_angle = abs(angle_deg) % 360
    if norm_angle > 180:
        norm_angle = 360 - norm_angle

    if norm_angle <= 15:
        return "Conjunction (0°)", "Direct Focus / Synthesis", 2
    elif 50 <= norm_angle <= 70:
        return "Sextile (60°)", "Harmonic Alignment / Opportunity", 1
    elif 80 <= norm_angle <= 100:
        return "Square (90°)", "Dynamic Tension / Quadrature Friction", -2
    elif 110 <= norm_angle <= 130:
        return "Trine (120°)", "Equilateral Flow / Resonance", 2
    elif 165 <= norm_angle <= 180:
        return "Opposition (180°)", "Polar Complement / Axis Tension", -1
    else:
        return f"Inconjunct/Minor ({norm_angle:.1f}°)", "Asymmetric Vector Transition", 0

def _ring_aspect(delta_deg, allowed):
    """Exact-aspect lookup for ring layouts. Returns (short, name, desc, modifier) or None."""
    norm = abs(delta_deg) % 360
    if norm > 180:
        norm = 360 - norm
    for short, name, angle, desc, modifier in RING_ASPECTS:
        if short in allowed and abs(norm - angle) <= RING_ASPECT_ORB:
            return short, name, desc, modifier
    return None

def analyze_spatial_vectors(spread_results, spread_key):
    """Spatial relations per layout segment, measured around each layout's centroid.

    Master pipelines are analysed one operation at a time against that operation's own layout,
    so no pair spans two operations. Ring layouts (see RING_LAYOUT_ASPECTS) are paired by
    exact aspect between any two positions; all other layouts pair consecutive positions.
    Segments without a defined layout are skipped (no fake geometry). A position sitting on
    the centroid has no direction, so consecutive pairs involving it are reported as a
    centre/axis node.
    """
    if len(spread_results) < 2:
        return []

    spatial_matrix = []
    for layout_key, seg_start, seg_end, seg_name in spread_segments(spread_results, spread_key):
        seg_len = seg_end - seg_start
        coords = SPREAD_DEFAULT_COORDINATES.get(layout_key)
        if seg_len < 2 or not coords or len(coords) < seg_len:
            continue
        coords = coords[:seg_len]

        cx = sum(x for x, _ in coords) / len(coords)
        cy = sum(y for _, y in coords) / len(coords)

        def polar(point):
            dx, dy = point[0] - cx, point[1] - cy
            if math.hypot(dx, dy) < 1e-9:
                return None
            return math.degrees(math.atan2(dy, dx)) % 360

        def pair_label(item1, item2):
            return (f"Pos {item1['position_number']} ({item1['card_data']['title']}) "
                    f"<-> Pos {item2['position_number']} ({item2['card_data']['title']})")

        allowed = RING_LAYOUT_ASPECTS.get(layout_key)
        if allowed is not None:
            found = []
            for a in range(seg_len):
                for b in range(a + 1, seg_len):
                    ang_a, ang_b = polar(coords[a]), polar(coords[b])
                    if ang_a is None or ang_b is None:
                        continue
                    delta = abs(ang_a - ang_b)
                    hit = _ring_aspect(delta, allowed)
                    if not hit:
                        continue
                    short, name, desc, modifier = hit
                    (xa, ya), (xb, yb) = coords[a], coords[b]
                    found.append((
                        [r[0] for r in RING_ASPECTS].index(short), a, b,
                        {
                            "pair": pair_label(spread_results[seg_start + a], spread_results[seg_start + b]),
                            "distance": round(math.hypot(xb - xa, yb - ya), 3),
                            "delta_angle": round(min(delta % 360, 360 - delta % 360), 1),
                            "aspect": name,
                            "description": desc,
                            "score_modifier": modifier,
                            "segment_name": seg_name,
                            "pair_mode": "aspect",
                        },
                    ))
            found.sort(key=lambda t: (t[0], t[1], t[2]))
            spatial_matrix.extend(t[3] for t in found)
            continue

        for j in range(seg_len - 1):
            item1, item2 = spread_results[seg_start + j], spread_results[seg_start + j + 1]
            (x1, y1), (x2, y2) = coords[j], coords[j + 1]
            dist = math.hypot(x2 - x1, y2 - y1)

            a1, a2 = polar(coords[j]), polar(coords[j + 1])
            if a1 is None or a2 is None:
                delta_angle = 0.0
                aspect_name, aspect_desc, modifier = (
                    "Centre Node", "Axis / Core Point (no angular relation)", 0)
            else:
                delta_angle = abs(a1 - a2)
                aspect_name, aspect_desc, modifier = calculate_spatial_aspect(delta_angle)

            spatial_matrix.append({
                "pair": pair_label(item1, item2),
                "distance": round(dist, 3),
                "delta_angle": round(delta_angle, 1),
                "aspect": aspect_name,
                "description": aspect_desc,
                "score_modifier": modifier,
                "segment_name": seg_name,
                "pair_mode": "consecutive",
            })

    return spatial_matrix

def analyze_hebrew_spatial_distribution(spread_results):
    distribution = {
        "Mother_Axis": 0,
        "Double_Direction": 0,
        "Simple_Edge": 0,
        "Sephira_Point": 0,
        "Unmapped": 0
    }
    spatial_details = []

    for item in spread_results:
        data = item["card_data"]
        stype = data.get("spatial_type")
        sdim = data.get("spatial_dimension")

        if stype in distribution:
            distribution[stype] += 1
        else:
            if data.get("arcana_type") == "Minor" or "Sephira" in str(data.get("path_or_sephira")):
                distribution["Sephira_Point"] += 1
                stype = "Sephira_Point"
                sdim = "Nodal Sphere (Sephira)"
            else:
                distribution["Unmapped"] += 1
                stype = "Unmapped"
                sdim = "General Form"

        spatial_details.append({
            "position": item["position_number"],
            "title": data["title"],
            "letter": data.get("hebrew_letter") or "N/A",
            "spatial_type": stype,
            "spatial_dimension": sdim or "Standard Continuum"
        })

    return distribution, spatial_details

def analyze_platonic_topology(spread_results):
    solid_counts = {
        "Dodecahedron": 0,
        "Tetrahedron": 0,
        "Icosahedron": 0,
        "Octahedron": 0,
        "Hexahedron (Cube)": 0,
        "Unmapped": 0
    }
    topology_details = []

    for item in spread_results:
        data = item["card_data"]
        solid = data.get("platonic_solid") or "Unmapped"
        role = data.get("topological_role") or "Standard Node"
        dual = data.get("dual_solid") or "N/A"

        if solid in solid_counts:
            solid_counts[solid] += 1
        else:
            solid_counts["Unmapped"] += 1

        topology_details.append({
            "position": item["position_number"],
            "title": data["title"],
            "solid": solid,
            "faces": data.get("solid_faces") or "N/A",
            "vertices": data.get("solid_vertices") or "N/A",
            "dual_solid": dual,
            "role": role
        })

    dual_pairings = []
    for i in range(len(topology_details) - 1):
        s1 = topology_details[i]["solid"]
        s2 = topology_details[i+1]["solid"]
        p1 = topology_details[i]["position"]
        p2 = topology_details[i+1]["position"]

        if (s1 == "Hexahedron (Cube)" and s2 == "Octahedron") or (s1 == "Octahedron" and s2 == "Hexahedron (Cube)"):
            dual_pairings.append(f"Positions {p1} & {p2}: Earth/Air Inversion Dual (Cube <-> Octahedron)")
        elif (s1 == "Dodecahedron" and s2 == "Icosahedron") or (s1 == "Icosahedron" and s2 == "Dodecahedron"):
            dual_pairings.append(f"Positions {p1} & {p2}: Spirit/Water Inversion Dual (Dodecahedron <-> Icosahedron)")
        elif s1 == "Tetrahedron" and s2 == "Tetrahedron":
            dual_pairings.append(f"Positions {p1} & {p2}: Self-Dual Ignis Resonance (Tetrahedron <-> Tetrahedron)")

    return solid_counts, topology_details, dual_pairings

def evaluate_macro_framework(spread_results, forced_framework="auto"):
    if forced_framework != "auto":
        framework_names = {
            "light_descent": "1. Divine Light Flow (Aleph -> Tav Pathway)",
            "soul_formation": "2. Soul Formation & Pre-Incarnation Shaping",
            "life_path": "3. Incarnational Life Path & Psychological Evolution",
            "post_mortem": "4. Post-Mortem Return & Reversal of Paths (Book of the Dead)"
        }
        return framework_names.get(forced_framework, "1. Divine Light Flow")

    if not spread_results:
        return "3. Incarnational Life Path & Psychological Evolution"

    has_majors = any(item["card_data"].get("arcana_type") == "Major" for item in spread_results if item.get("card_data"))
    sephiroth_ranks = []
    sephiroth_map = {
        "kether": 1, "chokmah": 2, "binah": 3, "chesed": 4, "geburah": 5,
        "tiphareth": 6, "netzach": 7, "hod": 8, "yesod": 9, "malkuth": 10
    }

    for item in spread_results:
        if not item.get("card_data"):
            continue
        path = str(item["card_data"].get("path_or_sephira") or "").lower()
        for seph, rank in sephiroth_map.items():
            if seph in path:
                sephiroth_ranks.append(rank)

    if sephiroth_ranks:
        if sephiroth_ranks[0] < sephiroth_ranks[-1]:
            return "1. Divine Light Flow (Involutionary Descent: Kether -> Malkuth)"
        elif sephiroth_ranks[0] > sephiroth_ranks[-1]:
            return "4. Post-Mortem Return & Reversal of Paths (Ascension / Book of the Dead)"
        elif any(r <= 3 for r in sephiroth_ranks) and any(r >= 7 for r in sephiroth_ranks):
            return "2. Soul Formation & Pre-Incarnation Stage (Descent Through Sephiroth)"

    if has_majors:
        return "3. Incarnational Life Path & Psychological Evolution (Arcana Progression)"

    return "3. Incarnational Life Path & Psychological Evolution"

def build_analytical_prompt(spread_name, query_prompt, significator, seed_val, spread_results, element_counts, dignity_matrix, spatial_matrix, spatial_dist, spatial_details, solid_counts, topology_details, dual_pairings, macro_framework="3. Incarnational Life Path", mapping_system="golden_dawn"):
    total_cards = sum(element_counts.values()) or 1
    mapping_labels = {
        "golden_dawn": "Golden Dawn / English System (Liber 777)",
        "french_egyptian": "French / Egyptian System (Lévi / Papus / Wirth)",
    }
    mapping_label = mapping_labels.get(mapping_system, mapping_system)

    prompt_md = f"""# HERMETIC ANALYTICAL REPORT & SYSTEM PROMPT
**Operation/Spread:** {spread_name}
**Query/Intent Topic:** {query_prompt or 'General Operation'}
**Significator:** {significator}
**PRNG Seed:** {seed_val or 'Manual Entry'}
**Macro Cabbalistic Framework:** {macro_framework}
**Active Mapping System:** {mapping_label}

---

## 1. ELEMENTAL VECTOR DISTRIBUTION
"""
    for elem, count in element_counts.items():
        pct = (count / total_cards) * 100
        bar = "█" * int(count * 2)
        prompt_md += f"* **{elem:6s}**: {bar} {count} ({pct:.1f}%)\n"

    prompt_md += "\n---\n\n## 2. HEBREW LETTER SPATIAL DIMENSIONS (Sefer Yetzirah / Stanislavivsky)\n"
    prompt_md += f"* **3 Mother Axes (Core Planes)**: `{spatial_dist['Mother_Axis']}`\n"
    prompt_md += f"* **7 Double Directions (Cardinal Faces)**: `{spatial_dist['Double_Direction']}`\n"
    prompt_md += f"* **12 Simple Edges (Polyhedral Boundaries)**: `{spatial_dist['Simple_Edge']}`\n"
    prompt_md += f"* **Nodal Sephiroth Spheres**: `{spatial_dist['Sephira_Point']}`\n\n"
    prompt_md += "**Card Spatial Vectors:**\n"
    for sd in spatial_details:
        prompt_md += f"- Pos {sd['position']} ({sd['title']}): Letter `{sd['letter']}` -> **{sd['spatial_type']}** [{sd['spatial_dimension']}]\n"

    prompt_md += "\n---\n\n## 3. PLATONIC SOLID TOPOLOGY MATRIX\n"
    for solid, count in solid_counts.items():
        prompt_md += f"* **{solid:20s}**: `{count}`\n"

    if dual_pairings:
        prompt_md += "\n**Topological Dual Pairings / Polyhedral Inversions:**\n"
        for dp in dual_pairings:
            prompt_md += f"* {dp}\n"

    prompt_md += "\n---\n\n## 4. PAIRWISE ELEMENTAL DIGNITY INTERACTIONS\n"
    last_segment = None
    for d in dignity_matrix:
        if d.get("segment_name") and d["segment_name"] != last_segment:
            prompt_md += f"\n**{d['segment_name']}**\n\n"
            last_segment = d["segment_name"]
        score_str = f"+{d['score']}" if d['score'] > 0 else str(d['score'])
        prompt_md += f"* **{d['pair']}**: `Score: {score_str}` | {d['relationship']}\n"

    prompt_md += "\n---\n\n## 5. SPATIAL & GEOMETRIC VECTOR ANALYSIS\n"
    if spatial_matrix:
        last_segment = None
        last_aspect = None
        first_in_segment = False
        for s in spatial_matrix:
            if s.get("segment_name") and s["segment_name"] != last_segment:
                prompt_md += f"\n**{s['segment_name']}**\n"
                last_segment = s["segment_name"]
                last_aspect = None
                first_in_segment = True
            else:
                first_in_segment = False
            mod_str = f"+{s['score_modifier']}" if s['score_modifier'] > 0 else str(s['score_modifier'])
            if s.get("pair_mode") == "aspect":
                # Ring layouts: pairs are grouped under their aspect, one line per pair.
                if s["aspect"] != last_aspect:
                    prompt_md += f"\n_{s['aspect']} - {s['description']} [Modifier: `{mod_str}`]_\n\n"
                    last_aspect = s["aspect"]
                prompt_md += f"* {s['pair']}\n"
            else:
                prompt_md += ("\n" if first_in_segment else "") + f"* **{s['pair']}**:\n"
                prompt_md += f"  - Spatial Distance: `{s['distance']}` units | Angular Delta: `{s['delta_angle']}°`\n"
                prompt_md += f"  - Geometric Aspect: **{s['aspect']}** ({s['description']}) [Modifier: `{mod_str}`]\n"
    else:
        prompt_md += "* No spatial layout is defined for this spread (or only one card was drawn), so no geometric relations were evaluated.\n"

    prompt_md += "\n---\n\n## 6. CARD-BY-CARD CORRESPONDENCE MATRIX\n\n"

    for item in spread_results:
        data = item["card_data"]
        letter_val = data.get('hebrew_letter')
        letter_str = f" ({letter_val})" if letter_val and letter_val != 'N/A' else ""
        
        gd_letter = data.get('gd_hebrew_letter') or 'N/A'
        french_letter = data.get('french_hebrew_letter') or 'N/A'

        prompt_md += f"### Position {item['position_number']}: {item['position_name']}\n"
        prompt_md += f"- **Card Drawn**: {data['title']}\n"
        prompt_md += f"- **Arcana/Suit**: {data['arcana_type']} | {data['suit'] or 'N/A'}\n"
        prompt_md += f"- **Path/Sephira**: {data['path_or_sephira']}{letter_str}\n"
        prompt_md += f"- **Attribution**: {data['attribution']}\n"
        prompt_md += f"- **Comparative Hebrew Mapping**: GD: `{gd_letter}` | French/Egyptian: `{french_letter}`\n"
        prompt_md += f"- **Spatial Dimension**: `{data.get('spatial_type', 'N/A')}` ({data.get('spatial_dimension', 'N/A')})\n"
        prompt_md += f"- **Platonic Topology**: `{data.get('platonic_solid', 'N/A')}` (Faces: {data.get('solid_faces', 'N/A')}, Vertices: {data.get('solid_vertices', 'N/A')}) | Dual: `{data.get('dual_solid', 'N/A')}`\n"
        prompt_md += f"- **Topological Role**: {data.get('topological_role', 'N/A')}\n"
        prompt_md += f"- **King Scale Color**: {data['king_scale_color']}\n\n"

    prompt_md += f"""---

## 7. SYNTHESIS & INTERPRETATION INSTRUCTIONS FOR LLM

Act as an expert Hermetic scholar and Tarot authority. Synthesize the above spread matrix following these dynamic rules:

1. **Active System Context ({mapping_label}):** Analyze how the cards function under the `{mapping_system}` mapping.
2. **Hebrew Letter Spatial Geometry & Platonic Topology:** Consider the balance between Mother Axes, Double Directions, Simple Edges, and the active Platonic Solid geometries (Tetrahedron, Cube, Octahedron, Icosahedron, Dodecahedron).
3. **Macro Conceptual Framework Context:** Interpret this spread through the Lens of **{macro_framework}**.
4. **Elemental Dignity & Spatial Geometry Analysis:** Utilize the Pairwise Dignity interactions, Spatial Vector Aspects, and Polyhedral Dual Inversions calculated above.
5. **Actionable Executive Resolution:** Conclude with a direct summary of the key forces and final dynamic outcome.
"""
    return prompt_md

def card_is_dignified(index, dignity_matrix):
    """A card is dignified when the pairwise scores touching it sum to >= 0.

    Pairs carry explicit card indices, so a card at the edge of an operation is judged only by
    its in-operation neighbour. A card with no pairs counts as dignified.
    """
    touching = [
        d["score"] for d in (dignity_matrix or [])
        if index in (d["from_index"], d["to_index"])
    ]
    return sum(touching) >= 0 if touching else True

def save_spread_session(conn, spread_name, query_prompt, notes, significator, spread_results, dignity_matrix=None):
    insert_session_query = """
    INSERT INTO tarot_sessions (operation_type, significator, notes)
    VALUES (%s, %s, %s)
    RETURNING session_id;
    """
    insert_spread_query = """
    INSERT INTO spread_pulls (session_id, spread_name, pull_order)
    VALUES (%s, %s, %s)
    RETURNING spread_id;
    """
    insert_pull_query = """
    INSERT INTO session_card_pulls (session_id, spread_id, card_id, position_index, is_dignified, notes)
    VALUES (%s, %s, %s, %s, %s, %s);
    """
    
    full_notes = f"Prompt: {query_prompt} | Notes: {notes}" if query_prompt and notes else (query_prompt or notes)
    
    try:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(insert_session_query, ('OOTK', significator, full_notes))
                session_id = cur.fetchone()["session_id"]
                
                cur.execute(insert_spread_query, (session_id, spread_name, 1))
                spread_id = cur.fetchone()["spread_id"]
                
                for idx, item in enumerate(spread_results):
                    card_data = item["card_data"]
                    cur.execute(insert_pull_query, (
                        session_id,
                        spread_id,
                        card_data["card_id"],
                        item["position_number"],
                        card_is_dignified(idx, dignity_matrix),
                        item["position_name"]
                    ))
                    
        print(f"\n[SUCCESS] Session #{session_id} (Spread #{spread_id}) and {len(spread_results)} card pulls recorded to my_tarot_db.")
        return session_id
    except Exception as e:
        print(f"\n[ERROR] Failed to record session to database: {e}")
        return None

def generate_html_output(session_id, spread_name, query_prompt, analytical_prompt):
    output_dir = BASE_DIR / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = output_dir / f"ootk_output_{session_id or 'latest'}.html"
    
    html_analysis = html.escape(analytical_prompt, quote=False)
    safe_spread_name = html.escape(spread_name)
    safe_query = html.escape(query_prompt) if query_prompt else "N/A"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Spread Report - {safe_spread_name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace; background: #121212; color: #e0e0e0; padding: 30px; line-height: 1.6; }}
        h1, h2, h3 {{ color: #bb86fc; }}
        .meta {{ background: #1f1f1f; padding: 20px; border-radius: 8px; border-left: 4px solid #03dac6; margin-bottom: 25px; }}
        pre {{ background: #1e1e1e; color: #a9b7c6; padding: 20px; border-radius: 8px; overflow-x: auto; white-space: pre-wrap; font-family: "Fira Code", monospace; }}
    </style>
</head>
<body>
    <h1>OOTK Thoth Engine - Analytical Synthesis Report</h1>
    <div class="meta">
        <p><strong>Spread Operation:</strong> {safe_spread_name}</p>
        <p><strong>Query / Topic:</strong> {safe_query}</p>
        <p><strong>Database Session ID:</strong> #{session_id or 'N/A'}</p>
    </div>
    <h2>Generated Operational Prompt & Matrix</h2>
    <pre>{html_analysis}</pre>
</body>
</html>
"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[HTML EXPORT] Report generated at: {filename}")

def display_card_selection(cards):
    print("\n--- AVAILABLE THOTH CARDS ---")
    for idx, card in enumerate(cards, start=1):
        print(f"{idx:2d}. {card['title']} (Card ID {card['card_id']})")

def resolve_significator(cards, name):
    """Finds the significator card by full title or by name after the 'XI - ' style prefix."""
    wanted = (name or "").strip().lower()
    if not wanted:
        return None
    for c in cards:
        t = c["title"].lower()
        if t == wanted or t.split(" - ", 1)[-1] == wanted:
            return c
    return None

def run_spread_session():
    args = parse_args()

    with get_db_connection() as conn:
        cards = fetch_all_cards(conn)
        card_lookup = {str(idx): card["title"] for idx, card in enumerate(cards, start=1)}
        card_titles_set = {card["title"].lower(): card["title"] for card in cards}

        shuffled_deck = shuffle_deck(cards, args.seed) if args.seed else None
        auto_draw_index = 0

        print("==================================================")
        print("       THOTH TAROT & LIBER 777 ENGINE           ")
        print("==================================================")

        if args.spread and args.spread in SPREADS:
            spread_choice = args.spread
        else:
            print("Select a spread layout:\n")
            print("--- CORE & PROGRESSIVE SPREADS ---")
            for key in ["1", "2", "3", "4", "5"]:
                print(f" [{key:2s}] {SPREADS[key]['name']} ({len(SPREADS[key]['positions'])} cards)")
                
            print("\n--- HERMETIC & MACROCOSMIC LAYOUTS ---")
            for key in ["6", "7"]:
                print(f" [{key:2s}] {SPREADS[key]['name']} ({len(SPREADS[key]['positions'])} cards)")

            print("\n--- OPENING OF THE KEY (OOTK) OPERATIONS ---")
            for key in ["8", "9", "10", "11"]:
                print(f" [{key:2s}] {SPREADS[key]['name']} ({len(SPREADS[key]['positions'])} cards)")

            print("\n--- MASTER PIPELINE ---")
            print(f" [12] {SPREADS['12']['name']} (75 cards total)")

            spread_choice = input("\nEnter spread number (1-12): ").strip()
            while spread_choice not in SPREADS:
                spread_choice = input("Invalid spread. Enter a number from 1 to 12: ").strip()

        selected_spread = SPREADS[spread_choice]
        print(f"\n---> Selected Spread: {selected_spread['name']}\n")

        query_prompt = args.topic if args.topic else (input("Enter Query / Intent Prompt (optional, press ENTER to skip): ").strip() or None)
        session_notes = f"PRNG Seed: {args.seed}" if args.seed else (input("Enter Session Notes (optional, press ENTER to skip): ").strip() or None)
        significator = args.significator

        spread_results = []

        target_positions = []
        if "operations" in selected_spread:
            for op_num, op_key in enumerate(selected_spread["operations"], start=1):
                op_spread = SPREADS[op_key]
                for p in op_spread["positions"]:
                    target_positions.append(f"[Op {op_num}] {p}")
        else:
            target_positions = selected_spread.get("positions", [])

        sig_card = resolve_significator(cards, significator)
        if significator and sig_card is None:
            print(f"[ERROR] Significator '{significator}' not found in thoth_cards.")
            sys.exit(1)

        # Only pin when the spread actually has a significator position (first position).
        pin_significator = bool(
            sig_card and target_positions and "significator" in target_positions[0].lower()
        )
        if pin_significator and shuffled_deck:
            # Remove it from the shuffled deck so it cannot be drawn a second time;
            # remaining order is unchanged, so a given seed stays deterministic.
            shuffled_deck = [c for c in shuffled_deck if c["card_id"] != sig_card["card_id"]]
        significator_label = (
            sig_card["title"] if pin_significator
            else "None (spread has no significator position)"
        )

        for pos_idx, position_name in enumerate(target_positions, start=1):
            print(f"\n[Position {pos_idx}: {position_name}]")
            
            if pin_significator and pos_idx == 1:
                selected_title = sig_card["title"]
                print(f"--> Significator (pinned): {selected_title}")
            elif shuffled_deck:
                selected_title = shuffled_deck[auto_draw_index % len(shuffled_deck)]["title"]
                auto_draw_index += 1
                print(f"--> PRNG Auto-Drawn: {selected_title}")
            else:
                selected_title = None
                while not selected_title:
                    user_input = input("Enter card index number (or type full name): ").strip()
                    if user_input in card_lookup:
                        selected_title = card_lookup[user_input]
                    elif user_input.lower() in card_titles_set:
                        selected_title = card_titles_set[user_input.lower()]
                    else:
                        print("Invalid card selection. Type 'list' or try again.")
                        if user_input.lower() == 'list':
                            display_card_selection(cards)

            card_data = fetch_card_correspondences(conn, selected_title, system=args.mapping)
            spread_results.append({
                "position_number": pos_idx,
                "position_name": position_name,
                "card_data": card_data
            })

        element_counts = analyze_elemental_balance(spread_results)
        dignity_matrix = calculate_elemental_dignities(spread_results, spread_choice)
        spatial_matrix = analyze_spatial_vectors(spread_results, spread_choice)
        spatial_dist, spatial_details = analyze_hebrew_spatial_distribution(spread_results)
        solid_counts, topology_details, dual_pairings = analyze_platonic_topology(spread_results)
        macro_framework = evaluate_macro_framework(spread_results, forced_framework=args.framework)

        analytical_prompt = build_analytical_prompt(
            selected_spread["name"], query_prompt, significator_label, args.seed,
            spread_results, element_counts, dignity_matrix, spatial_matrix, 
            spatial_dist, spatial_details, solid_counts, topology_details, dual_pairings,
            macro_framework, mapping_system=args.mapping
        )

        print("\n" + analytical_prompt)

        session_id = save_spread_session(conn, selected_spread["name"], query_prompt, session_notes, significator_label, spread_results, dignity_matrix)

        if args.html:
            generate_html_output(session_id, selected_spread["name"], query_prompt, analytical_prompt)

if __name__ == "__main__":
    run_spread_session()

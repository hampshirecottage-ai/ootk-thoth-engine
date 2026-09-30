import os
import sys
import json
import math
import argparse
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "config.json"

def load_db_config():
    """Loads database credentials from config/config.json with environment variable overrides."""
    config = {
        "dbname": os.getenv("DB_NAME", "my_tarot_db"),
        "user": os.getenv("DB_USER", "dbuser"),
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
                    if key in db_json and not os.getenv(f"DB_{key.upper()}"):
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
    ]
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
    query = """
    SELECT 
        tc.card_id,
        tc.title,
        tc.arcana_type,
        tc.suit,
        tc.number_or_rank,
        tc.description,
        tc.key_scale,
        CASE WHEN %s = 'french_egyptian' AND c.path_or_sephira_french IS NOT NULL THEN c.path_or_sephira_french ELSE c.name END AS path_or_sephira,
        CASE WHEN %s = 'french_egyptian' AND c.hebrew_letter_french IS NOT NULL THEN c.hebrew_letter_french ELSE COALESCE(c.hebrew_letter, 'N/A') END AS hebrew_letter,
        c.hebrew_letter AS gd_hebrew_letter,
        c.hebrew_letter_french AS french_hebrew_letter,
        CASE WHEN %s = 'french_egyptian' AND c.attribution_french IS NOT NULL THEN c.attribution_french ELSE c.element_or_planet_or_sign END AS attribution,
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
    LEFT JOIN correspondences c ON tc.key_scale = c.key_scale
    WHERE tc.title = %s;
    """
    with conn.cursor() as cur:
        cur.execute(query, (system, system, system, title))
        return cur.fetchone()

def prng_shuffle_deck(cards, seed_val):
    import hashlib
    seed_int = int(hashlib.sha256(str(seed_val).encode('utf-8')).hexdigest(), 16)
    deck = list(cards)
    n = len(deck)
    m = 2**32
    a = 1664525
    c = 1013904223
    state = seed_int % m

    for i in range(n - 1, 0, -1):
        state = (a * state + c) % m
        j = state % (i + 1)
        deck[i], deck[j] = deck[j], deck[i]
    
    return deck

def derive_primary_element(card_data):
    if not card_data:
        return "Spirit"
    suit = str(card_data.get("suit") or "").lower()
    attr = str(card_data.get("attribution") or "").lower()
    title = str(card_data.get("title") or "").lower()

    if "wand" in suit or "fire" in attr or "aries" in attr or "leo" in attr or "sagittarius" in attr or "fire" in title:
        return "Fire"
    elif "cup" in suit or "water" in attr or "cancer" in attr or "scorpio" in attr or "pisces" in attr or "water" in title:
        return "Water"
    elif "sword" in suit or "air" in attr or "gemini" in attr or "libra" in attr or "aquarius" in attr or "air" in title:
        return "Air"
    elif "disk" in suit or "pentacle" in suit or "earth" in attr or "taurus" in attr or "virgo" in attr or "capricorn" in attr or "earth" in title:
        return "Earth"
    return "Spirit"

def calculate_elemental_dignities(spread_results):
    dignity_matrix = []
    if len(spread_results) < 2:
        return dignity_matrix

    for i in range(len(spread_results) - 1):
        c1 = spread_results[i]
        c2 = spread_results[i+1]
        
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
            "relationship": rel
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

def analyze_spatial_vectors(spread_results, spread_key):
    spatial_matrix = []
    if len(spread_results) < 2:
        return spatial_matrix

    coords = SPREAD_DEFAULT_COORDINATES.get(spread_key)

    for i in range(len(spread_results) - 1):
        item1 = spread_results[i]
        item2 = spread_results[i + 1]

        if coords and i + 1 < len(coords):
            x1, y1 = coords[i]
            x2, y2 = coords[i + 1]
        else:
            x1, y1 = (float(i), 0.0)
            x2, y2 = (float(i + 1), 0.0)

        dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

        angle1 = math.degrees(math.atan2(y1, x1)) % 360
        angle2 = math.degrees(math.atan2(y2, x2)) % 360
        delta_angle = abs(angle1 - angle2)

        aspect_name, aspect_desc, modifier = calculate_spatial_aspect(delta_angle)

        spatial_matrix.append({
            "pair": f"Pos {item1['position_number']} ({item1['card_data']['title']}) <-> Pos {item2['position_number']} ({item2['card_data']['title']})",
            "distance": round(dist, 3),
            "delta_angle": round(delta_angle, 1),
            "aspect": aspect_name,
            "description": aspect_desc,
            "score_modifier": modifier
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
    mapping_label = "Golden Dawn / English System (Liber 777)" if mapping_system == "golden_dawn" else "French / Egyptian System (Lévi / Papus / Wirth)"

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
    for d in dignity_matrix:
        score_str = f"+{d['score']}" if d['score'] > 0 else str(d['score'])
        prompt_md += f"* **{d['pair']}**: `Score: {score_str}` | {d['relationship']}\n"

    prompt_md += "\n---\n\n## 5. SPATIAL & GEOMETRIC VECTOR ANALYSIS\n"
    if spatial_matrix:
        for s in spatial_matrix:
            mod_str = f"+{s['score_modifier']}" if s['score_modifier'] > 0 else str(s['score_modifier'])
            prompt_md += f"* **{s['pair']}**:\n"
            prompt_md += f"  - Spatial Distance: `{s['distance']}` units | Angular Delta: `{s['delta_angle']}°`\n"
            prompt_md += f"  - Geometric Aspect: **{s['aspect']}** ({s['description']}) [Modifier: `{mod_str}`]\n"
    else:
        prompt_md += "* Single-card operation or no vector relations evaluated.\n"

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

def save_spread_session(conn, spread_name, query_prompt, notes, significator, spread_results):
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
                
                for item in spread_results:
                    card_data = item["card_data"]
                    cur.execute(insert_pull_query, (
                        session_id,
                        spread_id,
                        card_data["card_id"],
                        item["position_number"],
                        True,
                        item["position_name"]
                    ))
                    
        print(f"\n[SUCCESS] Session #{session_id} (Spread #{spread_id}) and {len(spread_results)} card pulls recorded to my_tarot_db.")
        return session_id
    except Exception as e:
        print(f"\n[ERROR] Failed to record session to database: {e}")
        return None

def generate_html_output(session_id, spread_name, query_prompt, analytical_prompt):
    os.makedirs("output", exist_ok=True)
    filename = f"output/ootk_output_{session_id or 'latest'}.html"
    
    html_analysis = analytical_prompt.replace("<", "&lt;").replace(">", "&gt;")

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Spread Report - {spread_name}</title>
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
        <p><strong>Spread Operation:</strong> {spread_name}</p>
        <p><strong>Query / Topic:</strong> {query_prompt or 'N/A'}</p>
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

def run_spread_session():
    args = parse_args()

    with get_db_connection() as conn:
        cards = fetch_all_cards(conn)
        card_lookup = {str(idx): card["title"] for idx, card in enumerate(cards, start=1)}
        card_titles_set = {card["title"].lower(): card["title"] for card in cards}

        shuffled_deck = prng_shuffle_deck(cards, args.seed) if args.seed else None
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

        selected_spread = SPREADS.get(spread_choice, SPREADS["1"])
        print(f"\n---> Selected Spread: {selected_spread['name']}\n")

        query_prompt = args.topic if args.topic else (input("Enter Query / Intent Prompt (optional, press ENTER to skip): ").strip() or None)
        session_notes = f"PRNG Seed: {args.seed}" if args.seed else (input("Enter Session Notes (optional, press ENTER to skip): ").strip() or None)
        significator = args.significator

        spread_results = []

        target_positions = []
        if "operations" in selected_spread:
            for op_key in selected_spread["operations"]:
                op_spread = SPREADS[op_key]
                for p in op_spread["positions"]:
                    target_positions.append(f"[{op_spread['name'][:6]}] {p}")
        else:
            target_positions = selected_spread.get("positions", [])

        for pos_idx, position_name in enumerate(target_positions, start=1):
            print(f"\n[Position {pos_idx}: {position_name}]")
            
            if shuffled_deck:
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
        dignity_matrix = calculate_elemental_dignities(spread_results)
        spatial_matrix = analyze_spatial_vectors(spread_results, spread_choice)
        spatial_dist, spatial_details = analyze_hebrew_spatial_distribution(spread_results)
        solid_counts, topology_details, dual_pairings = analyze_platonic_topology(spread_results)
        macro_framework = evaluate_macro_framework(spread_results, forced_framework=args.framework)

        analytical_prompt = build_analytical_prompt(
            selected_spread["name"], query_prompt, significator, args.seed,
            spread_results, element_counts, dignity_matrix, spatial_matrix, 
            spatial_dist, spatial_details, solid_counts, topology_details, dual_pairings,
            macro_framework, mapping_system=args.mapping
        )

        print("\n" + analytical_prompt)

        session_id = save_spread_session(conn, selected_spread["name"], query_prompt, session_notes, significator, spread_results)

        if args.html:
            generate_html_output(session_id, selected_spread["name"], query_prompt, analytical_prompt)

if __name__ == "__main__":
    run_spread_session()

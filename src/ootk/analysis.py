"""Analysis of a drawn spread: elements, dignities, geometry, topology and macro framework."""
import math
import re

from ootk.spreads import (
    RING_ASPECT_ORB, RING_ASPECTS, RING_LAYOUT_ASPECTS, SPREAD_DEFAULT_COORDINATES, spread_segments,
)

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

# Auto-detection of the macro framework looks at where the whole draw sits on the Tree of Life,
# not just its first and last card. Tunable thresholds:
FRAMEWORK_MIN_CARDS = 6        # fewer Sephirothic cards than this -> not enough evidence
FRAMEWORK_TREND_Z = 1.64       # |r| * sqrt(n) needed to call a trend (~90% two-sided)

SEPHIROTH_RANKS = {
    "kether": 1, "chokmah": 2, "binah": 3, "chesed": 4, "geburah": 5,
    "tiphareth": 6, "netzach": 7, "hod": 8, "yesod": 9, "malkuth": 10,
}

# Golden Dawn Tree of Life: path number (key_scale 11-32) -> the two Sephiroth it joins.
GD_PATH_ENDPOINTS = {
    11: (1, 2), 12: (1, 3), 13: (1, 6), 14: (2, 3), 15: (2, 6), 16: (2, 4),
    17: (3, 6), 18: (3, 5), 19: (4, 5), 20: (4, 6), 21: (4, 7), 22: (5, 6),
    23: (5, 8), 24: (6, 7), 25: (6, 9), 26: (6, 8), 27: (7, 8), 28: (7, 9),
    29: (7, 10), 30: (8, 9), 31: (8, 10), 32: (9, 10),
}

def card_sephirothic_rank(card_data):
    """Mean Sephirothic rank of a card, or None if it has no place on the Tree.

    Named Sephiroth in the path/Sephira text win: 'Path 19 (Chesed-Tiphareth)' -> 5.0
    (whole-word matches, averaged so name order doesn't matter). That covers the French
    rows. Golden Dawn rows name a Sephira or path only in English ('Wisdom', 'Ox'), so
    Majors and Minors otherwise fall back to their key_scale: 1-10 is the Sephira itself,
    11-32 is the mean of the path's two endpoints. Courts have no Sephira or path of
    their own, so they get None.
    """
    data = card_data or {}
    text = str(data.get("path_or_sephira") or "").lower()
    ranks = [SEPHIROTH_RANKS[w] for w in re.findall(r"[a-z]+", text) if w in SEPHIROTH_RANKS]
    if ranks:
        return sum(ranks) / len(ranks)
    if data.get("arcana_type") not in ("Major", "Minor"):
        return None
    key = data.get("key_scale")
    if isinstance(key, int) and 1 <= key <= 10:
        return float(key)
    if key in GD_PATH_ENDPOINTS:
        return sum(GD_PATH_ENDPOINTS[key]) / 2
    return None

def evaluate_macro_framework(spread_results, forced_framework="auto"):
    """Returns (framework_name, basis). 'basis' says why, so the label is never opaque.

    Auto mode takes every card that names a Sephira or path, in position order, and measures
    the trend: Pearson r between position order and Sephirothic rank. Rank rising toward
    Malkuth = descent; falling toward Kether = ascent. A trend only counts when
    |r| * sqrt(n) >= FRAMEWORK_TREND_Z; for a random shuffle that happens about 10% of the
    time (5% each way). Descent -> 1 Divine Light Flow. Ascent -> 4 Post-Mortem Return.
    No significant trend -> 3 Incarnational Life Path, the default lens.

    Framework 2 (Soul Formation) is never auto-selected: it has no reliable signature in a
    draw. A mean-rank test would only measure the deck itself (a 75-card spread contains
    almost the whole deck), so use --framework soul_formation to choose it.
    """
    if forced_framework != "auto":
        framework_names = {
            "light_descent": "1. Divine Light Flow (Aleph -> Tav Pathway)",
            "soul_formation": "2. Soul Formation & Pre-Incarnation Shaping",
            "life_path": "3. Incarnational Life Path & Psychological Evolution",
            "post_mortem": "4. Post-Mortem Return & Reversal of Paths (Book of the Dead)"
        }
        return (framework_names.get(forced_framework, "1. Divine Light Flow"),
                f"forced by --framework {forced_framework}")

    life_path = "3. Incarnational Life Path & Psychological Evolution"
    if not spread_results:
        return life_path, "auto: no cards drawn"

    has_majors = any(item["card_data"].get("arcana_type") == "Major"
                     for item in spread_results if item.get("card_data"))
    default_name = life_path + (" (Arcana Progression)" if has_majors else "")

    series = []  # (position order, rank)
    for idx, item in enumerate(spread_results):
        rank = card_sephirothic_rank(item.get("card_data"))
        if rank is not None:
            series.append((idx, rank))

    n = len(series)
    if n < FRAMEWORK_MIN_CARDS:
        return default_name, (f"auto: only {n} card(s) carry Sephirothic data "
                              f"(minimum {FRAMEWORK_MIN_CARDS}); defaulted to Life Path")

    xs = [x for x, _ in series]
    ys = [y for _, y in series]
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    r = sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else 0.0
    z = r * math.sqrt(n)
    stats = f"r={r:+.2f}, z={z:+.2f} (needs |z| >= {FRAMEWORK_TREND_Z}), n={n}"

    if z >= FRAMEWORK_TREND_Z:
        return ("1. Divine Light Flow (Involutionary Descent: Kether -> Malkuth)",
                f"auto: rank rises toward Malkuth across the draw - {stats}")
    if z <= -FRAMEWORK_TREND_Z:
        return ("4. Post-Mortem Return & Reversal of Paths (Ascension / Book of the Dead)",
                f"auto: rank falls toward Kether across the draw - {stats}")
    return default_name, f"auto: no significant Sephirothic trend, default lens - {stats}"

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

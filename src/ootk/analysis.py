"""Analysis of a drawn spread: elements, dignities, geometry, topology and macro framework."""
import math
import re

from ootk.rules import aspect_label, element_dignity, find_aspect, separation
from ootk.spreads import (
    HEAP_LAYOUTS, HEAP_PAIRS, RING_ASPECTS, RING_LAYOUT_ASPECTS, SPREAD_DEFAULT_COORDINATES,
    TREE_LAYOUTS, spread_segments,
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

# Platonic solids. A card's solid follows the card's own element (the one Section 1 counts
# and the dignities score), so the two never disagree: pips and courts take their suit's
# solid, Majors their MAJOR_ELEMENTS element. The seven planetary Majors keep the
# Dodecahedron. Spatial type and cube position stay with the Hebrew letter.
PLATONIC_SOLIDS = {
    "Tetrahedron": {"solid_faces": 4, "solid_vertices": 4, "dual_solid": "Tetrahedron (Self-Dual)",
                    "topological_role": "Primary Ignis Vector (Expansion)"},
    "Icosahedron": {"solid_faces": 20, "solid_vertices": 12, "dual_solid": "Dodecahedron",
                    "topological_role": "Receptive Matrix (Fluid Volume)"},
    "Octahedron": {"solid_faces": 8, "solid_vertices": 6, "dual_solid": "Hexahedron (Cube)",
                   "topological_role": "Dynamic Axis (Mediating Air)"},
    "Hexahedron (Cube)": {"solid_faces": 6, "solid_vertices": 8, "dual_solid": "Octahedron",
                          "topological_role": "Crystallized Vessel (Physical Boundary)"},
    "Dodecahedron": {"solid_faces": 12, "solid_vertices": 20, "dual_solid": "Icosahedron",
                     "topological_role": "Planetary Celestial Face"},
}
ELEMENT_SOLIDS = {"Fire": "Tetrahedron", "Water": "Icosahedron", "Air": "Octahedron",
                  "Earth": "Hexahedron (Cube)"}
# The seven Majors on the seven double letters, one per classical planet. The Universe (Tav,
# Saturn) is one of them: it also carries Earth, but Section 2 counts its letter as a double
# letter, so its solid follows the planet too.
PLANETARY_MAJORS = {"The Magus", "The Priestess", "The Empress", "Fortune", "The Tower", "The Sun",
                    "The Universe"}

def card_solid(card_data):
    """The card's Platonic solid name (see PLATONIC_SOLIDS), or None for an unknown card."""
    data = card_data or {}
    if data.get("arcana_type") == "Major" and major_name(data) in PLANETARY_MAJORS:
        return "Dodecahedron"
    return ELEMENT_SOLIDS.get(derive_primary_element(data))

def apply_card_solid(card_data):
    """Sets the platonic fields of a fetched card row from card_solid(). Returns the row."""
    solid = card_solid(card_data)
    if solid:
        card_data["platonic_solid"] = solid
        card_data.update(PLATONIC_SOLIDS[solid])
    return card_data

def major_name(card_data):
    """'XI - Lust' -> 'Lust'."""
    return str(card_data.get("title") or "").split(" - ", 1)[-1].strip()

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
        name = major_name(card_data)
        if name in MAJOR_ELEMENTS:
            return MAJOR_ELEMENTS[name]

    lookup = {**ELEMENT_WORDS, **ZODIAC_ELEMENTS, **PLANET_ELEMENTS}
    for field in ("attribution", "title"):
        for token in re.findall(r"[a-z]+", str(card_data.get(field) or "").lower()):
            if token in lookup:
                return lookup[token]
    return "Spirit"

def _closes_ring(layout_key, seg_len):
    """True when a segment fills a whole ring layout (houses, signs, decans), so its last
    position sits next to its first."""
    coords = SPREAD_DEFAULT_COORDINATES.get(layout_key) or ()
    return layout_key in RING_LAYOUT_ASPECTS and seg_len == len(coords) and seg_len > 2

def segment_pairs(layout_key, seg_len):
    """The neighbouring positions of one segment, as 0-based (a, b) pairs within it.

    Dignities and dual pairings both use these, so the two never disagree on who neighbours
    whom. Neighbours are consecutive positions, except:
    - on a full ring (houses, signs, decans) the last position also neighbours the first
      (twelfth house <-> first house), closing the circle;
    - a heap (HEAP_PAIRS) pairs its named pairs instead of following deal order;
    - a Tree of Life layout (TREE_LAYOUTS) pairs Sephiroth joined by a path.
    """
    if layout_key in HEAP_PAIRS:
        return [(a, b) for a, b in HEAP_PAIRS[layout_key] if b < seg_len]
    if layout_key in TREE_LAYOUTS:
        return [(a - 1, b - 1) for a, b in GD_PATH_ENDPOINTS.values() if b <= seg_len]
    pairs = [(i, i + 1) for i in range(seg_len - 1)]
    if _closes_ring(layout_key, seg_len):
        pairs.append((seg_len - 1, 0))
    return pairs

def calculate_elemental_dignities(spread_results, spread_key=None):
    """Pairwise dignity between neighbouring cards (see segment_pairs), never across an
    operation boundary."""
    dignity_matrix = []
    if len(spread_results) < 2:
        return dignity_matrix

    for layout, seg_start, seg_end, seg_name in spread_segments(spread_results, spread_key):
        pairs = [(seg_start + a, seg_start + b) for a, b in segment_pairs(layout, seg_end - seg_start)]
        for i, j in pairs:
            c1 = spread_results[i]
            c2 = spread_results[j]

            elem1 = derive_primary_element(c1["card_data"])
            elem2 = derive_primary_element(c2["card_data"])

            score, rel = element_dignity(elem1, elem2)

            dignity_matrix.append({
                "pair": f"Pos {c1['position_number']} ({c1['card_data']['title']}) <-> Pos {c2['position_number']} ({c2['card_data']['title']})",
                "score": score,
                "relationship": rel,
                "from_index": i,
                "to_index": j,
                "segment_name": seg_name,
            })

    return dignity_matrix

def analyze_elemental_balance(spread_results):
    element_counts = {"Fire": 0, "Water": 0, "Air": 0, "Earth": 0, "Spirit": 0}
    for item in spread_results:
        elem = derive_primary_element(item["card_data"])
        element_counts[elem] += 1
    return element_counts

def spirit_bearing_cards(spread_results):
    """Majors that carry Spirit as a secondary quality: on Shin (Fire + Spirit) under the
    active mapping, or attributed to Spirit. Their primary element still drives dignities;
    this only stops the report from reading 'Spirit 0' as 'no Spirit in the draw'."""
    found = []
    for item in spread_results:
        data = item.get("card_data") or {}
        if data.get("arcana_type") != "Major":
            continue
        letter = str(data.get("hebrew_letter") or "")
        if "Shin" in letter or "ש" in letter or "spirit" in str(data.get("attribution") or "").lower():
            found.append((item["position_number"], data["title"]))
    return found

def calculate_spatial_aspect(angle_deg):
    """Aspect between two positions of a drawn layout, with the wide 'layout' orbs."""
    aspect = find_aspect(angle_deg, "layout")
    if aspect is None:
        return f"Minor / Unaspected ({separation(angle_deg):.1f}°)", "Asymmetric Vector Transition", 0
    return aspect_label(aspect), aspect.nature, aspect.score

def _ring_aspect(delta_deg, allowed):
    """Exact-aspect lookup for ring layouts. Returns (short, name, desc, modifier) or None."""
    aspect = find_aspect(delta_deg, "ring", allowed)
    if aspect is None:
        return None
    return aspect.name, aspect_label(aspect), aspect.nature, aspect.score

def analyze_spatial_vectors(spread_results, spread_key):
    """Spatial relations per layout segment, measured around each layout's centroid.

    Master pipelines are analysed one operation at a time against that operation's own layout,
    so no pair spans two operations. Ring layouts (see RING_LAYOUT_ASPECTS) are paired by
    exact aspect between any two positions; all other layouts pair consecutive positions.
    Heap layouts (HEAP_LAYOUTS, Op 1) link the same pairs as their dignities (HEAP_PAIRS), by
    distance only, with no aspect: their drawing coordinates are not a wheel.
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
                    # The aspect is fixed by the two positions; the cards in them are what
                    # changes between readings, so each pair also carries their dignity.
                    card_a = spread_results[seg_start + a]["card_data"]
                    card_b = spread_results[seg_start + b]["card_data"]
                    card_score, card_rel = element_dignity(derive_primary_element(card_a),
                                                           derive_primary_element(card_b))
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
                            "aspect_name": short,
                            "card_score": card_score,
                            "card_relationship": card_rel,
                            "from_index": seg_start + a,
                            "to_index": seg_start + b,
                        },
                    ))
            found.sort(key=lambda t: (t[0], t[1], t[2]))
            spatial_matrix.extend(t[3] for t in found)
            continue

        links = (segment_pairs(layout_key, seg_len) if layout_key in HEAP_LAYOUTS
                 else [(j, j + 1) for j in range(seg_len - 1)])
        for j, k in links:
            item1, item2 = spread_results[seg_start + j], spread_results[seg_start + k]
            (x1, y1), (x2, y2) = coords[j], coords[k]
            dist = math.hypot(x2 - x1, y2 - y1)

            a1, a2 = polar(coords[j]), polar(coords[k])
            if layout_key in HEAP_LAYOUTS:
                delta_angle = None
                aspect_name, aspect_desc, modifier = (
                    "Heap Pair", "Paired in the heap; a heap has no angular relation", 0)
                short = None
            elif a1 is None or a2 is None:
                delta_angle = 0.0
                aspect_name, aspect_desc, modifier = (
                    "Centre Node", "Axis / Core Point (no angular relation)", 0)
                short = None
            else:
                delta_angle = abs(a1 - a2)
                aspect_name, aspect_desc, modifier = calculate_spatial_aspect(delta_angle)
                hit = find_aspect(delta_angle, "layout")
                short = hit.name if hit else None

            spatial_matrix.append({
                "pair": pair_label(item1, item2),
                "distance": round(dist, 3),
                "delta_angle": None if delta_angle is None else round(delta_angle, 1),
                "aspect": aspect_name,
                "description": aspect_desc,
                "score_modifier": modifier,
                "segment_name": seg_name,
                "pair_mode": "consecutive",
                "aspect_name": short,           # None for unaspected and centre-node pairs
                "from_index": seg_start + j,
                "to_index": seg_start + k,
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

        letter = data.get("hebrew_letter") or "N/A"
        if data.get("arcana_type") == "Minor":
            # Minors sit on a Sephira, not a letter; hebrew_letter holds the Sephira's name.
            letter = f"none - Sephira {letter}"

        spatial_details.append({
            "position": item["position_number"],
            "title": data["title"],
            "letter": letter,
            "spatial_type": stype,
            "spatial_dimension": sdim or "Standard Continuum"
        })

    return distribution, spatial_details

# The three dual pairs: put a corner at the centre of each face of one solid and the corners
# make the other. The tetrahedron is its own dual.
DUAL_LABELS = {
    frozenset(["Hexahedron (Cube)", "Octahedron"]): "Earth/Air Inversion Dual (Cube <-> Octahedron)",
    frozenset(["Dodecahedron", "Icosahedron"]): "Planetary/Water Inversion Dual (Dodecahedron <-> Icosahedron)",
    frozenset(["Tetrahedron"]): "Self-Dual Ignis Resonance (Tetrahedron <-> Tetrahedron)",
}


def dual_pairs(spread_results, spread_key=None):
    """(i, j, label) for neighbouring cards whose solids are each other's duals.

    Neighbours are the dignities' (segment_pairs): never across an operation boundary, and on
    a full wheel the last position neighbours the first."""
    out = []
    for layout, start, end, _ in spread_segments(spread_results, spread_key):
        for a, b in segment_pairs(layout, end - start):
            i, j = start + a, start + b
            label = DUAL_LABELS.get(frozenset([spread_results[i]["card_data"].get("platonic_solid"),
                                               spread_results[j]["card_data"].get("platonic_solid")]))
            if label:
                out.append((i, j, label))
    return out


def analyze_platonic_topology(spread_results, spread_key=None):
    """Solid counts, per-card topology and dual pairings between neighbouring cards.

    Dual pairings use the same neighbours as the dignities (segment_pairs): they never cross an
    operation boundary, and on a full wheel the last position neighbours the first.
    """
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

    dual_pairings = [f"Positions {topology_details[i]['position']} & {topology_details[j]['position']}: {label}"
                     for i, j, label in dual_pairs(spread_results, spread_key)]
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
    draw. A mean-rank test would mostly measure the deck itself (a 75-card spread holds most
    of it), so use --framework soul_formation to choose it.
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
    stats = (f"r={r:+.2f}, z={z:+.2f} (needs |z| >= {FRAMEWORK_TREND_Z}), n={n} cards with a "
             f"place on the Tree (Majors and pips; courts have none)")

    if z >= FRAMEWORK_TREND_Z:
        return ("1. Divine Light Flow (Involutionary Descent: Kether -> Malkuth)",
                f"auto: rank rises toward Malkuth across the draw - {stats}")
    if z <= -FRAMEWORK_TREND_Z:
        return ("4. Post-Mortem Return & Reversal of Paths (Ascension / Book of the Dead)",
                f"auto: rank falls toward Kether across the draw - {stats}")
    return default_name, f"auto: no significant Sephirothic trend, default lens - {stats}"

# A draw that leaves out only a few cards is defined as much by those cards as by the ones
# drawn: dealing 75 of 78 forces the element counts to the deck's totals minus the three left
# out. The report lists the withheld cards when there are at most this many.
WITHHELD_MAX = 12

def withheld_summary(deck_rows, drawn_titles):
    """The deck's cards that were not drawn, or None when more than WITHHELD_MAX were left out.

    `deck_rows` are correspondence rows for the whole deck. Returns {"cards": [rows in deck
    order], "elements": withheld count per element, "deck_elements": whole-deck count per
    element}.
    """
    drawn = set(drawn_titles)
    if len(drawn) != len(drawn_titles):
        # A card fell in more than one operation (the master pipeline reshuffles for each), so
        # the counts are no longer the deck's totals minus the cards left out.
        return None
    left_out = [row for row in deck_rows if row["title"] not in drawn]
    if not left_out or len(left_out) > WITHHELD_MAX:
        return None
    def tally(rows):
        counts = {"Fire": 0, "Water": 0, "Air": 0, "Earth": 0, "Spirit": 0}
        for row in rows:
            counts[derive_primary_element(row)] += 1
        return counts
    return {"cards": left_out, "elements": tally(left_out), "deck_elements": tally(deck_rows)}

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

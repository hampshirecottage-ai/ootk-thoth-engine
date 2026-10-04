"""View model for the web report: the summary figures and drawable spread layouts.

Everything here is computed from the same analysis results the Markdown report uses, so
the pictures and the text never disagree. Drawings use the layout coordinates in
ootk.spreads (the ones the geometry is measured on); this module only scales them to pixels.
"""
import math
import re
from collections import Counter

from ootk.analysis import card_is_dignified, derive_primary_element, spirit_bearing_cards
from ootk.assets import static_url
from ootk.atlas import card_atlas
from ootk.report import withheld_sentence
from ootk.rules import ASPECTS, ASPECTS_BY_NAME, DIGNITY_CONTRARY, DIGNITY_FRIENDLY, DIGNITY_SAME, element_dignity
from ootk.spreads import RING_LAYOUT_ASPECTS, SPREAD_DEFAULT_COORDINATES, spread_segments

ELEMENTS = ("Fire", "Water", "Air", "Earth", "Spirit")
ELEMENT_COLORS = {
    "Fire": "#e4572e", "Water": "#3a86ff", "Air": "#f2c14e",
    "Earth": "#57a773", "Spirit": "#b8b8d1",
}

# Aspect types in filter order. "Unaspected" covers layout pairs that hit no aspect (and
# centre-node pairs); they are drawn faint and dashed.
UNASPECTED = "Unaspected"
ASPECT_TYPES = tuple(a.name for a in ASPECTS) + (UNASPECTED,)
ASPECT_COLORS = {
    "Conjunction": "#f5c542", "Sextile": "#4ea1ff", "Square": "#ff5c5c",
    "Trine": "#3ecf8e", "Quincunx": "#c77dff", "Opposition": "#ff9f43",
    UNASPECTED: "#8a8a8a",
}
# An aspect is "strong" when its score is at least this far from zero:
# Conjunction (+2), Trine (+2) and Square (-2).
STRONG_ASPECT_SCORE = 2

SIGNS = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
         "Sagittarius", "Capricorn", "Aquarius", "Pisces")
# U+FE0E asks for the plain text glyph rather than the emoji.
SIGN_GLYPHS = {sign: glyph + "\ufe0e" for sign, glyph in zip(SIGNS, "♈♉♊♋♌♍♎♏♐♑♒♓")}

# Pixel geometry per drawing kind. Card sizes keep neighbouring cards from overlapping.
LAYOUT_SCALE = {"8": 140}           # px per layout unit; others use DEFAULT_LAYOUT_SCALE
DEFAULT_LAYOUT_SCALE = 150
LAYOUT_CARD = {"8": (54, 84)}
DEFAULT_LAYOUT_CARD = (64, 100)
WHEEL = {
    # n positions: outer radius, label band inner radius, card radius, card size, inner radius
    12: {"r_out": 300, "r_band": 262, "r_card": 200, "card": (56, 88), "r_in": 140},
    36: {"r_out": 450, "r_band": 412, "r_card": 350, "card": (36, 56), "r_in": 305},
}
PAD = 24
HOUSE_R_OUT = 345   # Op 2's outer radius: its band also carries each house's definition

# Element-pair links (neighbouring cards), coloured by their Book T score.
DIGNITY_COLORS = {DIGNITY_SAME: "#ffe0a0", DIGNITY_FRIENDLY: "#d6f5e3", 0: "#b9c4bd", DIGNITY_CONTRARY: "#ff6b6b"}
# What one step round each ring is called, for "4 houses apart".
RING_UNITS = {"9": "house", "10": "sign", "11": "decan"}

# Op 1 is drawn inside a triangle frame (layout units). Purely decorative.
TRIANGLE_FRAME = {"8": [(0.0, 4.1), (-4.6, -2.3), (4.6, -2.3)]}


def card_slug(title):
    return str(title).lower().replace(" ", "-").replace("'", "")


def card_image_url(title, size="thumb"):
    """Versioned URL of the card's WebP image ('small' 110, 'thumb' 200 or 'full' 440 px wide),
    or None when the file is missing. scripts/optimize_images.py builds them from static/images."""
    return static_url(f"cards/{size}/{card_slug(title)}.webp")


# The art is the 1909 Rider-Waite-Smith deck (static/cards/CREDITS.md). These Thoth cards show
# a Waite card under a different name, so the page says which one rather than look mislabelled.
# Courts go by Golden Dawn rank: the Thoth Knight is the Waite King, the Prince the Waite Knight.
RWS_TRUMPS = {"VIII - Adjustment": "Justice", "XI - Lust": "Strength", "XIV - Art": "Temperance",
              "XX - The Aeon": "Judgement", "XXI - The Universe": "The World"}
RWS_COURTS = {"Knight": "King", "Prince": "Knight", "Princess": "Page"}
RWS_SUITS = {"Disks": "Pentacles"}


def rws_art_name(title):
    """The Rider-Waite-Smith card a renamed Thoth card is pictured with ('Knight of Wands' ->
    'King of Wands'), or None when the picture carries the same name (Queens, pips, most trumps)."""
    t = str(title)
    if t in RWS_TRUMPS:
        return RWS_TRUMPS[t]
    m = re.fullmatch(r"(Knight|Prince|Princess) of (\w+)", t)
    return f"{RWS_COURTS[m[1]]} of {RWS_SUITS.get(m[2], m[2])}" if m else None


def art_note(title):
    """'Pictured: Rider-Waite-Smith King of Wands', or '' when no note is needed."""
    name = rws_art_name(title)
    return f"Pictured: Rider-Waite-Smith {name}" if name else ""


def card_srcset(title):
    """srcset for a card shown about 100 px wide: 'small' on 1x screens, 'thumb' on 2x."""
    small, thumb = card_image_url(title, "small"), card_image_url(title, "thumb")
    return f"{small} 1x, {thumb} 2x" if small and thumb else ""


def short_card_name(title):
    """'XIX - The Sun' -> 'The Sun'; '2 of Wands - Dominion' -> '2 of Wands'."""
    t = str(title)
    if " - " in t:
        head, tail = t.split(" - ", 1)
        return tail if re.fullmatch(r"[0IVXL]+", head) else head
    return t


def position_note(position_name):
    """'[Op 2] 4. Fourth House (Home & Roots)' -> 'Home & Roots' ('' when there is none)."""
    m = re.search(r"\(([^()]*)\)\s*$", position_name)
    return m.group(1).strip() if m else ""


def _note_lines(note, width=16):
    """A house definition on one or two short lines, split after its first '&' or '/'."""
    if len(note) <= width:
        return [note]
    for joiner in (" / ", " & "):
        if joiner in note:
            head, tail = note.split(joiner, 1)
            return [head + joiner.rstrip(), tail]
    return [note]


def position_label(position_name):
    """'[Op 2] 5. Fifth House (Creativity & Will)' -> 'Fifth House'."""
    name = re.sub(r"^\[Op \d+\]\s*", "", position_name)
    name = re.sub(r"^\d+\.\s*", "", name)
    return name.split(" (", 1)[0].strip()


def is_strong(score):
    return abs(score or 0) >= STRONG_ASPECT_SCORE


def _signed(n):
    return f"+{n}" if n > 0 else str(n)


def _svg_point(r, deg):
    rad = math.radians(deg)
    return round(r * math.cos(rad), 2), round(-r * math.sin(rad), 2)


def _sector_path(r1, r2, a0, a1):
    """Annular sector between radii r1 < r2 and angles a0 < a1 (degrees, counter-clockwise)."""
    x0, y0 = _svg_point(r2, a0)
    x1, y1 = _svg_point(r2, a1)
    x2, y2 = _svg_point(r1, a1)
    x3, y3 = _svg_point(r1, a0)
    large = 1 if (a1 - a0) > 180 else 0
    return (f"M{x0},{y0} A{r2},{r2} 0 {large} 0 {x1},{y1} "
            f"L{x2},{y2} A{r1},{r1} 0 {large} 1 {x3},{y3} Z")


def _aspect_view(entry, start):
    name = entry.get("aspect_name") or UNASPECTED
    score = entry.get("score_modifier", 0)
    return {
        "type": name,
        "label": entry["aspect"],
        "description": entry["description"],
        "pair": entry["pair"],
        "score": score,
        "score_text": _signed(score),
        "strong": is_strong(score),
        "color": ASPECT_COLORS.get(name, ASPECT_COLORS[UNASPECTED]),
        "angle": entry.get("delta_angle"),
        "a": entry["from_index"] - start,
        "b": entry["to_index"] - start,
        # Ring aspects also carry the dignity of the two cards drawn in those positions.
        "cards_text": (f"{_signed(entry['card_score'])} {entry['card_relationship']}"
                       if "card_score" in entry else ""),
    }


def _card_view(item, index, dignity_matrix):
    data = item["card_data"]
    element = derive_primary_element(data)
    return {
        "index": index,
        "number": item["position_number"],
        "position_name": re.sub(r"^\[Op \d+\]\s*", "", item["position_name"]),
        "label": position_label(item["position_name"]),
        "title": data["title"],
        "short": short_card_name(data["title"]),
        "image": card_image_url(data["title"]),
        "srcset": card_srcset(data["title"]),
        "art": art_note(data["title"]),
        "element": element,
        "color": ELEMENT_COLORS[element],
        "attribution": data.get("attribution") or "",
        "dignified": card_is_dignified(index, dignity_matrix),
        "gindex": index,
        "search": " ".join(str(v) for v in (
            item["position_name"], data["title"], element, data.get("hebrew_letter"),
            data.get("path_or_sephira"), data.get("attribution"), data.get("platonic_solid"),
        ) if v).lower(),
    }


# Card attributes shown in the detail panel: (label, card_data key).
DETAIL_FIELDS = (
    ("Attribution", "attribution"), ("Path / Sephira", "path_or_sephira"),
    ("Hebrew letter", "hebrew_letter"), ("Spatial type", "spatial_type"),
    ("Platonic solid", "platonic_solid"), ("Dual solid", "dual_solid"),
    ("Topological role", "topological_role"), ("King Scale colour", "king_scale_color"),
)


def card_details(spread_results, cards, all_aspects_by_card, dignity_matrix, sign_carriers=None):
    """Per-card data for the click-to-open detail panel, indexed like spread_results. Each card
    carries its atlas (ootk.atlas) for the small maps; `sign_carriers` places a pip through its
    sign's Major and may be left out."""
    out = []
    for item, card in zip(spread_results, cards):
        data = item["card_data"]
        i = card["gindex"]
        out.append({
            "title": card["title"], "position": card["position_name"], "number": card["number"],
            "image": card_image_url(card["title"], "full"), "art": art_note(card["title"]),
            "element": card["element"], "color": card["color"],
            "dignified": card["dignified"],
            "fields": [[label, str(data.get(key))] for label, key in DETAIL_FIELDS
                       if data.get(key) not in (None, "", "N/A")],
            "aspects": all_aspects_by_card.get(i, []),
            "dignities": [f"{_signed(d['score'])} {d['relationship']}: {d['pair']}"
                          for d in dignity_matrix if i in (d["from_index"], d["to_index"])],
            "atlas": card_atlas(data, sign_carriers or {}),
        })
    return out


def _pair_curve(p, q, centre, bulge=0.22):
    """A curve from p to q bowed away from centre, so a link between two far-apart cards
    does not run under the cards between them. Returns (path, badge point)."""
    (x1, y1), (x2, y2) = p, q
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    length = math.hypot(x2 - x1, y2 - y1) or 1.0
    nx, ny = -(y2 - y1) / length, (x2 - x1) / length
    if (mx - centre[0]) * nx + (my - centre[1]) * ny < 0:
        nx, ny = -nx, -ny
    off = bulge * length
    return (f"M{x1:.1f},{y1:.1f} Q{mx + nx * off:.1f},{my + ny * off:.1f} {x2:.1f},{y2:.1f}",
            (round(mx + nx * off / 2, 1), round(my + ny * off / 2, 1)))


def _ring_arc(r, a0, a1):
    """The short arc between two angles (degrees) on radius r. Returns (path, badge point)."""
    d = (a1 - a0 + 540) % 360 - 180
    x0, y0 = _svg_point(r, a0)
    x1, y1 = _svg_point(r, a0 + d)
    return f"M{x0},{y0} A{r},{r} 0 0 {0 if d > 0 else 1} {x1},{y1}", _svg_point(r, a0 + d / 2)


def _pair_link(pair, path, badge):
    return {"a": pair["a"], "b": pair["b"], "score": pair["score"], "score_text": _signed(pair["score"]),
            "color": DIGNITY_COLORS.get(pair["score"], DIGNITY_COLORS[0]),
            "d": path, "bx": badge[0], "by": badge[1]}


def _layout_drawing(layout_key, cards, aspects, pairs=()):
    scale = LAYOUT_SCALE.get(layout_key, DEFAULT_LAYOUT_SCALE)
    w, h = LAYOUT_CARD.get(layout_key, DEFAULT_LAYOUT_CARD)
    coords = SPREAD_DEFAULT_COORDINATES[layout_key][:len(cards)]
    points = [(x * scale, -y * scale) for x, y in coords]
    frame = [(x * scale, -y * scale) for x, y in TRIANGLE_FRAME.get(layout_key, [])]

    xs = [x for x, _ in points] + [x for x, _ in frame]
    ys = [y for _, y in points] + [y for _, y in frame]
    min_x, max_x = min(xs) - w / 2 - PAD, max(xs) + w / 2 + PAD
    min_y, max_y = min(ys) - h / 2 - PAD, max(ys) + h / 2 + PAD

    slots = [dict(card, x=round(px - w / 2, 2), y=round(py - h / 2, 2), cx=px, cy=py, w=w, h=h)
             for card, (px, py) in zip(cards, points)]
    lines = [dict(a, x1=points[a["a"]][0], y1=points[a["a"]][1],
                  x2=points[a["b"]][0], y2=points[a["b"]][1]) for a in aspects]
    centre = (sum(x for x, _ in points) / len(points), sum(y for _, y in points) / len(points))
    pair_links = [_pair_link(p, *_pair_curve(points[p["a"]], points[p["b"]], centre)) for p in pairs]
    return {
        "kind": "layout",
        "pair_links": pair_links,
        "badge_r": 10,
        "viewbox": f"{min_x:.0f} {min_y:.0f} {max_x - min_x:.0f} {max_y - min_y:.0f}",
        "width": round(max_x - min_x),
        "frame": " ".join(f"{x:.1f},{y:.1f}" for x, y in frame),
        "slots": slots,
        "lines": lines,
    }


def _wheel_drawing(layout_key, cards, aspects, pairs=()):
    n = len(cards)
    geo = dict(WHEEL[36 if n > 12 else 12])
    if layout_key == "9":
        geo["r_out"] = HOUSE_R_OUT   # a wider band, to fit each house's definition
    w, h = geo["card"]
    coords = SPREAD_DEFAULT_COORDINATES[layout_key][:n]
    angles = [math.degrees(math.atan2(y, x)) % 360 for x, y in coords]
    half = 180.0 / n

    slots, sectors, labels = [], [], []
    for i, (card, ang) in enumerate(zip(cards, angles), start=1):
        cx, cy = _svg_point(geo["r_card"], ang)
        slots.append(dict(card, x=round(cx - w / 2, 2), y=round(cy - h / 2, 2), cx=cx, cy=cy, w=w, h=h))
        sectors.append({"d": _sector_path(geo["r_in"], geo["r_band"], ang - half, ang + half),
                        "color": card["color"], "title": card["position_name"]})
        lx, ly = _svg_point((geo["r_band"] + geo["r_out"]) / 2, ang)
        sub = []
        if layout_key == "9":
            text = f"House {i}"
            sub = _note_lines(position_note(card["position_name"]))
        else:
            text = (SIGN_GLYPHS.get(card["label"], "") + " " + card["label"]).strip()
        labels.append({"x": lx, "y": ly, "text": text, "sub": [s_ for s_ in sub if s_]})

    band = []
    if n == 36:
        # Outer band names the sign each run of three decans belongs to.
        labels = []
        for s, sign in enumerate(SIGNS):
            a0, a1 = angles[3 * s] - half, angles[3 * s + 2] + half
            mid = (a0 + a1) / 2
            band.append({"d": _sector_path(geo["r_band"], geo["r_out"], a0, a1)})
            lx, ly = _svg_point((geo["r_band"] + geo["r_out"]) / 2, mid)
            labels.append({"x": lx, "y": ly, "text": f"{SIGN_GLYPHS[sign]} {sign}"})

    r_line = geo["r_in"] - 4
    ends = [_svg_point(r_line, ang) for ang in angles]
    lines = [dict(a, x1=ends[a["a"]][0], y1=ends[a["a"]][1],
                  x2=ends[a["b"]][0], y2=ends[a["b"]][1]) for a in aspects]
    # Element pairs run round the inside of the card ring, between neighbouring cards.
    r_pair = (geo["r_in"] + geo["r_card"] - geo["card"][1] / 2) / 2
    pair_links = [_pair_link(p, *_ring_arc(r_pair, angles[p["a"]], angles[p["b"]])) for p in pairs]
    r = geo["r_out"] + PAD
    return {
        "kind": "wheel",
        "pair_links": pair_links,
        "badge_r": 9 if n > 12 else 10,
        "viewbox": f"{-r} {-r} {2 * r} {2 * r}",
        "width": 2 * r,
        "r_out": geo["r_out"], "r_band": geo["r_band"], "r_in": geo["r_in"], "r_line": r_line,
        "sectors": sectors,
        "band": band,
        "labels": labels,
        "label_size": 15 if n <= 12 else 13,
        "slots": slots,
        "lines": lines,
    }


def segment_drawing(layout_key, cards, aspects, pairs=()):
    """Pixel geometry for one segment, or a plain card row when it has no layout.

    `pairs` are the segment's element pairs ({a, b, score}, segment-local indices).
    """
    coords = SPREAD_DEFAULT_COORDINATES.get(layout_key)
    if not coords or len(coords) < len(cards):
        return {"kind": "row", "slots": cards, "lines": [], "pair_links": []}
    if layout_key in RING_LAYOUT_ASPECTS:
        return _wheel_drawing(layout_key, cards, aspects, pairs)
    return _layout_drawing(layout_key, cards, aspects, pairs)


def _dignity_counts(entries):
    scores = [d["score"] for d in entries]
    return {
        "pairs": len(scores),
        "strong": sum(s == DIGNITY_SAME for s in scores),
        "friendly": sum(s == DIGNITY_FRIENDLY for s in scores),
        "neutral": sum(s == 0 for s in scores),
        "contrary": sum(s == DIGNITY_CONTRARY for s in scores),
        "net": sum(scores),
        "net_text": _signed(sum(scores)),
    }


def _aspect_counts(aspects):
    counts = Counter(a["type"] for a in aspects)
    return {
        "total": len(aspects),
        "by_type": [{"type": t, "count": counts[t], "color": ASPECT_COLORS[t]}
                    for t in ASPECT_TYPES if counts[t]],
        "strong": sum(a["strong"] for a in aspects),
        "flowing": sum(a["score"] > 0 for a in aspects),
        "tense": sum(a["score"] < 0 for a in aspects),
        "net": sum(a["score"] for a in aspects),
        "net_text": _signed(sum(a["score"] for a in aspects)),
    }


def _element_rows(counts):
    total = sum(counts.values()) or 1
    return [{"element": e, "count": counts.get(e, 0), "pct": round(100 * counts.get(e, 0) / total, 1),
             "color": ELEMENT_COLORS[e]} for e in ELEMENTS]


def _and(names):
    """['Fire', 'Air', 'Water'] -> 'Fire, Air and Water'."""
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


def _headline(element_rows, dignity, aspects):
    """A few plain sentences that lead the report."""
    ranked = sorted((r for r in element_rows if r["element"] != "Spirit"), key=lambda r: -r["count"])
    lines = []
    if ranked and ranked[0]["count"]:
        top, low = ranked[0], ranked[-1]
        if top["count"] == low["count"]:
            lines.append("The four elements are evenly balanced.")
        else:
            # Name every element in a tie, so a three-card draw never reads as one leader.
            leaders = [r["element"] for r in ranked if r["count"] == top["count"]]
            lows = [r["element"] for r in ranked if r["count"] == low["count"]]
            lead = (f"{leaders[0]} leads ({top['pct']:g}%)" if len(leaders) == 1
                    else f"{_and(leaders)} share the lead ({top['pct']:g}% each)")
            if low["count"] == 0:
                tail = f"{_and(lows)} {'is' if len(lows) == 1 else 'are'} absent"
            else:
                tail = (f"{lows[0]} is weakest ({low['pct']:g}%)" if len(lows) == 1
                        else f"{_and(lows)} are weakest ({low['pct']:g}% each)")
            lines.append(f"{lead}; {tail}.")
    if dignity["pairs"]:
        lean = ("favourable" if dignity["net"] > 0 else "unfavourable" if dignity["net"] < 0 else "even")
        lines.append(f"Elemental dignities lean {lean}: net {dignity['net_text']} across "
                     f"{dignity['pairs']} neighbouring pairs ({dignity['contrary']} contrary).")
    if aspects["total"]:
        if aspects["flowing"] > aspects["tense"]:
            mood = "Flowing aspects outnumber tense ones"
        elif aspects["tense"] > aspects["flowing"]:
            mood = "Tense aspects outnumber flowing ones"
        else:
            mood = "Flowing and tense aspects are level"
        lines.append(f"{mood} ({aspects['flowing']} to {aspects['tense']}); "
                     f"{aspects['strong']} of {aspects['total']} aspects are strong.")
    return lines


def withheld_view(withheld):
    """The cards a near-whole-deck draw left out (analysis.withheld_summary), or None."""
    if not withheld:
        return None
    cards = []
    for row in withheld["cards"]:
        element = derive_primary_element(row)
        cards.append({"title": row["title"], "short": short_card_name(row["title"]),
                      "image": card_image_url(row["title"]), "srcset": card_srcset(row["title"]),
                      "art": art_note(row["title"]),
                      "element": element,
                      "color": ELEMENT_COLORS[element], "attribution": row.get("attribution"),
                      "solid": row.get("platonic_solid")})
    return {"cards": cards, "note": withheld_sentence(withheld),
            "elements": [{"element": e, "count": c, "color": ELEMENT_COLORS[e]}
                         for e, c in withheld["elements"].items() if c]}


SCORE_RULE = ("Element scores follow Book T: the same element +2, friendly elements +1, contrary "
              "elements \u22122 (Fire with Water, Air with Earth), and 0 when either card is Spirit.")


def element_reason(e1, e2):
    """Why two elements score what they do, in a few words: 'Fire and Water: contrary elements'."""
    score, _ = element_dignity(e1, e2)
    if score == DIGNITY_SAME:
        return f"both {e1}: same element"
    if score == DIGNITY_CONTRARY:
        return f"{e1} and {e2}: contrary elements"
    if score == DIGNITY_FRIENDLY:
        return f"{e1} and {e2}: friendly elements"
    return f"{e1} and {e2}: Spirit scores 0 with any element"


def link_explainer(layout_key, n_cards, has_layout):
    """Plain sentences on how one operation links its cards. Mechanics only, never meaning."""
    if n_cards < 2:
        return []
    unit = RING_UNITS.get(layout_key)
    if unit and has_layout:
        n = len(SPREAD_DEFAULT_COORDINATES[layout_key])
        step = 360 / n
        names = [a for a in ("Sextile", "Square", "Trine", "Opposition")
                 if a in RING_LAYOUT_ASPECTS[layout_key]]
        bits = [f"{round(ASPECTS_BY_NAME[a].angle / step)} {unit}s apart is {'an' if a[0] in 'AEIOU' else 'a'} {a.lower()} "
                f"({ASPECTS_BY_NAME[a].angle:g}\u00b0, {_signed(ASPECTS_BY_NAME[a].score)})" for a in names]
        per_card = sum(1 if ASPECTS_BY_NAME[a].angle == 180 else 2 for a in names)
        return [
            f"The {n_cards} cards sit round a wheel of {n} {unit}s, one in each {unit}.",
            f"Element pairs link each {unit} with the next, and the last with the first, so the "
            f"circle closes. {SCORE_RULE}",
            f"Aspect lines link every two {unit}s that stand an exact aspect apart: {_and(bits)}. "
            f"So each card has {per_card} aspect links. They belong to the wheel and are the same in "
            f"every reading; what changes is which cards sit at the two ends.",
        ]
    if layout_key == "8":
        first = (f"The {n_cards} cards are laid out in a heap around the significator and linked in the "
                 f"order they were dealt: 1 with 2, 2 with 3, and so on to {n_cards - 1} with {n_cards}.")
    else:
        first = "The cards are linked in the order they were laid out: 1 with 2, 2 with 3, and so on."
    lines = [first, f"Each pair gets an element score. {SCORE_RULE}"]
    if has_layout:
        lines.append("Each pair also gets an aspect: the angle between the two places, seen from the "
                     "middle of the layout, matched to the nearest astrological aspect. A pair with no "
                     "aspect is drawn dashed. The angle belongs to the layout, so it is the same in "
                     "every reading.")
    return lines


def _apart_text(layout_key, aspect):
    unit = RING_UNITS.get(layout_key)
    angle = aspect.get("angle")
    if angle is None:
        return ""
    if unit:
        step = 360 / len(SPREAD_DEFAULT_COORDINATES[layout_key])
        return f"{round(angle / step)} {unit}s apart ({angle:g}\u00b0)"
    if aspect["type"] == UNASPECTED:
        return f"{angle:g}\u00b0 apart, no aspect within orb"
    return f"{angle:g}\u00b0 apart round the middle"


def _where(layout_key, card):
    """How the link list names a card's place: numbered like the drawing's badges, unless the
    label already is ('Decan 5: ...'); a house also gives its definition."""
    if re.match(r"\w+ \d+:", card["label"]):
        return card["label"]
    where = f"{card['index'] + 1}. {card['label']}"
    note = position_note(card["position_name"]) if layout_key == "9" else ""
    return f"{where}: {note}" if note else where


def link_view(layout_key, cards, aspects, pairs):
    """Data for a segment's link inspector: its cards, element pairs and aspects, each link
    with a short reason. Indices are segment-local."""
    ring = layout_key in RING_LAYOUT_ASPECTS
    return {
        "unit": RING_UNITS.get(layout_key, "place"),
        "cards": [dict({k: c[k] for k in ("index", "gindex", "position_name", "title", "element",
                                          "color", "image", "art", "attribution")},
                       # Numbered like the drawing's badges, unless the label already is ("Decan 5: ...").
                       where=_where(layout_key, c))
                  for c in cards],
        "pairs": [dict(p, score_text=_signed(p["score"]),
                       why=element_reason(cards[p["a"]]["element"], cards[p["b"]]["element"]))
                  for p in pairs],
        "aspects": [{
            "a": a["a"], "b": a["b"], "type": a["type"], "color": a["color"],
            "score": a["score"], "score_text": a["score_text"], "apart": _apart_text(layout_key, a),
            # On a wheel the aspect pairs are not neighbours, so they carry their own element score.
            "cards": (f"{element_reason(cards[a['a']]['element'], cards[a['b']]['element'])} "
                      f"({_signed(element_dignity(cards[a['a']]['element'], cards[a['b']]['element'])[0])})"
                      if ring else ""),
        } for a in aspects],
    }


def build_report_view(spread_key, spread_results, element_counts, dignity_matrix, spatial_matrix,
                      macro_framework, framework_basis, sign_carriers=None):
    """Everything report.html needs beyond the raw prompt: summary first, then segments."""
    cards = [_card_view(item, i, dignity_matrix) for i, item in enumerate(spread_results)]
    all_aspects = []
    aspects_by_card = {}
    segments = []
    for number, (layout_key, start, end, name) in enumerate(
            spread_segments(spread_results, spread_key), start=1):
        seg_cards = [dict(c, index=c["index"] - start) for c in cards[start:end]]
        seg_aspects = [_aspect_view(s, start) for s in spatial_matrix
                       if start <= s["from_index"] < end]
        seg_dignity = [d for d in dignity_matrix if start <= d["from_index"] < end]
        seg_pairs = [{"a": d["from_index"] - start, "b": d["to_index"] - start, "score": d["score"]}
                     for d in seg_dignity]
        all_aspects.extend(seg_aspects)
        for a in seg_aspects:
            for i in (a["a"] + start, a["b"] + start):
                aspects_by_card.setdefault(i, []).append(f"{a['label']} ({a['score_text']}): {a['pair']}")
        seg_elements = Counter(c["element"] for c in seg_cards)
        drawing = segment_drawing(layout_key, seg_cards, seg_aspects, seg_pairs)
        segments.append({
            "id": f"op{number}",
            "name": name or "Spread",
            "cards": seg_cards,
            "elements": _element_rows(seg_elements),
            "dignity": _dignity_counts(seg_dignity),
            "dignity_rows": [dict(d, score_text=_signed(d["score"])) for d in seg_dignity],
            "aspects": seg_aspects,
            "aspect_counts": _aspect_counts(seg_aspects),
            "ill_dignified": [c for c in seg_cards if not c["dignified"]],
            "drawing": drawing,
            "how": link_explainer(layout_key, len(seg_cards), drawing["kind"] != "row"),
            "links": link_view(layout_key, seg_cards, seg_aspects, seg_pairs),
        })

    element_rows = _element_rows(element_counts)
    dignity = _dignity_counts(dignity_matrix)
    aspects = _aspect_counts(all_aspects)
    key_cards = [cards[0]] if cards else []
    if segments and len(segments[0]["cards"]) > 1:
        key_cards.append(cards[len(segments[0]["cards"]) - 1])
    return {
        "headline": _headline(element_rows, dignity, aspects),
        "framework": macro_framework,
        "framework_basis": framework_basis,
        "elements": element_rows,
        "spirit_secondary": spirit_bearing_cards(spread_results),
        "dignity": dignity,
        "aspects": aspects,
        "ill_dignified_count": sum(not c["dignified"] for c in cards),
        "card_count": len(cards),
        "key_cards": key_cards,
        "segments": segments,
        "card_details": card_details(spread_results, cards, aspects_by_card, dignity_matrix, sign_carriers),
        "aspect_types": [{"type": t, "color": ASPECT_COLORS[t], "strong": is_strong(
            next((a.score for a in ASPECTS if a.name == t), 0)),
            "key": (f"{ASPECTS_BY_NAME[t].angle:g}\u00b0, {_signed(ASPECTS_BY_NAME[t].score)}"
                    if t in ASPECTS_BY_NAME else "no aspect, 0")} for t in ASPECT_TYPES],
    }

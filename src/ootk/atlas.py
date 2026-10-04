"""Where each card sits in the correspondence systems: its path or sephira on the Tree of
Life, its place on the Cube of Space, its Platonic solid, its stretch of the zodiac (decans,
court spans, Princess quadrants) and its cell in the elemental grid.

Everything comes from the card's fetched row (db.fetch_cards_correspondences), so a picture
always agrees with the report and follows the active mapping system. Only the fixed frames
(the Tree's shape, the 36 decans in Book T order) are written here; tests check them
against the database. static/js/atlas.js draws the result. Nothing here interprets a card.
"""
import re

from ootk.analysis import ELEMENT_SOLIDS, PLANETARY_MAJORS, derive_primary_element, major_name

SIGNS = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
         "Sagittarius", "Capricorn", "Aquarius", "Pisces")
SIGN_ELEMENTS = ("Fire", "Earth", "Air", "Water") * 3
PLANETS = ("Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon")
ELEMENTS = ("Fire", "Water", "Air", "Earth")
SUIT_ELEMENTS = {"Wands": "Fire", "Cups": "Water", "Swords": "Air", "Disks": "Earth"}
ELEMENT_SUITS = {e: s for s, e in SUIT_ELEMENTS.items()}
# Book T: each court rank carries an element; the rank sits on one sephira (777's
# "The 4 Twos - Kings / Knights", "The 4 Threes - Queens", "The 4 Sixes - Princes",
# "The 4 Tens - Princesses").
RANK_ELEMENTS = {"Knight": "Fire", "Queen": "Water", "Prince": "Air", "Princess": "Earth"}
RANK_SEPHIRA = {"Knight": 2, "Queen": 3, "Prince": 6, "Princess": 10}

SEPHIROTH = ("Kether", "Chokmah", "Binah", "Chesed", "Geburah", "Tiphareth", "Netzach",
             "Hod", "Yesod", "Malkuth")
SEPHIROTH_ENGLISH = ("Crown", "Wisdom", "Understanding", "Mercy", "Strength", "Beauty",
                     "Victory", "Splendour", "Foundation", "Kingdom")
# Paths 11-32 (Golden Dawn numbering): the two sephiroth each joins, and its letter.
PATH_ENDS = {
    11: (1, 2), 12: (1, 3), 13: (1, 6), 14: (2, 3), 15: (2, 6), 16: (2, 4), 17: (3, 6),
    18: (3, 5), 19: (4, 5), 20: (4, 6), 21: (4, 7), 22: (5, 6), 23: (5, 8), 24: (6, 7),
    25: (6, 9), 26: (6, 8), 27: (7, 8), 28: (7, 9), 29: (7, 10), 30: (8, 9), 31: (8, 10),
    32: (9, 10),
}
LETTERS = dict(zip(range(11, 33), (
    ("Aleph", "א"), ("Beth", "ב"), ("Gimel", "ג"), ("Daleth", "ד"), ("Heh", "ה"),
    ("Vav", "ו"), ("Zain", "ז"), ("Cheth", "ח"), ("Teth", "ט"), ("Yod", "י"), ("Kaph", "כ"),
    ("Lamed", "ל"), ("Mem", "מ"), ("Nun", "נ"), ("Samekh", "ס"), ("Ayin", "ע"), ("Peh", "פ"),
    ("Tzaddi", "צ"), ("Qoph", "ק"), ("Resh", "ר"), ("Shin", "ש"), ("Tav", "ת"))))

# The 36 decans from 0° Aries, ten degrees each. Rulers run in Chaldean order from Mars, as
# Book T gives them (Mars, Sun, Venus in Aries = the 2, 3 and 4 of Wands).
_CHALDEAN = ("Mars", "Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter")
DECAN_RULERS = tuple(_CHALDEAN[i % 7] for i in range(36))


def decan_pip(index):
    """Book T's small card for decan `index` (0 = Aries 0-10°): (suit, number)."""
    sign, third = divmod(index, 3)
    return ELEMENT_SUITS[SIGN_ELEMENTS[sign]], 2 + 3 * (sign % 3) + third


def _short(title):
    """'XIX - The Sun' -> 'The Sun'; '2 of Wands - Dominion' -> '2 of Wands'."""
    head, _, tail = str(title).partition(" - ")
    return head if " of " in head else (tail or head)


def _deg(text):
    """'20° Scorpio' -> 230."""
    m = re.match(r"\s*(\d+)°\s*(\w+)", text)
    return SIGNS.index(m.group(2)) * 30 + int(m.group(1)) if m and m.group(2) in SIGNS else None


def _words(text):
    return re.findall(r"[A-Za-z]+", str(text or ""))


def first_of(text, names):
    """The first of `names` named as a whole word in `text`, or None."""
    for w in _words(text):
        if w in names:
            return w
    return None


def path_number(row):
    """The card's path on the Tree (11-32), or None. French/Egyptian rows name it ('Path 16
    (Chokmah-Chesed)'); otherwise it is the key_scale the active system joined on."""
    m = re.match(r"Path (\d+)", str(row.get("path_or_sephira") or ""))
    if m:
        return int(m.group(1))
    ks = row.get("key_scale")
    return ks if isinstance(ks, int) and 11 <= ks <= 32 else None


def card_element(row):
    suit = row.get("suit")
    if suit in SUIT_ELEMENTS:
        return SUIT_ELEMENTS[suit]
    return derive_primary_element(row)


def _tree(row, kind):
    rank = row.get("number_or_rank")
    if kind == "Minor":
        n = 1 if str(rank) in ("1", "Ace") else int(rank)
        return {"path": None, "sephira": [n],
                "note": f"Sephira {n}, {SEPHIROTH[n - 1]} ({SEPHIROTH_ENGLISH[n - 1]}): "
                        f"the {'Aces' if n == 1 else f'{n}s'} of all four suits sit here."}
    p = path_number(row)
    name, glyph = LETTERS.get(p, ("", ""))
    a, b = PATH_ENDS.get(p, (None, None))
    joins = f"joining {SEPHIROTH[a - 1]} and {SEPHIROTH[b - 1]}" if p else ""
    if kind == "Court":
        s = RANK_SEPHIRA.get(rank)
        note = (f"Path {p}, {name} ({glyph}), the letter of its main sign or element, {joins}. " if p else "")
        if s:
            note += f"As a {rank} it also sits on {SEPHIROTH[s - 1]} (Liber 777)."
        return {"path": p, "sephira": [s] if s else [], "note": note.strip()}
    return {"path": p, "sephira": [], "note": f"Path {p}, {name} ({glyph}), {joins}." if p else ""}


def _zodiac(row, kind):
    """Arcs of the zodiac (degrees from 0° Aries) and decan indexes the card covers."""
    text = row.get("attribution") or ""
    rank = row.get("number_or_rank")
    if kind == "Minor":
        sign = first_of(text, SIGNS)
        if not sign:
            return {"arcs": [], "decans": [], "note": "Aces carry no decan: each is the root of its element."}
        n = int(rank)
        i = SIGNS.index(sign) * 3 + (n - 2) % 3
        return {"arcs": [[i * 10, i * 10 + 10]], "decans": [i],
                "note": f"{text}: decan {i % 3 + 1} of {sign}, {i * 10 % 30}° to {i * 10 % 30 + 10}°."}
    if kind == "Court":
        span = re.search(r"(\d+°\s*\w+)\s+to\s+(\d+°\s*\w+)", text)
        if span:
            a, b = _deg(span.group(1)), _deg(span.group(2))
            first = a // 10
            decans = [(first + k) % 36 for k in range(3)]
            return {"arcs": [[a, b if b > a else b + 360]], "decans": decans,
                    "note": f"From {span.group(1)} to {span.group(2)}: thirty degrees across three decans."}
        signs = [s for s in _words(text) if s in SIGNS]
        if signs:
            a = SIGNS.index(signs[0]) * 30
            return {"arcs": [[a, a + 90]], "decans": [(a // 10 + k) % 36 for k in range(9)],
                    "note": f"A quadrant of the zodiac: {', '.join(signs)}."}
        return {"arcs": [], "decans": [], "note": ""}
    sign = first_of(text, SIGNS)
    if sign:
        i = SIGNS.index(sign)
        return {"arcs": [[i * 30, i * 30 + 30]], "decans": [i * 3, i * 3 + 1, i * 3 + 2],
                "note": f"{sign}: the sign's thirty degrees and its three decans."}
    planet = first_of(text, PLANETS)
    if planet:
        decans = [i for i, p in enumerate(DECAN_RULERS) if p == planet]
        return {"arcs": [[i * 10, i * 10 + 10] for i in decans], "decans": decans,
                "note": f"{planet}: the {len(decans)} decans it rules in Book T."}
    element = first_of(text, ELEMENTS)
    if element:
        signs = [i for i, e in enumerate(SIGN_ELEMENTS) if e == element]
        return {"arcs": [[i * 30, i * 30 + 30] for i in signs],
                "decans": [i * 3 + k for i in signs for k in range(3)],
                "note": f"{element}: the three signs of {element}."}
    return {"arcs": [], "decans": [], "note": "No sign, planet or element in this system's attribution."}


def _cube(row, kind, signs):
    if kind in ("Major", "Court"):
        place = row.get("spatial_dimension")
        if not place:
            return {"place": None, "note": ""}
        letter = row.get("hebrew_letter") or ""
        where = place_label(place)
        return {"place": place, "derived": False,
                "note": f"The {where}, where its letter {letter} sits." if letter not in ("", "N/A")
                        else f"The {where}."}
    sign = first_of(row.get("attribution") or "", SIGNS)
    via = signs.get(sign)
    if not via or not via.get("place"):
        return {"place": None, "note": "Aces have no place on the cube." if sign is None else ""}
    return {"place": via["place"], "derived": True,
            "note": f"Not placed itself. Its sign, {sign}, belongs to {via['card']}, whose letter "
                    f"{via['letter']} sits on the {place_label(via['place'])}."}


FACE_LABELS = {"Up (Zenith)": "upper face (Zenith)", "Down (Nadir)": "lower face (Nadir)",
               "East": "east face", "West": "west face", "North": "north face", "South": "south face",
               "Center Core (Holy Temple)": "centre (Holy Temple)"}


def place_label(place):
    """'East' -> 'east face'; edges and axes keep their own names."""
    return FACE_LABELS.get(place, place)


def _solid(row):
    name = row.get("platonic_solid")
    if not name:
        return None
    f, v = row.get("solid_faces"), row.get("solid_vertices")
    return {"name": name, "faces": f, "vertices": v, "edges": f + v - 2 if f and v else None,
            "dual": row.get("dual_solid")}


def _grid(row, kind, element):
    if kind == "Court":
        return {"row": SUIT_ELEMENTS.get(row.get("suit")), "col": RANK_ELEMENTS.get(row.get("number_or_rank")),
                "note": f"{RANK_ELEMENTS.get(row.get('number_or_rank'))} of {SUIT_ELEMENTS.get(row.get('suit'))}: "
                        f"its rank gives the first element, its suit the second."}
    if element in ELEMENTS:
        return {"row": element, "col": None,
                "note": f"{element}: the {ELEMENT_SUITS[element]} row." if kind == "Minor"
                        else f"Its element is {element}; the row is the {ELEMENT_SUITS[element]}."}
    return {"row": None, "col": None, "note": "Spirit stands outside the four elements."}


def sign_carriers(rows):
    """{sign: {card, letter, place}}: which Major carries each sign in the active system,
    and where its letter sits on the cube. Built from the Majors' fetched rows."""
    out = {}
    for row in rows:
        if row.get("arcana_type") != "Major":
            continue
        sign = first_of(row.get("attribution"), SIGNS)
        if sign and sign not in out:
            out[sign] = {"card": _short(row["title"]), "letter": row.get("hebrew_letter") or "",
                         "place": row.get("spatial_dimension")}
    return out


def card_atlas(row, signs):
    """One card's place in each system, with a plain sentence for each picture."""
    kind = row.get("arcana_type")
    element = card_element(row)
    return {
        "title": row["title"], "short": _short(row["title"]), "kind": kind, "element": element,
        "letter": row.get("hebrew_letter") if row.get("hebrew_letter") not in (None, "N/A") else "",
        "attribution": row.get("attribution") or "",
        "tree": _tree(row, kind), "cube": _cube(row, kind, signs), "zodiac": _zodiac(row, kind),
        "solid": _solid(row), "grid": _grid(row, kind, element),
        "colour": (row.get("attributions") or {}).get("king_scale_hex") if kind == "Major" else None,
        "colour_name": row.get("king_scale_color") if kind == "Major" else None,
    }


def solid_note(name, kind, title):
    """Why the card has this solid (the engine's rule, analysis.card_solid)."""
    if kind == "Major" and major_name({"title": title}) in PLANETARY_MAJORS:
        return f"{name}: the planetary Majors keep the Dodecahedron."
    element = next((e for e, s in ELEMENT_SOLIDS.items() if s == name), None)
    return f"{name}: the solid of {element}, the card's element." if element else name


def deck_atlas(rows):
    """The whole deck for the maps page: every card's atlas plus the shared frames. `rows`
    are fetched rows in deck order."""
    signs = sign_carriers(rows)
    cards = []
    for row in rows:
        a = card_atlas(row, signs)
        if a["solid"]:
            a["solid"]["note"] = solid_note(a["solid"]["name"], a["kind"], row["title"])
        cards.append(a)
    by_short = {c["short"]: i for i, c in enumerate(cards)}
    decans = []
    for i in range(36):
        suit, n = decan_pip(i)
        short = f"{n} of {suit}"
        decans.append({"sign": SIGNS[i // 3], "ruler": DECAN_RULERS[i], "card": short,
                       "index": by_short.get(short)})
    return {
        "cards": cards,
        "paths": {p: {"letter": LETTERS[p][0], "glyph": LETTERS[p][1], "ends": PATH_ENDS[p],
                      "cards": [i for i, c in enumerate(cards) if c["tree"]["path"] == p]}
                  for p in PATH_ENDS},
        "sephiroth": [{"name": SEPHIROTH[n], "english": SEPHIROTH_ENGLISH[n],
                       "cards": [i for i, c in enumerate(cards) if n + 1 in c["tree"]["sephira"]]}
                      for n in range(10)],
        "decans": decans,
        "signs": [{"name": s, "element": SIGN_ELEMENTS[i], "carrier": signs.get(s, {})}
                  for i, s in enumerate(SIGNS)],
    }


def letter_rows(atlas):
    """The 22 letters as a table: letter, path, Major, attribution, cube place, solid."""
    out = []
    for p, path in atlas["paths"].items():
        major = next((atlas["cards"][i] for i in path["cards"] if atlas["cards"][i]["kind"] == "Major"), None)
        courts = [atlas["cards"][i]["short"] for i in path["cards"] if atlas["cards"][i]["kind"] == "Court"]
        a, b = path["ends"]
        out.append({
            "path": p, "letter": f"{path['letter']} {path['glyph']}",
            "joins": f"{SEPHIROTH[a - 1]} to {SEPHIROTH[b - 1]}",
            "major": major["short"] if major else "", "major_index": atlas["cards"].index(major) if major else None,
            "attribution": major["attribution"] if major else "",
            "place": major["cube"]["place"] if major else "",
            "solid": major["solid"]["name"] if major and major["solid"] else "",
            "colour": major["colour"] if major else None, "colour_name": major["colour_name"] if major else "",
            "courts": ", ".join(courts),
        })
    return out


def sign_rows(atlas):
    """The twelve signs as a table: element, carrier Major, cube place, decan cards, courts."""
    cards = atlas["cards"]
    out = []
    for i, s in enumerate(atlas["signs"]):
        start = i * 30
        courts = [c["short"] for c in cards if c["kind"] == "Court" and c["zodiac"]["arcs"]
                  and (c["zodiac"]["arcs"][0][1] - c["zodiac"]["arcs"][0][0]) == 30
                  and any(start <= (a % 360) < start + 30 or start < (b % 360 or 360) <= start + 30
                          for a, b in c["zodiac"]["arcs"])]
        out.append({
            "sign": s["name"], "element": s["element"],
            "carrier": s["carrier"].get("card", ""), "letter": s["carrier"].get("letter", ""),
            "place": s["carrier"].get("place") or "",
            "decans": [f"{d['card']} ({d['ruler']})" for d in atlas["decans"][i * 3:i * 3 + 3]],
            "courts": ", ".join(courts),
        })
    return out

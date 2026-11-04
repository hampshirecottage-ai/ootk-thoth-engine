"""Builds the analytical report (Markdown prompt) and its HTML export."""
import html
import re
from datetime import datetime, timezone

from ootk import PROJECT_ROOT as BASE_DIR
from ootk import gematria
from ootk.analysis import (
    SUIT_ELEMENTS, analyze_elemental_balance, analyze_hebrew_spatial_distribution,
    analyze_platonic_topology, analyze_spatial_vectors, calculate_elemental_dignities, card_home,
    book_t_counts, derive_primary_element, evaluate_macro_framework, own_place_check, own_place_sentence,
    major_element_note, spirit_bearing_cards,
)
from ootk.birth_cards import birth_cards_markdown
from ootk.rules import ASPECTS, GEOMANTIC_FIGURES, planet_dignity_note, DIGNITY_CONTRARY, DIGNITY_FRIENDLY, DIGNITY_NEUTRAL, DIGNITY_SAME
from ootk.book_t import SITE_RULES, count_value, status_line
from ootk.shuffle import operation_number
from ootk.sky import sky_line
from ootk.spreads import BOOK_T_KEY, CELTIC_CROSS_KEY, SPREADS, ZODIAC_SIGNS, spread_segments

# The report header and the web form both name the systems from here, so the label always
# says which way the Tzaddi/Heh swap goes (see db.fetch_cards_correspondences).
MAPPING_LABELS = {
    "thoth": "Thoth / Crowley (Liber 777; Emperor on Tzaddi, Star on Heh)",
    "golden_dawn": "Golden Dawn / English System (Emperor on Heh, Star on Tzaddi)",
    "french_egyptian": "French / Egyptian System (Lévi / Papus / Wirth)",
}

# A note under the system name, for a system whose path numbers would otherwise read as a
# clash with the Golden Dawn Tree an AI already knows.
MAPPING_NOTES = {
    "thoth": (
        "Crowley swapped the letters Tzaddi and Heh, not the signs: the Emperor and the Queen of "
        "Wands stay Aries and the Star and the Prince of Swords stay Aquarius. Their colour scales "
        "and Cube of Space edge follow the sign, so a card on Tzaddi can sit on Heh's "
        "edge (North-East, Aries) and the reverse."
    ),
    "french_egyptian": (
        "Under this system each Major takes the Hebrew letter of its own number (I = Aleph, "
        "II = Beth ... XXI = Tav; the Fool = Shin, which Papus places between XX and XXI), and "
        "its \"Path n\" is the Tree path that carries that letter. So The Star (XVII) is Peh on "
        "Path 27 (Netzach-Hod) and The Devil (XV) is Samekh on Path 25 (Tiphareth-Yesod). These "
        "are not the Golden Dawn card-to-path pairings: the Thoth and Golden Dawn letters on each "
        "card's Comparative Hebrew Mapping line are there for comparison only. Minor and court "
        "cards keep their Thoth places."
    ),
}

# The Thoth components a reading's prompt can leave out, to test which of them help (see
# without_components). Card symbolism has no switch: the card's title carries it, and a prompt
# without the tables (scripts/ai_check.py "cards only") is the baseline. Opening of the Key has
# none either: it is the spread chosen. Leaving a component out never changes the cards drawn.
COMPONENTS = {
    "elements": "Elemental dignities",
    "astrology": "Astrology",
    "hebrew": "Hebrew letters",
    "tree": "Tree of Life",
    "courts": "Court card detail",
    "numerology": "Numerology (Book T counts)",
    "geomancy": "Geomantic figures",
    "geometry": "Geometry (Cube of Space, solids, aspects)",
    "gematria": "Gematria (letter values)",
}
def without_components(text):
    """frozenset of COMPONENTS keys from "astrology,geometry" (spaces and case ignored).
    Raises ValueError naming the keys allowed for anything else."""
    keys = [k.strip().lower() for k in re.split(r"[,\s]+", text or "") if k.strip()]
    unknown = [k for k in keys if k not in COMPONENTS]
    if unknown:
        raise ValueError(f"Unknown component {', '.join(map(repr, unknown))}. "
                         f"Use any of: {', '.join(COMPONENTS)}.")
    return frozenset(keys)

def components_param(off):
    """"astrology,geometry": the keys in COMPONENTS order, for a share link, a saved reading and
    `ootk --without`; "" when nothing is left out."""
    return ",".join(k for k in COMPONENTS if k in off)

def components_off_markdown(off):
    """The header line naming what this prompt leaves out, so the AI does not fill it in."""
    if not off:
        return ""
    names = ", ".join(COMPONENTS[k] for k in COMPONENTS if k in off)
    return (f"**Components Left Out:** {names}. They were switched off for this reading to test "
            "what each part adds. Do not bring them in from your own knowledge, even where a "
            "card's name or position hints at them; read only what is listed here.\n")

def _left_out(*keys):
    return ("* Left out on purpose: " + " and ".join(COMPONENTS[k] for k in keys)
            + " (see Components Left Out in the header).\n")

# Hebrew vowel points and cantillation marks. Every Hebrew name in the prompt carries its
# transliteration, so dropping the points loses nothing and saves many tokens.
_HEBREW_POINTS = re.compile("[\u0591-\u05BD\u05BF\u05C1\u05C2\u05C4\u05C5\u05C7]")
_SOLID_FIELDS = ("solid_faces", "solid_vertices", "dual_solid", "topological_role")
_MINOR_SPATIAL = ("Sephira_Point", "Nodal Sphere (Sephira)")

def strip_hebrew_points(text):
    return _HEBREW_POINTS.sub("", text)

def _solid_legend(spread_results):
    """{solid: (faces, vertices, dual, role)} for solids whose cards all agree on those fields."""
    legend, mixed = {}, set()
    for item in spread_results:
        data = item["card_data"]
        solid = data.get("platonic_solid")
        if not solid:
            continue
        props = tuple(data.get(f, "N/A") for f in _SOLID_FIELDS)
        if legend.setdefault(solid, props) != props:
            mixed.add(solid)
    return {k: v for k, v in legend.items() if k not in mixed}

def analyze_reading(spread_name, spread_key, query_prompt, significator, seed_val, spread_results,
                    framework="auto", mapping_system="thoth", withheld=None, significator_places=None,
                    drawn_at=None, local_zone=None, book_t_ops=None, without=frozenset(),
                    birth_cards=""):
    """Every analysis of a drawn spread, then its prompt. The command line and the web site both
    call this, so the same draw always gives the same prompt from either. `without` is a set of
    COMPONENTS keys the prompt leaves out; the analyses themselves always run."""
    element_counts = analyze_elemental_balance(spread_results)
    dignity_matrix = calculate_elemental_dignities(spread_results, spread_key)
    spatial_matrix = analyze_spatial_vectors(spread_results, spread_key)
    spatial_dist, spatial_details = analyze_hebrew_spatial_distribution(spread_results)
    solid_counts, topology_details, dual_pairings = analyze_platonic_topology(spread_results, spread_key)
    macro_framework, framework_basis = evaluate_macro_framework(spread_results, forced_framework=framework)
    own_place = own_place_check(spread_results, spread_key)
    analytical_prompt = build_analytical_prompt(
        spread_name, query_prompt, significator, seed_val, spread_results, element_counts,
        dignity_matrix, spatial_matrix, spatial_dist, solid_counts, dual_pairings, macro_framework,
        mapping_system=mapping_system, framework_basis=framework_basis, withheld=withheld, own_place=own_place,
        significator_places=significator_places, drawn_at=drawn_at, local_zone=local_zone,
        book_t=book_t_counts(spread_results, spread_key),
        book_t_notes=book_t_notes(spread_results, book_t_ops) if book_t_ops else None,
        without=without, birth_cards=birth_cards,
    )
    return {
        "element_counts": element_counts, "dignity_matrix": dignity_matrix,
        "spatial_matrix": spatial_matrix, "spatial_dist": spatial_dist,
        "spatial_details": spatial_details, "solid_counts": solid_counts,
        "topology_details": topology_details, "dual_pairings": dual_pairings,
        "macro_framework": macro_framework, "framework_basis": framework_basis,
        "own_place": own_place, "significator_places": significator_places or [],
        "analytical_prompt": analytical_prompt,
    }

# Section numbers, so the notes that point from one section to another stay right if the
# order changes. The cards come first: every later section names positions, and the AI
# reads them better once it knows which card sits where.
CARDS, ELEMENTS, HEBREW, SOLIDS, DIGNITY, SPATIAL = range(1, 7)   # section 7 is the instructions

def build_analytical_prompt(spread_name, query_prompt, significator, seed_val, spread_results, element_counts, dignity_matrix, spatial_matrix, spatial_dist, solid_counts, dual_pairings, macro_framework="3. Incarnational Life Path", mapping_system="thoth", framework_basis=None, withheld=None, own_place=None, significator_places=None, drawn_at=None, local_zone=None, book_t=None, book_t_notes=None, without=frozenset(), birth_cards=""):
    off = frozenset(without or ())
    unknown = off - set(COMPONENTS)
    if unknown:
        raise ValueError(f"Unknown component(s): {', '.join(sorted(unknown))}")
    if "numerology" in off:
        book_t = None
    if "astrology" in off:
        own_place = None
    if "tree" in off:
        framework_basis = None
    birth_line = birth_cards_markdown(birth_cards, spread_results) if "numerology" not in off else ""
    mapping_label = MAPPING_LABELS.get(mapping_system, mapping_system)
    mapping_note = MAPPING_NOTES.get(mapping_system) if not off & {"hebrew", "tree"} else None
    mapping_note_line = f"**Mapping Note:** {mapping_note}\n" if mapping_note else ""
    framework_basis_line = f"**Framework Basis:** {framework_basis}\n" if framework_basis else ""

    end_marker = end_of_prompt_marker(len(spread_results))
    header_md = f"""# HERMETIC ANALYTICAL REPORT & SYSTEM PROMPT
> **Before you start:** this prompt lists {_positions(len(spread_results))} and its very last line is `{end_marker}`. If you cannot see that line, the prompt was cut off: tell the user the last position you can see and that the rest is missing, ask them to send the rest, and do not interpret the reading until you have all of it.

{reading_time_markdown(drawn_at, local_zone, sky="astrology" not in off)}**Operation/Spread:** {spread_name}
**Query/Intent Topic:** {query_prompt or 'General Operation'}
**Significator:** {significator}
{significator_places_markdown(significator_places)}{birth_line}**PRNG Seed:** {seed_val or 'Manual Entry'}
**Macro Cabbalistic Framework:** {macro_framework}
{framework_basis_line}{own_place_markdown(own_place)}**Active Mapping System:** {mapping_label}
{mapping_note_line}{components_off_markdown(off)}"""
    legend = _solid_legend(spread_results)
    sections = (                     # in the order of the numbers above
        _cards_md(spread_results, legend, off),
        _elements_md(spread_results, element_counts, withheld, book_t, off),
        _hebrew_md(spatial_dist, off, spread_results),
        _solids_md(solid_counts, legend, dual_pairings, off,
                   "in a Celtic Cross" if spread_name == SPREADS[CELTIC_CROSS_KEY]["name"] else "in a heap"),
        _dignity_md(dignity_matrix, book_t_notes, off),
        _spatial_md(spatial_matrix, off),
        _instructions_md(query_prompt, mapping_label, macro_framework, spread_results, dignity_matrix,
                         spatial_matrix, solid_counts, dual_pairings, withheld, own_place,
                         significator_places, book_t, book_t_notes, off),
    )
    prompt_md = "".join(f"\n---\n\n## {n}. {body}" for n, body in enumerate(sections, start=1))
    prompt_md += f"\n{end_marker}\n"
    # The header keeps the querent's own text exactly as typed.
    return header_md + strip_hebrew_points(prompt_md)

def drawn_now():
    """This minute in UTC: the time a new reading is drawn, as the prompt gives it."""
    return datetime.now(timezone.utc).replace(second=0, microsecond=0)

def this_computer_zone():
    """This computer's own time zone, for a reading drawn at the command line."""
    return datetime.now().astimezone().tzinfo

def time_stamp(when):
    """'20261029T2200Z': how settings and share links carry a reading's time (ISO 8601, UTC)."""
    return f"{when.astimezone(timezone.utc):%Y%m%dT%H%M}Z"

def reading_time_markdown(drawn_at, local_zone=None, sky=True):
    """The header lines for when the reading was drawn and where the Sun and Moon stood then,
    or "" for a reading with no time (a sample, an old share link). `drawn_at` is an aware
    datetime; `local_zone` a tzinfo for the querent's own clock, or None for UTC only."""
    if drawn_at is None:
        return ""
    utc = drawn_at.astimezone(timezone.utc)
    when = f"{_long_date(utc)}, {utc:%H:%M} UTC"
    local = drawn_at.astimezone(local_zone) if local_zone is not None else utc
    name = getattr(local_zone, "key", None)
    if (name or local.tzname()) not in _UTC_NAMES:
        zone = f"{local.tzname()} ({name})" if name and name != local.tzname() else local.tzname()
        when = f"{_long_date(local)}, {local:%H:%M} {zone} | {utc:%H:%M} UTC"
        if local.date() != utc.date():
            when += f" on {_long_date(utc)}"
    if not sky:
        return f"**Date and Time of Reading:** {when}\n"
    return (f"**Date and Time of Reading:** {when}\n"
            f"**Sun and Moon at that Moment:** {sky_line(utc)} (tropical zodiac; context only, "
            f"not used in any score)\n")

_UTC_NAMES = {"UTC", "Etc/UTC", "Etc/GMT", "GMT", "Universal", "Zulu"}

def _long_date(when):
    return f"{when:%A} {when.day} {when:%B %Y}"

_DECAN_POSITION = re.compile(r"\bDecan \d+: ")
_OP_PREFIX = re.compile(r"^\[Op \d+\] ")
# Positions that name a place on the house, sign or decan wheel (Ops 2-4 of the OOTK).
_WHEEL_POSITIONS = {p for key in ("9", "10", "11") for p in SPREADS[key]["positions"]}

def _attribution(data, off):
    """The card's Attribution line value, less what `off` leaves out, or None for no line.
    A court's is "Fire of Water - 20° Gemini to 20° Cancer": its elemental combination, then
    its zodiac span; a numbered pip's and a Major's are astrology ("Saturn in Leo", "Aries");
    an Ace's ("Root of the Powers of Fire") is neither, so it always stays."""
    text = data.get("attribution")
    if data.get("arcana_type") == "Court":
        combo, _, span = (text or "").partition(" - ")
        parts = [p for p, key in ((combo, "courts"), (span, "astrology")) if p and key not in off]
        return " - ".join(parts) or None
    if "astrology" in off and not str(data.get("title", "")).startswith("Ace"):
        return None
    return text

def _cards_md(spread_results, legend, off=frozenset()):
    md = "CARD-BY-CARD CORRESPONDENCE MATRIX\n\n"
    if "tree" not in off and any(item["card_data"]["arcana_type"] == "Minor" for item in spread_results):
        if "geometry" in off:
            md += ("Minor (pip) cards sit on the same Sephira in every mapping system, so their "
                   "entries name the Sephira once.\n\n")
        else:
            md += ("Minor (pip) cards sit on the same Sephira in every mapping system and are nodal "
                   "Sephira points on the Cube of Space, so their entries name the Sephira once "
                   "and leave out the spatial dimension.\n\n")
    if "hebrew" not in off and any(item["card_data"]["arcana_type"] == "Court" for item in spread_results):
        md += ("Court cards take their Hebrew letter through their sign (a Princess through her "
               "element), a Golden Dawn and Thoth practice. The French/Egyptian system gives "
               "courts no path letter, so `none` there is by design, not missing data.\n\n")
    if "astrology" not in off and any(item["card_data"]["arcana_type"] == "Minor"
                                      and planet_dignity_note(item["card_data"].get("attribution"))
                                      for item in spread_results):
        md += ("Planet Strength is the classical dignity of a pip's planet in its sign, as Crowley "
               "reads the small cards; pips without the line have none.\n\n")
    names = [_OP_PREFIX.sub("", item["position_name"]) for item in spread_results]
    if any(name in _WHEEL_POSITIONS for name in names):
        md += ("A house, sign or decan position's name is the place on the wheel, not the card: "
               "the card that fell there is the Card Drawn, and it usually does not belong to that "
               "house, sign or decan" + (" (the Own-Place Check in the header counts the ones that do)."
                                          if "astrology" not in off else "."))
        if any(_DECAN_POSITION.search(name) for name in names):
            md += (" A decan's name ends with its own pip in brackets, for example \"Saturn in "
                   "Leo (5 of Wands)\"; that pip is part of the place's name too.")
        md += "\n\n"
    if len({operation_number(item["position_name"]) for item in spread_results}) > 1:
        md += ("Each operation is dealt from its own fresh shuffle of the whole deck, so a card "
               "can appear in more than one operation, but never twice in the same one.\n\n")

    for item in spread_results:
        data = item["card_data"]
        letter_val = data.get('hebrew_letter')
        letter_str = f" ({letter_val})" if letter_val and letter_val != 'N/A' and "hebrew" not in off else ""

        gd_letter = data.get('gd_hebrew_letter') or 'N/A'
        thoth_letter = data.get('thoth_hebrew_letter') or gd_letter
        french_letter = data.get('french_hebrew_letter') or 'N/A'
        if data['arcana_type'] == 'Court' and french_letter == 'N/A':
            french_letter = 'none'
        minor = data['arcana_type'] == 'Minor'

        md += f"### Position {item['position_number']}: {item['position_name']}\n"
        md += f"- **Card Drawn**: {data['title']}\n"
        md += f"- **Arcana/Suit**: {data['arcana_type']} | {data['suit'] or 'N/A'}\n"
        md += _place_line(data, letter_str, off)
        attribution = _attribution(data, off)
        if attribution:
            md += f"- **Attribution**: {attribution}\n"
        strength = planet_dignity_note(attribution) if minor and "astrology" not in off else None
        if strength:
            md += f"- **Planet Strength**: {strength}\n"
        figure = GEOMANTIC_FIGURES.get(data['attribution']) if data['arcana_type'] == 'Major' else None
        if figure and "geomancy" not in off:
            by = f" (Golden Dawn, by {data['attribution']})" if "astrology" not in off else " (Golden Dawn)"
            md += f"- **Geomantic Figure**: {figure}{by}\n"
        element_note = major_element_note(data) if "elements" not in off else None
        if element_note:
            if "astrology" in off:
                element_note = element_note.split(" (")[0]     # "Earth (Venus via Taurus...)" -> "Earth"
            md += f"- **Element (used in scores)**: {element_note}\n"
        if "hebrew" not in off:
            if minor:
                if gd_letter != letter_val and "tree" not in off:
                    md += f"- **Sephira (both systems)**: `{gd_letter}`\n"
            else:
                md += f"- **Comparative Hebrew Mapping**: Thoth: `{thoth_letter}` | Golden Dawn: `{gd_letter}` | French/Egyptian: `{french_letter}`\n"
        if "geometry" not in off:
            stype, sdim = data.get('spatial_type'), data.get('spatial_dimension')
            if not stype and minor:
                stype, sdim = _MINOR_SPATIAL
            if not (minor and (stype, sdim) == _MINOR_SPATIAL):
                md += f"- **Spatial Dimension**: `{stype or 'N/A'}` ({sdim or 'N/A'})\n"
            solid = data.get('platonic_solid', 'N/A')
            if solid in legend:
                md += f"- **Platonic Solid**: `{solid}`\n"
            else:
                md += f"- **Platonic Topology**: `{solid}` (Faces: {data.get('solid_faces', 'N/A')}, Vertices: {data.get('solid_vertices', 'N/A')}) | Dual: `{data.get('dual_solid', 'N/A')}`\n"
                md += f"- **Topological Role**: {data.get('topological_role', 'N/A')}\n"
        if "tree" not in off and data.get('colour_key_scale') is None:
            md += f"- **King Scale Color**: {data['king_scale_color']}\n"
        md += "\n"
    if "tree" not in off:
        md += liber_777_markdown(spread_results)
    return md

def _row_label(key_scale, name):
    kind = "Sephira" if key_scale <= 10 else "Path"
    return f"{kind} {key_scale} {name}" if name else f"{kind} {key_scale}"

def liber_777_markdown(spread_results):
    """The four Liber 777 colour scales (King, Queen, Prince, Princess) and the Yetziratic
    title of each 777 row the drawn cards use, once per row with the positions on it, so a long
    spread does not repeat them on every card (the OOTK prompt must stay under ~78k characters). The colours come from the King Scale's row (the sign's) and the title
    from the path the card is shown on; under the Thoth swap those differ for the Emperor, the
    Star and their courts, and the table marks which part each of those positions takes."""
    rows = {}                                   # key_scale -> {"label", "colours", "title", "pos"}
    for item in spread_results:
        data, pos = item["card_data"], item["position_number"]
        ck, tk = data.get("colour_key_scale"), data.get("title_key_scale")
        has_colours = any(data.get(k) for k in ("king_scale_color", "queen_scale_color", "prince_scale_color",
                                                "princess_scale_color"))
        parts = []
        if ck is not None and has_colours:
            parts.append((ck, data.get("colour_row_name"), "colours"))
        if tk is not None and data.get("yetziratic_title"):
            parts.append((tk, data.get("title_row_name"), "title"))
        if not parts:
            continue
        both = len({k for k, _, _ in parts}) == 1 and len(parts) == 2
        for key, name, part in parts:
            row = rows.setdefault(key, {"label": _row_label(key, name), "colours": None,
                                        "title": None, "pos": []})
            if part == "colours":
                row["colours"] = (data.get("king_scale_color"), data.get("queen_scale_color"), data.get("prince_scale_color"),
                                  data.get("princess_scale_color"))
            else:
                row["title"] = data.get("yetziratic_title")
            mark = "" if both else f" ({part})"
            if both and part == "title":
                continue                        # listed once, under colours
            if f"{pos}{mark}" not in row["pos"]:
                row["pos"].append(f"{pos}{mark}")
    if not rows:
        return ""
    split = any("(" in p for row in rows.values() for p in row["pos"])
    md = ("**Liber 777 Rows:** each card's four colour scales and Yetziratic title (Sepher "
          "Yetzirah, 32 Paths of Wisdom), given once per 777 row with the positions on it. The four "
          "scales go with the four worlds and court ranks: King (Atziluth), Queen (Briah), Prince or "
          "Emperor (Yetzirah), Princess or Empress (Assiah). A court takes the row of its sign or "
          "element, as its letter does.")
    if split:
        md += (" A position marked (colours) takes only the colours from that row, one marked (title) "
               "only the title: the colours follow the sign and the title follows the card's path.")
    md += ("\n\n| 777 Row | Yetziratic Title | King Scale | Queen Scale | Prince Scale | Princess Scale | Positions |\n"
           "|---|---|---|---|---|---|---|\n")
    for key in sorted(rows):
        row = rows[key]
        scales = " | ".join(c or "" for c in (row["colours"] or ("",) * 4))
        md += (f"| {row['label']} | {row['title'] or ''} | {scales} | "
               f"{', '.join(row['pos'])} |\n")
    return md + "\n"

def _place_line(data, letter_str, off):
    """The card's place on the Tree with its letter: a pip's Sephira, a Major's path, a court's
    letter (named through its sign). With the Tree left out a Major or court keeps only its
    letter, and a pip (whose letter is its Sephira's name) has no line; with the letters left
    out a court has none."""
    kind = data['arcana_type']
    tree, hebrew = "tree" not in off, "hebrew" not in off
    if kind == "Court":
        if not hebrew:
            return ""
        label = _path_label(data) if "astrology" not in off else "Hebrew Letter"
        return f"- **{label}**: {data['path_or_sephira']}{letter_str}\n"
    if tree:
        return f"- **{_path_label(data)}**: {data['path_or_sephira']}{letter_str}\n"
    if kind == "Major" and hebrew and letter_str:
        return f"- **Hebrew Letter**: {letter_str.strip(' ()')}\n"
    return ""

def _elements_md(spread_results, element_counts, withheld, book_t=None, off=frozenset()):
    total_cards = sum(element_counts.values()) or 1
    md = "ELEMENTAL VECTOR DISTRIBUTION\n"
    secondary = spirit_bearing_cards(spread_results)
    if "elements" in off:
        md += _left_out("elements")
        element_counts = {}
    for elem, count in element_counts.items():
        if elem == "Spirit" and not count:
            # Every card counts under one of the four elements, so Spirit is only ever a
            # secondary quality: name those cards instead of printing an empty 0% row.
            if secondary:
                cards = ", ".join(f"Pos {p} ({t})" for p, t in secondary)
                md += f"* **Spirit**: secondary quality only, on {len(secondary)}: {cards}\n"
            continue
        pct = (count / total_cards) * 100
        bar = "█" * int(count * 2)
        line = f"* **{elem:6s}**: {bar} {count} ({pct:.1f}%)"
        if elem == "Spirit" and secondary:
            cards = ", ".join(f"Pos {p} ({t})" for p, t in secondary)
            line += f" | secondary on {len(secondary)}: {cards}"
        md += line + "\n"
    if book_t:
        md += book_t_markdown(book_t)
    if withheld:
        md += withheld_markdown(withheld, off)
    return md

def book_t_notes(spread_results, ops):
    """{operation name: Markdown} for each Book T operation read: where the Significator
    fell, the Count and any card left over from the pairs (see book_t.positions)."""
    read = [o for o in ops if o["status"] != "abandoned"]
    notes = {}
    for o, (_, start, _end, name) in zip(read, spread_segments(spread_results, BOOK_T_KEY)):
        def pos(k):
            item = spread_results[start + k]
            return f"Pos {item['position_number']} ({item['card_data']['title']})"
        steps = " → ".join(f"{pos(k)} [{count_value(spread_results[start + k]['card_data'])}]"
                           for k in o["chain_at"])
        end = (f"; the next count lands on {pos(o['stop_at'])} again, so the count stops"
               if o["stop_at"] is not None else
               "; the last card counts round the whole pile back to itself, so the count stops")
        md = (f"{status_line(o)}\n\n**Count** (towards the {o['direction']}, numbers in brackets): "
              f"{steps}{end}.\n")
        if o["leftover_at"] is not None:
            md += f"\n{pos(o['leftover_at'])} is left over after pairing and is read on its own.\n"
        notes[name] = md
    return notes

_COUNT_WORDS = {3: "Three", 4: "Four"}

def _plural(n, one, many):
    return f"{n} {one if n == 1 else many}"

def book_t_markdown(book_t):
    """The Book T counts (analysis.book_t_counts) as lines under the element counts."""
    md = ("\n**Book T Counts** (Book T reads three or four cards of one rank, and a lead of "
          "Trumps, court cards, Aces or one suit; suits count the small and court cards):\n")
    for seg in book_t:
        line = (f"{_plural(seg['total'], 'card', 'cards')}: {_plural(seg['majors'], 'Trump', 'Trumps')}, "
                f"{_plural(seg['courts'], 'court card', 'court cards')}, {_plural(seg['aces'], 'Ace', 'Aces')} | "
                + ", ".join(f"{suit} {n}" for suit, n in seg["suits"].items()))
        kinds = [f"{_COUNT_WORDS.get(n, n)} {rank} ({', '.join(suits)})" for rank, n, suits in seg["kinds"]]
        line += " | " + ("; ".join(kinds) if kinds else "no rank three or more times")
        name = (seg["segment_name"] or "").split(":")[0]     # "Operation 2: OOTK - ..." -> "Operation 2"
        md += f"* {name + ': ' if name else ''}{line}\n"
    return md

def _hebrew_md(spatial_dist, off=frozenset(), spread_results=()):
    # Totals only: each card's letter and spatial type are in its section 1 entry.
    md = "HEBREW LETTER SPATIAL DIMENSIONS (Sefer Yetzirah / Cube of Space)\n"
    gone = [k for k in ("hebrew", "geometry") if k in off]
    if gone:
        md += _left_out(*gone)
    else:
        md += (f"* **3 Mother Axes (Core Planes)**: `{spatial_dist['Mother_Axis']}`\n"
               f"* **7 Double Directions (Cardinal Faces)**: `{spatial_dist['Double_Direction']}`\n"
               f"* **12 Simple Edges (Polyhedral Boundaries)**: `{spatial_dist['Simple_Edge']}`\n"
               f"* **Nodal Sephiroth Spheres**: `{spatial_dist['Sephira_Point']}`\n"
               f"\nSection {CARDS} gives each card's letter and spatial type.\n")
    if "hebrew" not in off:
        md += _gematria_md(spread_results, off)
    return md

def _gematria_md(spread_results, off):
    """The letter values added up, per operation: plain sums, no meaning given to them."""
    if "gematria" in off:
        return "\n**Letter Values (gematria):**\n" + _left_out("gematria")
    totals = gematria.operation_totals(spread_results)
    if not totals:
        return ""
    md = ("\n**Letter Values (standard gematria, Aleph 1 to Tav 400):** the letters from section "
          f"{CARDS} added up (pips have none). Plain sums to weigh, not a verdict.\n")
    several = len({operation_number(i["position_name"]) for i in spread_results}) > 1
    for op, rows, total in totals:
        parts = " + ".join(f"{letter.split()[0]} {value}" for _, letter, value in rows)
        label = f"Operation {op}" if several else "Total"
        md += f"* **{label}**: {parts} = **{total}**\n"
    return md

def _solids_md(solid_counts, legend, dual_pairings, off=frozenset(), named="in a heap"):
    md = "PLATONIC SOLID TOPOLOGY MATRIX\n"
    if "geometry" in off:
        return md + _left_out("geometry")
    for solid, count in solid_counts.items():
        if count:
            md += f"* **{solid:20s}**: `{count}`\n"
    absent = [s for s, c in solid_counts.items() if not c and s != "Unmapped"]
    if absent:
        md += f"* None drawn: {', '.join(absent)}\n"

    if legend:
        md += f"\n**Solid properties** (fixed for each solid; section {CARDS} names only the card's solid):\n"
        for solid, (faces, vertices, dual, role) in legend.items():
            md += f"* **{solid}**: Faces {faces}, Vertices {vertices} | Dual: `{dual}` | Role: {role}\n"

    if dual_pairings:
        md += "\n**Topological Dual Pairings / Polyhedral Inversions:**\n"
        md += f"These are the pairs scored in section {DIGNITY} ({named}, only its named pairs).\n"
        for dp in dual_pairings:
            md += f"* {dp}\n"
    return md

def _dignity_md(dignity_matrix, book_t_notes=None, off=frozenset()):
    md = "PAIRWISE ELEMENTAL DIGNITY INTERACTIONS\n"
    scored = "elements" not in off
    if not scored and not book_t_notes:
        return md + _left_out("elements")
    if book_t_notes:
        md += ("Book T reads each operation in two passes. The **Count** starts at the Significator "
               "and counts round its pile, each card counting itself as one, and makes the story. "
               "The **Pairs** below it are the cards either side of the Significator, then those "
               "outside them, which fill in what the count leaves out; each pair has its elemental "
               "dignity.\n")
        if not scored:
            md += _left_out("elements") + ("The Count and the Pairs are Book T's method and stay, "
                                           "without their dignity scores.\n")
    if not dignity_matrix:
        return md + "* Only one card was drawn, so there are no pairs to score.\n"
    last_segment = None
    for d in dignity_matrix:
        if d.get("segment_name") and d["segment_name"] != last_segment:
            md += f"\n**{d['segment_name']}**\n\n"
            last_segment = d["segment_name"]
            if book_t_notes and last_segment in book_t_notes:
                md += book_t_notes[last_segment] + "\n**Pairs:**\n"
        md += (f"* **{d['pair']}**: `Score: {_signed(d['score'])}` | {d['relationship']}\n" if scored
               else f"* **{d['pair']}**\n")
    return md

_CROSS_NOTE = ("\n* The Celtic Cross is not a wheel: its places make no angles. Its named pairs "
               "(1 with 2, 3 with 4, 5 with 6, the staff from 7 up to 10, and 1 with 10) are "
               "scored in section {dignity}.\n")

def _is_heap(s):
    return s.get("pair_mode") != "aspect" and s["delta_angle"] is None

def _spatial_md(spatial_matrix, off=frozenset()):
    md = "SPATIAL & GEOMETRIC VECTOR ANALYSIS\n"
    if "geometry" in off:
        return md + _left_out("geometry")
    # A pair touching a centre card has no angle, and a heap's drawing coordinates are not a
    # wheel, so neither says anything about the reading: they are left out.
    shown = [s for s in spatial_matrix or () if s.get("aspect") != "Centre Node"]
    if not spatial_matrix:
        return md + ("* No spatial layout is defined for this spread (or only one card was drawn), "
                     "so no geometric relations were evaluated.\n")
    if not shown:
        return md + (f"* Every pair in this layout meets at the centre card, so no pair makes an angle "
                     f"and there is no geometry to report. The cards' pairs are scored in section {DIGNITY}.\n")
    if any(s.get("pair_mode") == "aspect" for s in shown):
        md += ("\nOn the house, sign and decan wheels the aspect between two positions is "
               "fixed by the layout and is the same in every reading" + (
                   "; the `cards:` part (the elemental dignity of the two cards drawn there) is "
                   "this reading's.\n" if "elements" not in off else ".\n"))
    if any(s.get("pair_mode") == "consecutive" and s["delta_angle"] is not None for s in shown):
        md += ("\nThe aspects below come from where the positions sit in the spread's layout, "
               "not from the cards, so they are the same in every reading of this spread. "
               f"This reading's cards are scored in section {DIGNITY}.\n")
    last_segment = None
    last_aspect = None
    first_in_segment = False
    heaps_noted = set()
    for s in shown:
        if s.get("segment_name") and s["segment_name"] != last_segment:
            md += f"\n**{s['segment_name']}**\n"
            last_segment = s["segment_name"]
            last_aspect = None
            first_in_segment = True
        else:
            first_in_segment = False
        mod_str = _signed(s['score_modifier'])
        if s.get("pair_mode") == "aspect":
            # Ring layouts: pairs are grouped under their aspect, one line per pair.
            if s["aspect"] != last_aspect:
                md += f"\n_{s['aspect']} - {s['description']} [Modifier: `{mod_str}`]_\n\n"
                last_aspect = s["aspect"]
            cards = (f"{_signed(s['card_score'])} {s['card_relationship']}"
                     if "card_score" in s and "elements" not in off else "")
            md += f"* {s['pair']}" + (f" | cards: {cards}" if cards else "") + "\n"
        elif _is_heap(s):
            # One sentence per heap instead of its pairs' drawing distances.
            if last_segment not in heaps_noted:
                heaps_noted.add(last_segment)
                md += (_CROSS_NOTE if s.get("aspect") == "Cross Pair" else
                       "\n* A heap is not a wheel: its cards make no angles. Its named pairs are "
                       "scored in section {dignity}.\n").format(dignity=DIGNITY)
        else:
            md += ("\n" if first_in_segment else "") + f"* **{s['pair']}**:\n"
            md += f"  - Spatial Distance: `{s['distance']}` units | Angular Delta: `{s['delta_angle']}°`\n"
            md += f"  - Geometric Aspect: **{s['aspect']}** ({s['description']}) [Modifier: `{mod_str}`]\n"
    return md

def _instructions_md(query_prompt, mapping_label, macro_framework, spread_results, dignity_matrix,
                     spatial_matrix, solid_counts, dual_pairings, withheld, own_place,
                     significator_places=None, book_t=None, book_t_notes=None, off=frozenset()):
    """What the AI is asked to do. Each rule names only what this reading contains."""
    if "geometry" in off:
        spatial_matrix, dual_pairings = (), None
    operations = len({d["segment_name"] for d in dignity_matrix if d.get("segment_name")})
    aspects = {}
    for s in spatial_matrix or ():
        if s.get("aspect_name"):
            aspects.setdefault(s["aspect_name"], s["score_modifier"])
    solids = [s for s, c in solid_counts.items() if c and s != "Unmapped"]

    if query_prompt:
        # The question doesn't change the draw, only how it is read, so it is worth framing in the
        # terms this spread and framework read in before any card is interpreted.
        lens = re.sub(r"^\d+\.\s*", "", macro_framework)     # "3. Incarnational..." -> "Incarnational..."
        question = ("Relate the reading to the querent's question, given as the Query/Intent Topic "
                    "in the header. Before reading any card, restate it in one or two sentences as "
                    f"an open question framed in this spread's terms: its positions (section {CARDS}) "
                    f"and the {lens} lens. If it asks yes or no, or whether "
                    "something will happen, turn it toward what the querent can understand or do. Keep the "
                    "querent's subject and intent and change only the wording; show the reframed "
                    "question first so the querent can correct it, then read each position as "
                    "answering part of it.")
        summary_answer = " Answer the reframed question directly."
    else:
        question = "No question was given, so describe the forces the reading shows in general."
        summary_answer = ""
    balance = _balance_words(off, solids)
    if len(spread_results) == 1:
        order = (f"Start with the card in section {CARDS} and its correspondences"
                 + (f", then its {balance[1]} (sections {ELEMENTS}-{SOLIDS})." if balance else "."))
    else:
        order = ((f"First the overall balance of {balance[0]} in sections {ELEMENTS}-{SOLIDS}; then each "
                  if balance else "Take each ")
                 + f"position in turn (its name says what it stands for, and section {CARDS} says which "
                 f"card fell there)"
                 + (f"; then the strongest and most strained pairs (section {DIGNITY}"
                    + (f" and the aspects in section {SPATIAL}" if aspects else "") + ")."
                    if "elements" not in off else
                    (f"; then the aspects in section {SPATIAL}." if aspects else ".")))
        if operations > 1:
            order += " Take the operations one at a time, in order, then draw them together."
    if book_t_notes:
        order = (f"Take the operations in order. In each, start with where the Significator falls "
                 f"(the first line under the operation in section {DIGNITY}), then read the Count as "
                 f"the story, then the Pairs to fill in its details. Where an operation says Book T "
                 f"would abandon the divination, say so plainly and weigh that operation lightly. "
                 f"Then draw the operations together"
                 + (f", with the overall balance in sections {ELEMENTS}-{SOLIDS}." if balance else "."))
    notes = []
    if dual_pairings:
        notes.append(f"Section {SOLIDS} lists the neighbouring cards whose solids are duals (polyhedral inversions).")
    if significator_places:
        notes.append("Where the Significator Falls (in the header) is the Golden Dawn's key to each "
                     "operation: read the pack, house, sign or decan it falls in as where the matter turns, "
                     "alongside the cards drawn. It names a place, not a printed card: unless a line "
                     "says the Significator is the card printed there, do not look for it among "
                     "the cards at that place.")
    if own_place:
        notes.append("The Own-Place Check in the header compares the cards on their own place with "
                     "chance; give it weight only where it is marked unusual.")
    if withheld:
        notes.append(f"With so few cards left out, the withheld cards in section {ELEMENTS} say as much "
                     f"as the element counts.")

    rules = [
        ("The question", question),
        ("Use only this data", f"Work from the correspondences listed here, under the {mapping_label} "
                               "system. Do not swap in meanings or attributions from another deck or "
                               "system; if something here looks inconsistent, say so rather than "
                               "correcting it silently."),
        ("Macro Conceptual Framework", f"Read the spread through the lens of **{macro_framework}**."),
        ("Suggested order", " ".join([order] + notes)),
        ("Closing Summary", "Conclude with a summary that draws each part of the reading above "
                            "together, then the outcome they lean toward and which findings point there."
                            + summary_answer + " Offer it as a likely outcome to weigh, not a "
                            "certainty, and leave the decision to the querent."),
        ("Plain-Language Recap", "End with a short recap in simple everyday words, free of technical "
                                 "terms, that someone new to tarot could follow: what the cards "
                                 "show and the likely outcome."),
    ]
    md = ("SYNTHESIS & INTERPRETATION INSTRUCTIONS FOR LLM\n\n"
          "Act as an expert Hermetic scholar and Tarot authority. Interpret the reading from the "
          "calculations above, following these rules:\n\n")
    md += "".join(f"{i}. **{name}:** {text}\n" for i, (name, text) in enumerate(rules, start=1))

    key = []
    if dignity_matrix and "elements" not in off:
        key.append(f"* `Score` in section {DIGNITY}" + (f" (and `cards:` in section {SPATIAL})" if any(
            "card_score" in s for s in spatial_matrix or ()) else "")
                   + f" is the pair's Book T elemental dignity: {_signed(DIGNITY_SAME)} same element (strong), "
                   f"{_signed(DIGNITY_FRIENDLY)} friendly, {DIGNITY_NEUTRAL} neutral (Spirit), "
                   f"{_signed(DIGNITY_CONTRARY)} contrary (ill-dignified: each card weakens the other). "
                   f"As Book T says, each element is contrary only to its opposite (Fire-Water, "
                   f"Air-Earth) and friendly with both others, so Fire-Earth and Air-Water count as "
                   f"fully friendly here, not as the weaker pairs some later writers make them.")
    if aspects:
        named = ", ".join(f"{a} {_signed(m)}" for a, m in
                          sorted(aspects.items(), key=lambda kv: [x.name for x in ASPECTS].index(kv[0])))
        key.append(f"* `Modifier` (section {SPATIAL}) is the weight of the aspect itself ({named}). It "
                   f"describes the two positions, not the cards, and is not added to the dignity score.")
    if "elements" not in off:
        key.append(f"* Section {ELEMENTS} counts each card once, under its primary element."
                   + (" Its Book T Counts are per operation, never across one." if book_t and
                      len(book_t) > 1 else ""))
    elif book_t and len(book_t) > 1:
        key.append(f"* Section {ELEMENTS}'s Book T Counts are per operation, never across one.")
    if book_t_notes:
        key.append("* Counting numbers (Book T): Knights, Queens and Princes 4; Princesses 7; Aces "
                   "11; small cards their own number; Trumps 3 (elements), 9 (planets), 12 (signs). "
                   "Where Book T is silent this site's rules are: " + "; ".join(SITE_RULES.values()) + ".")
    if key:
        md += "\n**How to read the numbers:**\n" + "\n".join(key) + "\n"
    return md

def _balance_words(off, solids):
    """("elements, Cube of Space letters and solids (Cube)", "element, letter and solid") for
    the parts of sections 2-4 this prompt keeps, or None when it keeps none of them."""
    parts = []
    if "elements" not in off:
        parts.append(("elements", "element"))
    if not off & {"hebrew", "geometry"}:
        parts.append(("Cube of Space letters", "letter"))
    if "geometry" not in off:
        parts.append((f"solids ({', '.join(solids) or 'none mapped'})", "solid"))
    if not parts:
        return None
    def join(words):
        return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]
    return join([p for p, _ in parts]), join([w for _, w in parts])

OWN_PLACE_INTRO = ("a card on its own decan (its pip), its own sign (a sign Trump, a pip, or a "
                   "Knight, Queen or Prince by the sign that gives it its letter) or its natural "
                   "house (the house of that sign, Aries = 1st). The chance is exact for a random "
                   "deal from the 78 cards.")

SIGNIFICATOR_PLACES_INTRO = ("Book T's key to each operation, worked out from the shuffle each "
                             "operation was dealt from by laying out the whole deck, not only the "
                             f"cards printed in section {CARDS}. For Operation 1 the deck is cut into four packs for I H V H and "
                             "the pack holding the Significator is named; the printed Operation 1 "
                             "cards are still the 15-card heap")
SIGNIFICATOR_PLACES_DEALT = (". Later operations deal the whole deck round into one pile per house, "
                             f"sign or decan, and section {CARDS} prints only the top card of each "
                             "pile, so the Significator usually lies inside its pile, under the card "
                             "printed there, and is not one of the printed cards. That is expected, "
                             "not a mismatch")

def significator_places_markdown(places):
    if not places:
        return ""
    def where(p):
        if p["op"] == 1:
            return p["place"]
        at = f"position {p['position']}" if p.get("position") else "that place"
        return p["place"] + (f", the Significator is the card printed at {at}" if p["shown"]
                             else f", inside that pile, under the card printed at {at}")
    lines = "".join(f"  * Operation {p['op']}: {where(p)}\n" for p in places)
    dealt = SIGNIFICATOR_PLACES_DEALT if len(places) > 1 else ""
    return f"**Where the Significator Falls:** {SIGNIFICATOR_PLACES_INTRO}{dealt}.\n{lines}"

def own_place_markdown(own_place):
    if not own_place:
        return ""
    lines = "".join(f"  * {c['label']}: {own_place_sentence(c)}\n" for c in own_place)
    return f"**Own-Place Check:** {OWN_PLACE_INTRO}\n{lines}"

def _path_label(data):
    """A court has no place of its own on the Tree: it takes its Hebrew letter through its
    zodiac sign (a Princess through her element), and section 6 says so."""
    if data.get("arcana_type") != "Court":
        return "Path/Sephira"
    sign, _ = card_home(data)
    if sign is not None:
        return f"Letter via Sign ({ZODIAC_SIGNS[sign]})"
    element = SUIT_ELEMENTS.get(str(data.get("suit") or "").lower())
    return f"Letter via Element ({element})" if element else "Path/Sephira"

def _positions(n):
    return f"{n} position{'s' if n != 1 else ''}"

def end_of_prompt_marker(n):
    """The prompt's last line. The top of the prompt names it, so an AI that was handed a
    cut-off copy (an upload or paste limit) can tell, and say so instead of reading on."""
    return f"END OF OOTK PROMPT ({_positions(n)})"

def _signed(n):
    return f"+{n}" if n > 0 else str(n)

def withheld_sentence(withheld):
    """Why the withheld cards matter, with the deck's own element totals."""
    deck = withheld["deck_elements"]
    totals = ", ".join(f"{e} {deck[e]}" for e in ("Fire", "Water", "Air", "Earth") if deck[e])
    n = len(withheld["cards"])
    return (f"Only {n} card{'s' if n != 1 else ''} of the deck stayed out of this draw, so the element "
            f"counts above are the whole deck's ({totals}) minus these. The counts barely move "
            f"between readings; the withheld cards and where each drawn card fell carry the signal.")

def withheld_markdown(withheld, off=frozenset()):
    cards = withheld["cards"]
    md = f"\n### Withheld ({len(cards)} card{'s' if len(cards) != 1 else ''} not drawn)\n"
    for row in cards:
        fields = [derive_primary_element(row) if "elements" not in off else None,
                  _attribution(row, off) or ("N/A" if not off & {"astrology", "courts"} else None),
                  (row.get('platonic_solid') or 'N/A') if "geometry" not in off else None]
        fields = [f for f in fields if f]
        md += f"- **{row['title']}**" + (f": {' | '.join(fields)}" if fields else "") + "\n"
    if "elements" in off:
        return md
    by_elem = ", ".join(f"{e} {c}" for e, c in withheld["elements"].items() if c)
    md += f"\nWithheld by element: {by_elem}. {withheld_sentence(withheld)}\n"
    return md

def generate_html_output(session_id, spread_name, query_prompt, analytical_prompt):
    output_dir = BASE_DIR / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    # A reading the database didn't save has no session number: a timestamp keeps it from
    # overwriting the previous unsaved one.
    name = session_id or f"unsaved_{datetime.now():%Y%m%d-%H%M%S}"
    filename = output_dir / f"ootk_output_{name}.html"
    
    html_analysis = html.escape(analytical_prompt, quote=False)
    safe_spread_name = html.escape(spread_name)
    safe_query = html.escape(query_prompt) if query_prompt else "N/A"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Spread Report - {safe_spread_name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace; background: #121212; color: #e0e0e0; padding: 30px; line-height: 1.6; }}
        h1, h2, h3 {{ color: #6fcf97; }}
        .meta {{ background: #1f1f1f; padding: 20px; border-radius: 8px; border-left: 4px solid #ffe0a0; margin-bottom: 25px; }}
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

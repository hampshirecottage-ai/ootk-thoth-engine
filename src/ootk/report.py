"""Builds the analytical report (Markdown prompt) and its HTML export."""
import html
import re
from datetime import datetime

from ootk import PROJECT_ROOT as BASE_DIR
from ootk.analysis import (
    SUIT_ELEMENTS, analyze_elemental_balance, analyze_hebrew_spatial_distribution,
    analyze_platonic_topology, analyze_spatial_vectors, calculate_elemental_dignities, card_home,
    derive_primary_element, evaluate_macro_framework, own_place_check, own_place_sentence,
    spirit_bearing_cards,
)
from ootk.rules import ASPECTS, DIGNITY_CONTRARY, DIGNITY_FRIENDLY, DIGNITY_NEUTRAL, DIGNITY_SAME
from ootk.spreads import ZODIAC_SIGNS

# The report header and the web form both name the systems from here, so the label always
# says which way the Tzaddi/Heh swap goes (see db.fetch_cards_correspondences).
MAPPING_LABELS = {
    "thoth": "Thoth / Crowley (Liber 777; Emperor on Tzaddi, Star on Heh)",
    "golden_dawn": "Golden Dawn / English System (Emperor on Heh, Star on Tzaddi)",
    "french_egyptian": "French / Egyptian System (Lévi / Papus / Wirth)",
}

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
                    framework="auto", mapping_system="thoth", withheld=None):
    """Every analysis of a drawn spread, then its prompt. The command line and the web site both
    call this, so the same draw always gives the same prompt from either."""
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
    )
    return {
        "element_counts": element_counts, "dignity_matrix": dignity_matrix,
        "spatial_matrix": spatial_matrix, "spatial_dist": spatial_dist,
        "spatial_details": spatial_details, "solid_counts": solid_counts,
        "topology_details": topology_details, "dual_pairings": dual_pairings,
        "macro_framework": macro_framework, "framework_basis": framework_basis,
        "own_place": own_place, "analytical_prompt": analytical_prompt,
    }

# Section numbers, so the notes that point from one section to another stay right if the
# order changes. The cards come first: every later section names positions, and the AI
# reads them better once it knows which card sits where.
CARDS, ELEMENTS, HEBREW, SOLIDS, DIGNITY, SPATIAL = range(1, 7)   # section 7 is the instructions

def build_analytical_prompt(spread_name, query_prompt, significator, seed_val, spread_results, element_counts, dignity_matrix, spatial_matrix, spatial_dist, solid_counts, dual_pairings, macro_framework="3. Incarnational Life Path", mapping_system="thoth", framework_basis=None, withheld=None, own_place=None):
    mapping_label = MAPPING_LABELS.get(mapping_system, mapping_system)
    framework_basis_line = f"**Framework Basis:** {framework_basis}\n" if framework_basis else ""

    end_marker = end_of_prompt_marker(len(spread_results))
    header_md = f"""# HERMETIC ANALYTICAL REPORT & SYSTEM PROMPT
> **Before you start:** this prompt lists {_positions(len(spread_results))} and its very last line is `{end_marker}`. If you cannot see that line, the prompt was cut off: tell the user the last position you can see and that the rest is missing, ask them to send the rest, and do not interpret the reading until you have all of it.

**Operation/Spread:** {spread_name}
**Query/Intent Topic:** {query_prompt or 'General Operation'}
**Significator:** {significator}
**PRNG Seed:** {seed_val or 'Manual Entry'}
**Macro Cabbalistic Framework:** {macro_framework}
{framework_basis_line}{own_place_markdown(own_place)}**Active Mapping System:** {mapping_label}
"""
    legend = _solid_legend(spread_results)
    sections = (                     # in the order of the numbers above
        _cards_md(spread_results, legend),
        _elements_md(spread_results, element_counts, withheld),
        _hebrew_md(spatial_dist),
        _solids_md(solid_counts, legend, dual_pairings),
        _dignity_md(dignity_matrix),
        _spatial_md(spatial_matrix),
        _instructions_md(query_prompt, mapping_label, macro_framework, spread_results, dignity_matrix,
                         spatial_matrix, solid_counts, dual_pairings, withheld, own_place),
    )
    prompt_md = "".join(f"\n---\n\n## {n}. {body}" for n, body in enumerate(sections, start=1))
    prompt_md += f"\n{end_marker}\n"
    # The header keeps the querent's own text exactly as typed.
    return header_md + strip_hebrew_points(prompt_md)

def _cards_md(spread_results, legend):
    md = "CARD-BY-CARD CORRESPONDENCE MATRIX\n\n"
    if any(item["card_data"]["arcana_type"] == "Minor" for item in spread_results):
        md += ("Minor (pip) cards sit on the same Sephira in every mapping system and are nodal "
               "Sephira points on the Cube of Space, so their entries name the Sephira once "
               "and leave out the spatial dimension.\n\n")

    for item in spread_results:
        data = item["card_data"]
        letter_val = data.get('hebrew_letter')
        letter_str = f" ({letter_val})" if letter_val and letter_val != 'N/A' else ""

        gd_letter = data.get('gd_hebrew_letter') or 'N/A'
        thoth_letter = data.get('thoth_hebrew_letter') or gd_letter
        french_letter = data.get('french_hebrew_letter') or 'N/A'

        md += f"### Position {item['position_number']}: {item['position_name']}\n"
        md += f"- **Card Drawn**: {data['title']}\n"
        md += f"- **Arcana/Suit**: {data['arcana_type']} | {data['suit'] or 'N/A'}\n"
        md += f"- **{_path_label(data)}**: {data['path_or_sephira']}{letter_str}\n"
        md += f"- **Attribution**: {data['attribution']}\n"
        minor = data['arcana_type'] == 'Minor'
        if minor:
            if gd_letter != letter_val:
                md += f"- **Sephira (both systems)**: `{gd_letter}`\n"
        else:
            md += f"- **Comparative Hebrew Mapping**: Thoth: `{thoth_letter}` | Golden Dawn: `{gd_letter}` | French/Egyptian: `{french_letter}`\n"
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
        md += f"- **King Scale Color**: {data['king_scale_color']}\n\n"
    return md

def _elements_md(spread_results, element_counts, withheld):
    total_cards = sum(element_counts.values()) or 1
    md = "ELEMENTAL VECTOR DISTRIBUTION\n"
    secondary = spirit_bearing_cards(spread_results)
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
    if withheld:
        md += withheld_markdown(withheld)
    return md

def _hebrew_md(spatial_dist):
    # Totals only: each card's letter and spatial type are in its section 1 entry.
    return ("HEBREW LETTER SPATIAL DIMENSIONS (Sefer Yetzirah / Cube of Space)\n"
            f"* **3 Mother Axes (Core Planes)**: `{spatial_dist['Mother_Axis']}`\n"
            f"* **7 Double Directions (Cardinal Faces)**: `{spatial_dist['Double_Direction']}`\n"
            f"* **12 Simple Edges (Polyhedral Boundaries)**: `{spatial_dist['Simple_Edge']}`\n"
            f"* **Nodal Sephiroth Spheres**: `{spatial_dist['Sephira_Point']}`\n"
            f"\nSection {CARDS} gives each card's letter and spatial type.\n")

def _solids_md(solid_counts, legend, dual_pairings):
    md = "PLATONIC SOLID TOPOLOGY MATRIX\n"
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
        for dp in dual_pairings:
            md += f"* {dp}\n"
    return md

def _dignity_md(dignity_matrix):
    md = "PAIRWISE ELEMENTAL DIGNITY INTERACTIONS\n"
    if not dignity_matrix:
        return md + "* Only one card was drawn, so there are no pairs to score.\n"
    last_segment = None
    for d in dignity_matrix:
        if d.get("segment_name") and d["segment_name"] != last_segment:
            md += f"\n**{d['segment_name']}**\n\n"
            last_segment = d["segment_name"]
        md += f"* **{d['pair']}**: `Score: {_signed(d['score'])}` | {d['relationship']}\n"
    return md

def _is_heap(s):
    return s.get("pair_mode") != "aspect" and s["delta_angle"] is None

def _spatial_md(spatial_matrix):
    md = "SPATIAL & GEOMETRIC VECTOR ANALYSIS\n"
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
               "fixed by the layout and is the same in every reading; the `cards:` part "
               "(the elemental dignity of the two cards drawn there) is this reading's.\n")
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
            cards = f"{_signed(s['card_score'])} {s['card_relationship']}" if "card_score" in s else ""
            md += f"* {s['pair']}" + (f" | cards: {cards}" if cards else "") + "\n"
        elif _is_heap(s):
            # One sentence per heap instead of its pairs' drawing distances.
            if last_segment not in heaps_noted:
                heaps_noted.add(last_segment)
                md += (f"\n* A heap is not a wheel: its cards make no angles. Its named pairs are "
                       f"scored in section {DIGNITY}.\n")
        else:
            md += ("\n" if first_in_segment else "") + f"* **{s['pair']}**:\n"
            md += f"  - Spatial Distance: `{s['distance']}` units | Angular Delta: `{s['delta_angle']}°`\n"
            md += f"  - Geometric Aspect: **{s['aspect']}** ({s['description']}) [Modifier: `{mod_str}`]\n"
    return md

def _instructions_md(query_prompt, mapping_label, macro_framework, spread_results, dignity_matrix,
                     spatial_matrix, solid_counts, dual_pairings, withheld, own_place):
    """What the AI is asked to do. Each rule names only what this reading contains."""
    operations = len({d["segment_name"] for d in dignity_matrix if d.get("segment_name")})
    aspects = {}
    for s in spatial_matrix or ():
        if s.get("aspect_name"):
            aspects.setdefault(s["aspect_name"], s["score_modifier"])
    solids = [s for s, c in solid_counts.items() if c and s != "Unmapped"]

    if query_prompt:
        question = ("Relate the reading to the querent's question, given as the Query/Intent Topic "
                    "in the header.")
    else:
        question = "No question was given, so describe the forces the reading shows in general."
    if len(spread_results) == 1:
        order = (f"Start with the card in section {CARDS} and its correspondences, then its element, "
                 f"letter and solid (sections {ELEMENTS}-{SOLIDS}).")
    else:
        order = (f"First the overall balance of elements, Cube of Space letters and solids "
                 f"({', '.join(solids) or 'none mapped'}) in sections {ELEMENTS}-{SOLIDS}; then each "
                 f"position in turn (its name says what it stands for, and section {CARDS} says which "
                 f"card fell there); then the strongest and most strained pairs (section {DIGNITY}" + (f" and the aspects in section {SPATIAL}" if aspects else "")
                 + ").")
        if operations > 1:
            order += " Take the operations one at a time, in order, then draw them together."
    notes = []
    if dual_pairings:
        notes.append(f"Section {SOLIDS} lists the neighbouring cards whose solids are duals (polyhedral inversions).")
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
                            "together, then the outcome they lean toward and which findings point there. "
                            "Offer it as a likely outcome to weigh, not a certainty, and leave the "
                            "decision to the querent."),
        ("Plain-Language Recap", "End with a short recap in simple everyday words, free of technical "
                                 "terms, that someone new to tarot could follow: what the cards "
                                 "show and the likely outcome."),
    ]
    md = ("SYNTHESIS & INTERPRETATION INSTRUCTIONS FOR LLM\n\n"
          "Act as an expert Hermetic scholar and Tarot authority. Interpret the reading from the "
          "calculations above, following these rules:\n\n")
    md += "".join(f"{i}. **{name}:** {text}\n" for i, (name, text) in enumerate(rules, start=1))

    key = []
    if dignity_matrix:
        key.append(f"* `Score` in section {DIGNITY}" + (f" (and `cards:` in section {SPATIAL})" if any(
            "card_score" in s for s in spatial_matrix or ()) else "")
                   + f" is the pair's Book T elemental dignity: {_signed(DIGNITY_SAME)} same element (strong), "
                   f"{_signed(DIGNITY_FRIENDLY)} friendly, {DIGNITY_NEUTRAL} neutral (Spirit), "
                   f"{_signed(DIGNITY_CONTRARY)} contrary (ill-dignified: each card weakens the other).")
    if aspects:
        named = ", ".join(f"{a} {_signed(m)}" for a, m in
                          sorted(aspects.items(), key=lambda kv: [x.name for x in ASPECTS].index(kv[0])))
        key.append(f"* `Modifier` (section {SPATIAL}) is the weight of the aspect itself ({named}). It "
                   f"describes the two positions, not the cards, and is not added to the dignity score.")
    key.append(f"* Section {ELEMENTS} counts each card once, under its primary element.")
    md += "\n**How to read the numbers:**\n" + "\n".join(key) + "\n"
    return md

OWN_PLACE_INTRO = ("a card on its own decan (its pip), its own sign (a sign Trump, a pip, or a "
                   "Knight, Queen or Prince by the sign that gives it its letter) or its natural "
                   "house (the house of that sign, Aries = 1st). The chance is exact for a random "
                   "deal from the 78 cards.")

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

def withheld_markdown(withheld):
    cards = withheld["cards"]
    md = f"\n### Withheld ({len(cards)} card{'s' if len(cards) != 1 else ''} not drawn)\n"
    for row in cards:
        md += (f"- **{row['title']}**: {derive_primary_element(row)} | {row.get('attribution') or 'N/A'}"
               f" | {row.get('platonic_solid') or 'N/A'}\n")
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

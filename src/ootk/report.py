"""Builds the analytical report (Markdown prompt) and its HTML export."""
import html
import re

from ootk import PROJECT_ROOT as BASE_DIR
from ootk.analysis import derive_primary_element, spirit_bearing_cards

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

def build_analytical_prompt(spread_name, query_prompt, significator, seed_val, spread_results, element_counts, dignity_matrix, spatial_matrix, spatial_dist, spatial_details, solid_counts, topology_details, dual_pairings, macro_framework="3. Incarnational Life Path", mapping_system="thoth", framework_basis=None, withheld=None):
    total_cards = sum(element_counts.values()) or 1
    mapping_label = MAPPING_LABELS.get(mapping_system, mapping_system)
    framework_basis_line = f"**Framework Basis:** {framework_basis}\n" if framework_basis else ""

    end_marker = end_of_prompt_marker(len(spread_results))
    prompt_md = f"""# HERMETIC ANALYTICAL REPORT & SYSTEM PROMPT
> **Before you start:** this prompt lists {_positions(len(spread_results))} and its very last line is `{end_marker}`. If you cannot see that line, the prompt was cut off: tell the user the last position you can see and that the rest is missing, ask them to send the rest, and do not interpret the reading until you have all of it.

**Operation/Spread:** {spread_name}
**Query/Intent Topic:** {query_prompt or 'General Operation'}
**Significator:** {significator}
**PRNG Seed:** {seed_val or 'Manual Entry'}
**Macro Cabbalistic Framework:** {macro_framework}
{framework_basis_line}**Active Mapping System:** {mapping_label}
"""
    header_md = prompt_md
    prompt_md = """
---

## 1. ELEMENTAL VECTOR DISTRIBUTION
"""
    for elem, count in element_counts.items():
        pct = (count / total_cards) * 100
        bar = "█" * int(count * 2)
        line = f"* **{elem:6s}**: {bar} {count} ({pct:.1f}%)"
        if elem == "Spirit":
            secondary = spirit_bearing_cards(spread_results)
            if secondary:
                cards = ", ".join(f"Pos {p} ({t})" for p, t in secondary)
                line += f" | secondary on {len(secondary)}: {cards}"
        prompt_md += line + "\n"

    if withheld:
        prompt_md += withheld_markdown(withheld)

    prompt_md += "\n---\n\n## 2. HEBREW LETTER SPATIAL DIMENSIONS (Sefer Yetzirah / Cube of Space)\n"
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

    legend = _solid_legend(spread_results)
    if legend:
        prompt_md += "\n**Solid properties** (fixed for each solid; section 6 names only the card's solid):\n"
        for solid, (faces, vertices, dual, role) in legend.items():
            prompt_md += f"* **{solid}**: Faces {faces}, Vertices {vertices} | Dual: `{dual}` | Role: {role}\n"

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
    if any(s.get("pair_mode") == "aspect" for s in spatial_matrix or ()):
        prompt_md += ("\nOn the house, sign and decan wheels the aspect between two positions is "
                      "fixed by the layout and is the same in every reading; the `cards:` part "
                      "(the elemental dignity of the two cards drawn there) is this reading's.\n")
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
                cards = f"{_signed(s['card_score'])} {s['card_relationship']}" if "card_score" in s else ""
                prompt_md += f"* {s['pair']}" + (f" | cards: {cards}" if cards else "") + "\n"
            elif s["delta_angle"] is None:
                # Heap layouts: no angle, so every pair shares one aspect; state it once.
                if s["aspect"] != last_aspect:
                    prompt_md += f"\n_{s['aspect']} - {s['description']} [Modifier: `{mod_str}`]_\n\n"
                    last_aspect = s["aspect"]
                prompt_md += f"* **{s['pair']}**: Spatial Distance `{s['distance']}` units\n"
            else:
                prompt_md += ("\n" if first_in_segment else "") + f"* **{s['pair']}**:\n"
                prompt_md += f"  - Spatial Distance: `{s['distance']}` units | Angular Delta: `{s['delta_angle']}°`\n"
                prompt_md += f"  - Geometric Aspect: **{s['aspect']}** ({s['description']}) [Modifier: `{mod_str}`]\n"
    else:
        prompt_md += "* No spatial layout is defined for this spread (or only one card was drawn), so no geometric relations were evaluated.\n"

    prompt_md += "\n---\n\n## 6. CARD-BY-CARD CORRESPONDENCE MATRIX\n\n"
    if any(item["card_data"]["arcana_type"] == "Minor" for item in spread_results):
        prompt_md += ("Minor (pip) cards sit on the same Sephira in every mapping system and are nodal "
                      "Sephira points on the Cube of Space, so their entries name the Sephira once "
                      "and leave out the spatial dimension.\n\n")

    for item in spread_results:
        data = item["card_data"]
        letter_val = data.get('hebrew_letter')
        letter_str = f" ({letter_val})" if letter_val and letter_val != 'N/A' else ""
        
        gd_letter = data.get('gd_hebrew_letter') or 'N/A'
        thoth_letter = data.get('thoth_hebrew_letter') or gd_letter
        french_letter = data.get('french_hebrew_letter') or 'N/A'

        prompt_md += f"### Position {item['position_number']}: {item['position_name']}\n"
        prompt_md += f"- **Card Drawn**: {data['title']}\n"
        prompt_md += f"- **Arcana/Suit**: {data['arcana_type']} | {data['suit'] or 'N/A'}\n"
        prompt_md += f"- **Path/Sephira**: {data['path_or_sephira']}{letter_str}\n"
        prompt_md += f"- **Attribution**: {data['attribution']}\n"
        minor = data['arcana_type'] == 'Minor'
        if minor:
            if gd_letter != letter_val:
                prompt_md += f"- **Sephira (both systems)**: `{gd_letter}`\n"
        else:
            prompt_md += f"- **Comparative Hebrew Mapping**: Thoth: `{thoth_letter}` | Golden Dawn: `{gd_letter}` | French/Egyptian: `{french_letter}`\n"
        stype, sdim = data.get('spatial_type'), data.get('spatial_dimension')
        if not stype and minor:
            stype, sdim = _MINOR_SPATIAL
        if not (minor and (stype, sdim) == _MINOR_SPATIAL):
            prompt_md += f"- **Spatial Dimension**: `{stype or 'N/A'}` ({sdim or 'N/A'})\n"
        solid = data.get('platonic_solid', 'N/A')
        if solid in legend:
            prompt_md += f"- **Platonic Solid**: `{solid}`\n"
        else:
            prompt_md += f"- **Platonic Topology**: `{solid}` (Faces: {data.get('solid_faces', 'N/A')}, Vertices: {data.get('solid_vertices', 'N/A')}) | Dual: `{data.get('dual_solid', 'N/A')}`\n"
            prompt_md += f"- **Topological Role**: {data.get('topological_role', 'N/A')}\n"
        prompt_md += f"- **King Scale Color**: {data['king_scale_color']}\n\n"

    prompt_md += f"""---

## 7. SYNTHESIS & INTERPRETATION INSTRUCTIONS FOR LLM

Act as an expert Hermetic scholar and Tarot authority. Synthesize the above spread matrix following these dynamic rules:

1. **Active System Context ({mapping_label}):** Analyze how the cards function under the `{mapping_system}` mapping.
2. **Hebrew Letter Spatial Geometry & Platonic Topology:** Consider the balance between Mother Axes, Double Directions, Simple Edges, and the active Platonic Solid geometries (Tetrahedron, Cube, Octahedron, Icosahedron, Dodecahedron).
3. **Macro Conceptual Framework Context:** Interpret this spread through the Lens of **{macro_framework}**.
4. **Elemental Dignity & Spatial Geometry Analysis:** Utilize the Pairwise Dignity interactions, Spatial Vector Aspects, and Polyhedral Dual Inversions calculated above.
5. **Closing Summary:** Conclude with a short summary of the key forces the calculations above show. Describe tendencies and tensions between the cards rather than predicting a fixed outcome, and leave the conclusion to the querent.
"""
    # The header keeps the querent's own text exactly as typed.
    prompt_md += f"\n{end_marker}\n"
    return header_md + strip_hebrew_points(prompt_md)

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

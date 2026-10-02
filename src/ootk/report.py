"""Builds the analytical report (Markdown prompt) and its HTML export."""
import html

from ootk import PROJECT_ROOT as BASE_DIR
from ootk.analysis import spirit_bearing_cards

def build_analytical_prompt(spread_name, query_prompt, significator, seed_val, spread_results, element_counts, dignity_matrix, spatial_matrix, spatial_dist, spatial_details, solid_counts, topology_details, dual_pairings, macro_framework="3. Incarnational Life Path", mapping_system="golden_dawn", framework_basis=None):
    total_cards = sum(element_counts.values()) or 1
    mapping_labels = {
        "golden_dawn": "Golden Dawn / English System (Liber 777)",
        "french_egyptian": "French / Egyptian System (Lévi / Papus / Wirth)",
    }
    mapping_label = mapping_labels.get(mapping_system, mapping_system)
    framework_basis_line = f"**Framework Basis:** {framework_basis}\n" if framework_basis else ""

    prompt_md = f"""# HERMETIC ANALYTICAL REPORT & SYSTEM PROMPT
**Operation/Spread:** {spread_name}
**Query/Intent Topic:** {query_prompt or 'General Operation'}
**Significator:** {significator}
**PRNG Seed:** {seed_val or 'Manual Entry'}
**Macro Cabbalistic Framework:** {macro_framework}
{framework_basis_line}**Active Mapping System:** {mapping_label}

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
        if data['arcana_type'] == 'Minor':
            prompt_md += f"- **Sephira (both systems)**: `{gd_letter}`\n"
        else:
            prompt_md += f"- **Comparative Hebrew Mapping**: GD: `{gd_letter}` | French/Egyptian: `{french_letter}`\n"
        stype, sdim = data.get('spatial_type'), data.get('spatial_dimension')
        if not stype and data['arcana_type'] == 'Minor':
            stype, sdim = 'Sephira_Point', 'Nodal Sphere (Sephira)'
        prompt_md += f"- **Spatial Dimension**: `{stype or 'N/A'}` ({sdim or 'N/A'})\n"
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

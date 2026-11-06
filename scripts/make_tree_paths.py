"""Builds static/site/tree-paths.svg, the small Tree of Life animation on the front page.

The 22 paths light up one at a time, from Path 11 (Aleph, The Fool) to Path 32 (Tav, The
Universe), with the Hebrew letter and the Thoth trump shown below. Trumps follow this site's own
table (thoth_cards.key_scale), so The Star is on Path 15 (Heh) and The Emperor on Path 28 (Tzaddi).
The Sephiroth are filled in their Queen Scale colours (Liber 777, the colours the Tree is usually
painted in), with Malkuth quartered citrine, olive, russet and black.

Pure SVG + CSS: no script, no images. Visitors who ask for reduced motion see the still Tree.
Layout matches the Tree in static/js/atlas.js. Run `python scripts/make_tree_paths.py` after
changing anything here.
"""
from ootk import PROJECT_ROOT

OUT = PROJECT_ROOT / "static" / "site" / "tree-paths.svg"

SEPH = [(0, 0), (1, 1), (-1, 1), (1, 2.5), (-1, 2.5), (0, 3.3), (1, 4.6), (-1, 4.6), (0, 5.5), (0, 6.6)]
NAMES = "Kether Chokmah Binah Chesed Geburah Tiphareth Netzach Hod Yesod Malkuth".split()
# Queen Scale hex as stored in the correspondences table (attributions.queen_scale_hex).
QUEEN = ["#FFFFFF", "#808080", "#000000", "#0000FF", "#FF2400", "#FFD700", "#50C878", "#FFA500", "#EE82EE", None]
INK = ["#000", "#fff", "#fff", "#fff", "#fff", "#000", "#000", "#000", "#000", "#fff"]
MALKUTH = [("#E4D00A", "citrine"), ("#808000", "olive"), ("#000000", "black"), ("#80461B", "russet")]  # top, right, bottom, left
PATHS = {11: (1, 2), 12: (1, 3), 13: (1, 6), 14: (2, 3), 15: (2, 6), 16: (2, 4), 17: (3, 6), 18: (3, 5),
         19: (4, 5), 20: (4, 6), 21: (4, 7), 22: (5, 6), 23: (5, 8), 24: (6, 7), 25: (6, 9), 26: (6, 8),
         27: (7, 8), 28: (7, 9), 29: (7, 10), 30: (8, 9), 31: (8, 10), 32: (9, 10)}
LETTERS = "Aleph Beth Gimel Daleth Heh Vav Zain Cheth Teth Yod Kaph Lamed Mem Nun Samekh Ayin Peh Tzaddi Qoph Resh Shin Tav".split()
GLYPHS = "אבגדהוזחטיכלמנסעפצקרשת"
TRUMPS = {11: "The Fool", 12: "The Magus", 13: "The Priestess", 14: "The Empress", 15: "The Star",
          16: "The Hierophant", 17: "The Lovers", 18: "The Chariot", 19: "Lust", 20: "The Hermit",
          21: "Fortune", 22: "Adjustment", 23: "The Hanged Man", 24: "Death", 25: "Art", 26: "The Devil",
          27: "The Tower", 28: "The Emperor", 29: "The Moon", 30: "The Sun", 31: "The Aeon", 32: "The Universe"}

K, OX, OY, R = 34, 80, 18, 8.5      # path unit, centre x, top margin, Sephira radius
W, H = 160, round(OY + 6.6 * K + 52)
STEP = 1.4                           # seconds each path stays lit
CYCLE = STEP * len(PATHS)


def point(n):
    x, y = SEPH[n - 1]
    return OX + x * K * 1.25, OY + y * K


def pct(seconds):
    return f"{seconds / CYCLE * 100:.2f}%"


def sephira(i):
    x, y = point(i + 1)
    if QUEEN[i]:
        disc = f'<circle r="{R}" fill="{QUEEN[i]}"/>'
    else:   # four quarters, each a 90° wedge
        q = R * 0.7071
        corners = [(-q, -q), (q, -q), (q, q), (-q, q)]
        disc = "".join(
            f'<path d="M0 0L{a[0]:.2f} {a[1]:.2f}A{R} {R} 0 0 1 {b[0]:.2f} {b[1]:.2f}Z" fill="{colour}"/>'
            for (colour, _), a, b in zip(MALKUTH, corners, corners[1:] + corners[:1]))
        disc += f'<circle r="{R}" fill="none"/>'
    halo = ' stroke="#000" stroke-width="2" paint-order="stroke"' if i == 9 else ""
    return (f'<g class="s" transform="translate({x:.1f},{y:.1f})"><title>{i + 1}. {NAMES[i]}</title>{disc}'
            f'<text dy="3.2" fill="{INK[i]}"{halo}>{i + 1}</text></g>')


def build():
    css = (
        f".bg{{fill:#2E8A56}}"
        f".p{{stroke:#A7E2C0;stroke-width:1.4;opacity:.35}}"
        f".l{{stroke:#FFE0A0;stroke-width:3.2;stroke-linecap:round;fill:none;stroke-dasharray:1 1;stroke-dashoffset:1;"
        f"opacity:0;animation:draw {CYCLE:.1f}s linear infinite}}"
        f".s circle{{stroke:#0f2a1b;stroke-width:1}}"
        f".s text{{font:700 9px Inter,system-ui,sans-serif;text-anchor:middle}}"
        f".t{{opacity:0;animation:label {CYCLE:.1f}s linear infinite;text-anchor:middle;fill:#FFE0A0}}"
        f".t .g{{font:700 13px serif}}.t .n{{font:600 9px Inter,system-ui,sans-serif}}"
        f"@keyframes draw{{0%{{stroke-dashoffset:1;opacity:1}}{pct(.55)}{{stroke-dashoffset:0;opacity:1}}"
        f"{pct(STEP)}{{stroke-dashoffset:0;opacity:1}}{pct(STEP + .5)}{{stroke-dashoffset:0;opacity:0}}100%{{opacity:0}}}}"
        f"@keyframes label{{0%{{opacity:0}}{pct(.15)}{{opacity:1}}{pct(STEP - .15)}{{opacity:1}}{pct(STEP)}{{opacity:0}}100%{{opacity:0}}}}"
        f"@media (prefers-reduced-motion:reduce){{.l,.t{{animation:none;opacity:0}}}}"
    )
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
           f'<style>{css}</style><rect class="bg" width="{W}" height="{H}" rx="10"/>']
    lines = []
    for p, (a, b) in PATHS.items():
        (x1, y1), (x2, y2) = point(a), point(b)
        lines.append((x1, y1, x2, y2))
        out.append(f'<line class="p" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>')
    for i, (x1, y1, x2, y2) in enumerate(lines):
        out.append(f'<path class="l" pathLength="1" style="animation-delay:{i * STEP:.1f}s" '
                   f'd="M{x1:.1f} {y1:.1f}L{x2:.1f} {y2:.1f}"/>')
    out += [sephira(i) for i in range(10)]
    y = OY + 6.6 * K + 22
    for i, p in enumerate(PATHS):
        out.append(f'<g class="t" style="animation-delay:{i * STEP:.1f}s"><text class="g" x="{W / 2:g}" y="{y:.0f}">{GLYPHS[i]}</text>'
                   f'<text class="n" x="{W / 2:g}" y="{y + 15:.0f}">{p} · {LETTERS[i]} · {TRUMPS[p]}</text></g>')
    return "".join(out) + "</svg>\n"


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")

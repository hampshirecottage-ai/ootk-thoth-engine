"""Builds static/site/front-animation.svg, the small animation on the front page. It cycles
between two scenes, cross-fading from one to the other: the Tree of Life, then the zodiac and
its 36 decans, then the Tree again.

Tree of Life: the 22 paths light up one at a time, from Path 11 (Aleph, The Fool) to Path 32 (Tav, The
Universe), with the Hebrew letter and the Thoth trump shown below. Trumps follow this site's own
table (thoth_cards.key_scale), so The Star is on Path 15 (Heh) and The Emperor on Path 28 (Tzaddi).
The Sephiroth are filled in their Queen Scale colours (Liber 777, the colours the Tree is usually
painted in), with Malkuth quartered citrine, olive, russet and black.

Zodiac: the signs and decans are painted in their King Scale colours (Liber 777, the colours the
zodiac is traditionally painted in): each sign in its letter's colour, each decan in its ruling
planet's. The 36 decans light up one at a time, counter-clockwise from 0° Aries on the left (as on
the Card maps wheel), each with its ruling planet, sign and small card below. Rulers and cards
come from ootk.atlas (Book T: Chaldean order from Mars, the 2 of Wands on Aries 0-10°), so the
animation always agrees with the engine.

Pure SVG + CSS: no script, no images. Every element runs on one shared cycle, so the two scenes
never drift apart. Visitors who ask for reduced motion see the still Tree. Layouts match the
maps in static/js/atlas.js. Run `python scripts/make_front_animation.py` after changing anything
here.
"""
import math

from ootk import PROJECT_ROOT
from ootk.atlas import DECAN_RULERS, SIGNS, decan_pip

OUT = PROJECT_ROOT / "static" / "site" / "front-animation.svg"

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
TREE = STEP * len(PATHS)             # the Tree's run
FADE = 0.8                           # cross-fade between the scenes
Z_STEP = 1.0                         # seconds each decan stays lit
Z0 = TREE + FADE                     # the first decan lights once the wheel has faded in
CYCLE = Z0 + Z_STEP * 36 + FADE      # Tree, fade, 36 decans, fade, and round again

# Zodiac wheel: centre, and the sign and decan rings' inner and outer radii.
CX, CY = 80, 106
SIGN_R, DEC_R = (57, 76), (37, 57)
SIGN_GLYPHS = [g + "\ufe0e" for g in "♈♉♊♋♌♍♎♏♐♑♒♓"]   # text, not emoji
# King Scale hex as stored in the correspondences table (attributions.king_scale_hex) for each
# sign's and planet's path: Aries is Heh (Path 15, scarlet) ... Pisces is Qoph (Path 29, crimson);
# Saturn is Tav (Path 32, indigo), Jupiter Kaph (21, violet), Mars Peh (27, scarlet), the Sun
# Resh (30, orange), Venus Daleth (14, emerald), Mercury Beth (12, yellow), the Moon Gimel (13, blue).
SIGN_KING = ["#FF2400", "#FF4500", "#FFA500", "#FFBF00", "#ADFF2F", "#ADFF2F",
             "#00C957", "#006400", "#0000FF", "#4B0082", "#EE82EE", "#8A2BE2"]
PLANET_KING = {"Saturn": "#4B0082", "Jupiter": "#EE82EE", "Mars": "#FF2400", "Sun": "#FFA500",
               "Venus": "#00C957", "Mercury": "#FFFF00", "Moon": "#0000FF"}


def ink(hex_colour):
    """Dark or light text, whichever reads on this colour."""
    r, g, b = (int(hex_colour[k:k + 2], 16) for k in (1, 3, 5))
    return "#0f2a1b" if 0.299 * r + 0.587 * g + 0.114 * b > 140 else "#fff"


PLANET_GLYPHS = {"Saturn": "♄", "Jupiter": "♃", "Mars": "♂", "Sun": "☉", "Venus": "♀", "Mercury": "☿",
                 "Moon": "☽"}


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
        # the two scenes: the Tree shows for its run, then the wheel, cross-fading each way
        f".sc1{{animation:sc1 {CYCLE:.1f}s linear infinite}}.sc2{{opacity:0;animation:sc2 {CYCLE:.1f}s linear infinite}}"
        f"@keyframes sc1{{0%{{opacity:1}}{pct(TREE)}{{opacity:1}}{pct(TREE + FADE)}{{opacity:0}}"
        f"{pct(CYCLE - FADE)}{{opacity:0}}100%{{opacity:1}}}}"
        f"@keyframes sc2{{0%{{opacity:0}}{pct(TREE)}{{opacity:0}}{pct(TREE + FADE)}{{opacity:1}}"
        f"{pct(CYCLE - FADE)}{{opacity:1}}100%{{opacity:0}}}}"
        # the wheel: rings in the Tree's path colour, a lit decan in the Tree's lit-path cream
        f".zs path,.zd path{{stroke:#0f2a1b;stroke-opacity:.6;stroke-width:.6}}"
        f".zs text{{font:12px serif;text-anchor:middle}}"
        f".zd text{{font:7px serif;text-anchor:middle}}"
        f".zl,.zsl,.zc,.zt{{opacity:0}}"
        f".zl{{animation:dec {CYCLE:.1f}s linear infinite}}.zl path{{fill:#FFE0A0;stroke:#0f2a1b;stroke-width:.8}}"
        f".zl text{{font:700 7px serif;fill:#0f2a1b;text-anchor:middle}}"
        f".zsl{{animation:sign {CYCLE:.1f}s linear infinite}}.zsl path{{fill:none;stroke:#FFE0A0;stroke-width:2.2;stroke-linejoin:round}}"
        f".zc{{animation:sign {CYCLE:.1f}s linear infinite;font:30px serif;fill:#FFE0A0;text-anchor:middle}}"
        f".zt{{animation:zlabel {CYCLE:.1f}s linear infinite;text-anchor:middle;fill:#FFE0A0}}"
        f".zt .g{{font:700 14px serif}}.zt .n{{font:600 9px Inter,system-ui,sans-serif}}"
        f"@keyframes dec{{0%{{opacity:0}}{pct(.2)}{{opacity:1}}{pct(Z_STEP)}{{opacity:1}}{pct(Z_STEP + .5)}{{opacity:0}}100%{{opacity:0}}}}"
        f"@keyframes sign{{0%{{opacity:0}}{pct(.2)}{{opacity:1}}{pct(3 * Z_STEP - .1)}{{opacity:1}}{pct(3 * Z_STEP + .2)}{{opacity:0}}100%{{opacity:0}}}}"
        f"@keyframes zlabel{{0%{{opacity:0}}{pct(.1)}{{opacity:1}}{pct(Z_STEP - .1)}{{opacity:1}}{pct(Z_STEP)}{{opacity:0}}100%{{opacity:0}}}}"
        f"@media (prefers-reduced-motion:reduce){{.l,.t{{animation:none;opacity:0}}.sc1{{animation:none;opacity:1}}"
        f".sc2{{animation:none;display:none}}}}"
    )
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
           f'<style>{css}</style><rect class="bg" width="{W}" height="{H}" rx="10"/><g class="sc1">']
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
    out.append("</g>")
    out += zodiac()
    return "".join(out) + "</svg>\n"


def at(r, deg):
    """A point on the wheel: 0° Aries on the left, the signs running counter-clockwise."""
    a = math.radians(deg)
    return CX - r * math.cos(a), CY + r * math.sin(a)


def sector(r1, r2, a0, a1):
    (x1, y1), (x2, y2), (x3, y3), (x4, y4) = at(r2, a0), at(r2, a1), at(r1, a1), at(r1, a0)
    return (f"M{x1:.1f} {y1:.1f}A{r2} {r2} 0 0 0 {x2:.1f} {y2:.1f}"
            f"L{x3:.1f} {y3:.1f}A{r1} {r1} 0 0 1 {x4:.1f} {y4:.1f}Z")


def glyph(r, deg, text, css=""):
    x, y = at(r, deg)
    return f'<text{css} x="{x:.1f}" y="{y:.1f}" dy="0.35em">{text}</text>'


def zodiac():
    """The second scene: the twelve signs, the 36 decans lighting in turn, and each one's card."""
    out = ['<g class="sc2"><g class="zs">']
    mid_s, mid_d = sum(SIGN_R) / 2, sum(DEC_R) / 2
    for i, sign in enumerate(SIGNS):
        out.append(f'<path fill="{SIGN_KING[i]}" d="{sector(*SIGN_R, i * 30, i * 30 + 30)}"><title>{sign}</title></path>')
        out.append(glyph(mid_s, i * 30 + 15, SIGN_GLYPHS[i], f' fill="{ink(SIGN_KING[i])}"'))
    out.append('</g><g class="zd">')
    for i in range(36):
        colour = PLANET_KING[DECAN_RULERS[i]]
        out.append(f'<path fill="{colour}" d="{sector(*DEC_R, i * 10, i * 10 + 10)}"/>')
        out.append(glyph(mid_d, i * 10 + 5, PLANET_GLYPHS[DECAN_RULERS[i]], f' fill="{ink(colour)}"'))
    out.append("</g>")
    for i in range(12):   # the sign lit for its three decans, with its glyph in the centre
        delay = f' style="animation-delay:{Z0 + i * 3 * Z_STEP:.1f}s"'
        out.append(f'<g class="zsl"{delay}><path d="{sector(SIGN_R[0] - 1, SIGN_R[1] - 1, i * 30, i * 30 + 30)}"/></g>')
        out.append(f'<text class="zc"{delay} x="{CX}" y="{CY}" dy="0.35em">{SIGN_GLYPHS[i]}</text>')
    y = CY + SIGN_R[1] + 26
    for i in range(36):
        delay = f' style="animation-delay:{Z0 + i * Z_STEP:.1f}s"'
        ruler, sign = DECAN_RULERS[i], SIGNS[i // 3]
        suit, n = decan_pip(i)
        out.append(f'<g class="zl"{delay}><path d="{sector(*DEC_R, i * 10, i * 10 + 10)}"/>'
                   f'{glyph(sum(DEC_R) / 2, i * 10 + 5, PLANET_GLYPHS[ruler])}</g>')
        out.append(f'<g class="zt"{delay}><text class="g" x="{W / 2:g}" y="{y:.0f}">'
                   f'{PLANET_GLYPHS[ruler]}\ufe0e in {SIGN_GLYPHS[i // 3]}</text>'
                   f'<text class="n" x="{W / 2:g}" y="{y + 15:.0f}">{ruler} in {sign} · {i % 3 * 10}–{i % 3 * 10 + 10}°</text>'
                   f'<text class="n" x="{W / 2:g}" y="{y + 28:.0f}">{n} of {suit}</text></g>')
    out.append("</g>")
    return out


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")

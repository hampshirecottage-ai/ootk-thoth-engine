"""Builds static/site/wheel-aspects.svg, the animation of the aspects on a wheel on the How it
works page (templates/method.html, "Position in the layout").

A twelve-position wheel (the twelve signs, as on the front page) shows each kind of aspect in
turn, drawing every pair of positions that stands in it, then all of them together:

    Opposition 180° (-1), Square 90° (-2), Trine 120° (+2), Sextile 60° (+1)

The pairs and scores come from the engine itself (ootk.analysis._ring_pairs for the twelve
signs layout), and the colours are the report's (ootk.visual.ASPECT_COLORS), so the animation
always matches what a reading reports. The point it makes: the aspects belong to the wheel,
so they are the same in every reading; only the cards at their two ends change.

Same look as scripts/make_front_animation.py, whose colours and glyphs it reuses. Pure SVG +
CSS: no script. Visitors who ask for reduced motion see every aspect at once, still. Run
`python scripts/make_aspects_animation.py` after changing anything here.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_front_animation import SIGN_GLYPHS, SIGN_KING, ink  # noqa: E402

from ootk import PROJECT_ROOT  # noqa: E402
from ootk.analysis import _ring_pairs  # noqa: E402
from ootk.rules import ASPECTS_BY_NAME  # noqa: E402
from ootk.visual import ASPECT_COLORS  # noqa: E402

OUT = PROJECT_ROOT / "static" / "site" / "wheel-aspects.svg"

W, H = 160, 294
CX, CY = 80, 114
R_OUT, R_IN = 74, 54                  # the sign ring
R_CHORD = R_IN - 2                    # chords run between points just inside it
CREAM, INK, LINE = "#FFE0A0", "#0f2a1b", "#A7E2C0"
KINDS = ("Opposition", "Square", "Trine", "Sextile")
EACH = 0.22                           # seconds between chords
HOLD = 2.6                            # a kind stays this long once drawn
ALL_HOLD = 4.0                        # every aspect together
FADE = 0.5


def at(r, deg):
    """0° Aries on the left, counter-clockwise, as on the front-page wheel."""
    a = math.radians(deg)
    return CX - r * math.cos(a), CY + r * math.sin(a)


def sector(r1, r2, a0, a1):
    (x1, y1), (x2, y2), (x3, y3), (x4, y4) = at(r2, a0), at(r2, a1), at(r1, a1), at(r1, a0)
    return (f"M{x1:.1f} {y1:.1f}A{r2} {r2} 0 0 0 {x2:.1f} {y2:.1f}"
            f"L{x3:.1f} {y3:.1f}A{r1} {r1} 0 0 1 {x4:.1f} {y4:.1f}Z")


def signed(n):
    return f"+{n}" if n > 0 else f"−{-n}"


def build():
    pairs = _ring_pairs("10", 12)
    assert len(pairs) == 42, "twelve positions make 6 oppositions and 12 each of the rest"
    rules, out, caps = [], [], []
    t = 0.4

    def timed(cls, on, off):
        rules.append((cls, on, off))
        return cls

    def chord(cls, a, b, kind, width):
        (x1, y1), (x2, y2) = at(R_CHORD, a * 30 + 15), at(R_CHORD, b * 30 + 15)
        return (f'<path class="{cls}" pathLength="1" stroke="{ASPECT_COLORS[kind]}" stroke-width="{width}" '
                f'd="M{x1:.1f} {y1:.1f}L{x2:.1f} {y2:.1f}"/>')

    def cap(cls, on, off, title, line, line2):
        timed(cls, on, off)
        caps.append(f'<g class="cap {cls}"><text class="h" x="{W / 2}" y="222">{title}</text>'
                    f'<text class="n" x="{W / 2}" y="238">{line}</text>'
                    f'<text class="n" x="{W / 2}" y="250">{line2}</text></g>')

    for kind in KINDS:
        mine = [p for p in pairs if p[4] == kind]
        aspect = ASPECTS_BY_NAME[kind]
        end = t + EACH * len(mine) + HOLD
        for i, p in enumerate(mine):
            out.append(chord(f"d {timed(f'{kind[:3].lower()}{i}', t + EACH * i, end)}", p[0], p[1], kind, 1.8))
        cap(f"c{kind[:3].lower()}", t, end, f"{kind} · {aspect.angle:g}°",
            f"scores {signed(aspect.score)}", f"{len(mine)} pairs on a wheel of twelve")
        t = end + FADE
    out.append(f'<g class="{timed("all", t, t + ALL_HOLD)}">'   # every aspect at once, thinner
               + "".join(chord("e", p[0], p[1], p[4], 1.1) for p in pairs) + "</g>")
    cap("call", t, t + ALL_HOLD, "Every wheel aspect", f"{len(pairs)} pairs, the same in every reading:",
        "only the cards at their ends change")
    cycle = t + ALL_HOLD + FADE

    def pct(s):
        return f"{max(0.0, min(s, cycle)) / cycle * 100:.2f}%"

    anim = []
    for cls, on, off in rules:
        dash = cls not in ("all",) and not cls.startswith("c")
        if dash:   # a chord drawn along its length, held, then gone
            frames = (f"0%{{opacity:0;stroke-dashoffset:1}}{pct(on - .01)}{{opacity:0;stroke-dashoffset:1}}"
                      f"{pct(on)}{{opacity:1;stroke-dashoffset:1}}{pct(on + .5)}{{opacity:1;stroke-dashoffset:0}}"
                      f"{pct(off)}{{opacity:1;stroke-dashoffset:0}}{pct(off + FADE)}{{opacity:0;stroke-dashoffset:0}}"
                      f"100%{{opacity:0;stroke-dashoffset:0}}")
        else:
            frames = (f"0%{{opacity:0}}{pct(on - .01)}{{opacity:0}}{pct(on + .3)}{{opacity:1}}"
                      f"{pct(off)}{{opacity:1}}{pct(off + FADE)}{{opacity:0}}100%{{opacity:0}}")
        anim.append(f".{cls}{{animation:{cls} {cycle:.1f}s linear infinite}}@keyframes {cls}{{{frames}}}")

    ring = []
    for i in range(12):
        ring.append(f'<path class="sg" fill="{SIGN_KING[i]}" d="{sector(R_IN, R_OUT, i * 30, i * 30 + 30)}"/>')
        x, y = at((R_IN + R_OUT) / 2, i * 30 + 15)
        ring.append(f'<text class="gl" x="{x:.1f}" y="{y:.1f}" dy="0.35em" style="fill:{ink(SIGN_KING[i])}">{SIGN_GLYPHS[i]}</text>')
        x, y = at(R_CHORD, i * 30 + 15)
        ring.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.8"/>')

    css = (
        f".bg{{fill:#2E8A56}}text{{text-anchor:middle;fill:{CREAM}}}"
        f".sg{{stroke:{INK};stroke-opacity:.6;stroke-width:.6}}.gl{{font:12px serif}}"
        f"circle{{fill:{CREAM}}}.hub{{fill:{INK};fill-opacity:.18;stroke:{LINE};stroke-opacity:.35}}"
        f".d,.e{{fill:none;stroke-linecap:round}}.d{{stroke-dasharray:1 1;opacity:0}}"
        f".cap,.all{{opacity:0}}"
        f".t{{font:600 8px Inter,system-ui,sans-serif;fill:{LINE}}}"
        f".h{{font:700 11px Inter,system-ui,sans-serif}}.n{{font:600 8px Inter,system-ui,sans-serif}}"
        + "".join(anim)
        + "@media (prefers-reduced-motion:reduce){*{animation:none!important}.all,.call{opacity:1!important}}"
    )
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
            f'<style>{css}</style><rect class="bg" width="{W}" height="{H}" rx="10"/>'
            f'<text class="t" x="{W / 2}" y="18">Aspects on a wheel</text>'
            f'<circle class="hub" cx="{CX}" cy="{CY}" r="{R_IN}"/>'
            + "".join(ring) + "".join(out) + "".join(caps)
            + f'<text class="t" x="{W / 2}" y="278">They belong to the wheel, not the cards</text></svg>\n')


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")

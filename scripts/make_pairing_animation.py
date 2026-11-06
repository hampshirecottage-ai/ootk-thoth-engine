"""Builds static/site/neighbour-pairing.svg, the animation of how neighbouring cards are paired on
the How it works page (templates/method.html, "Element", step "Neighbours are paired").

Four spreads in turn, each drawing the pairs the engine scores by element:

    a row (the Triad)          each card with the next
    a full wheel (12 houses)   each with the next, and the twelfth back to the first
    the Tree of Life           the Sephiroth that a path joins (Binah and Chesed share none)
    the Celtic Cross           its named pairs, not the order they were dealt in

The pairs come from the engine itself (ootk.analysis.segment_pairs), and the Celtic Cross is
drawn from its own layout (SPREAD_DEFAULT_COORDINATES), so the animation always matches the
report. Book T's pairing outwards from the significator has its own animation
(scripts/make_counting_animation.py).

Same look as the other animations; reuses the aspects animation's keyframes. Pure SVG + CSS:
no script. Visitors who ask for reduced motion see the Tree's pairs, still. Run
`python scripts/make_pairing_animation.py` after changing anything here.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_aspects_animation import keyframes  # noqa: E402
from make_front_animation import QUEEN, SEPH, ink  # noqa: E402

from ootk import PROJECT_ROOT  # noqa: E402
from ootk.analysis import segment_pairs  # noqa: E402
from ootk.spreads import SPREAD_DEFAULT_COORDINATES  # noqa: E402

OUT = PROJECT_ROOT / "static" / "site" / "neighbour-pairing.svg"

W, H = 160, 294
CREAM, INK, LINE = "#FFE0A0", "#0f2a1b", "#A7E2C0"
LINK = 0.35          # seconds between links
HOLD = 2.4           # a spread stays this long once its links are drawn
FADE = 0.5
CW, CH = 13, 18      # card size


def card(x, y, label, fill=CREAM):
    return (f'<rect class="cd" x="{x - CW / 2:.1f}" y="{y - CH / 2:.1f}" width="{CW}" height="{CH}" rx="2" fill="{fill}"/>'
            f'<text class="l" x="{x:.1f}" y="{y:.1f}" dy="0.35em" style="fill:{ink(fill)}">{label}</text>')


def fit(coords, box=(18, 44, 142, 196)):
    """Coordinates (y up) scaled into the box, keeping their shape, centred."""
    xs, ys = [x for x, _ in coords], [y for _, y in coords]
    x0, y0, x1, y1 = box
    s = min((x1 - x0) / ((max(xs) - min(xs)) or 1), (y1 - y0) / ((max(ys) - min(ys)) or 1))
    mx, my = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    return [((x0 + x1) / 2 + (x - mx) * s, (y0 + y1) / 2 - (y - my) * s) for x, y in coords]


def build():
    timed, out, caps = [], [], []
    t = 0.3
    scenes = [
        ("3", "A row", "Each card with the next", fit([(-1, 0), (0, 0), (1, 0)], (26, 110, 134, 130)), None),
        ("9", "A full wheel", "Each with the next, and the", None, "twelfth back to the first"),
        ("7", "The Tree of Life", "The Sephiroth a path joins", fit([(x, -y) for x, y in SEPH], (40, 36, 120, 200)),
         "Binah and Chesed share none"),
        ("14", "The Celtic Cross", "Its named pairs, not the", fit(SPREAD_DEFAULT_COORDINATES["14"], (14, 50, 146, 196)),
         "order the cards were dealt"),
    ]
    for n_scene, (key, title, line, pts, line2) in enumerate(scenes):
        n = {"3": 3, "9": 12, "7": 10, "14": 10}[key]
        if pts is None:   # the wheel: the 1st house on the left, counter-clockwise, as in a chart
            pts = [(80 - 60 * math.cos(math.radians(k * 30 + 15)), 118 + 60 * math.sin(math.radians(k * 30 + 15)))
                   for k in range(n)]
        pairs = segment_pairs(key, n)
        end = t + LINK * len(pairs) + HOLD
        g = f"s{n_scene}"
        timed.append((g, t - 0.2, end, False))
        body = []
        for i, (a, b) in enumerate(pairs):
            (x1, y1), (x2, y2) = pts[a], pts[b]
            closing = key == "9" and (a, b) == (n - 1, 0)
            cls = f"{g}l{i}"
            timed.append((cls, t + LINK * i + 0.3, end, True))
            body.append(f'<path class="lk{" cl" if closing else ""} {cls}" pathLength="1" '
                        f'd="M{x1:.1f} {y1:.1f}L{x2:.1f} {y2:.1f}"/>')
        for k, (x, y) in enumerate(pts):
            fill = (QUEEN[k] or "#E4D00A") if key == "7" else CREAM
            body.append(card(x, y, k + 1, fill))
        out.append(f'<g class="sc {g}">{"".join(body)}</g>')
        caps.append(f'<g class="sc {g}"><text class="h" x="{W / 2}" y="232">{n_scene + 1} · {title}</text>'
                    f'<text class="n" x="{W / 2}" y="248">{line}</text>'
                    f'<text class="n" x="{W / 2}" y="260">{line2 or ""}</text></g>')
        t = end + FADE + 0.2
    cycle = t
    css = (
        f".bg{{fill:#2E8A56}}text{{text-anchor:middle;fill:{CREAM}}}"
        f".cd{{stroke:{INK};stroke-width:.7}}.l{{font:700 7px Inter,system-ui,sans-serif}}"
        f".lk{{fill:none;stroke:{CREAM};stroke-width:2;stroke-linecap:round;stroke-dasharray:1 1;opacity:0}}"
        f".lk.cl{{stroke:#fff;stroke-width:2.6}}.sc{{opacity:0}}"
        f".t{{font:600 8px Inter,system-ui,sans-serif;fill:{LINE}}}"
        f".h{{font:700 11px Inter,system-ui,sans-serif}}.n{{font:600 8px Inter,system-ui,sans-serif}}"
        + keyframes(timed, cycle)
        + "@media (prefers-reduced-motion:reduce){*{animation:none!important}.s2,.s2 .lk{opacity:1!important;stroke-dashoffset:0}}"
    )
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
            f'<style>{css}</style><rect class="bg" width="{W}" height="{H}" rx="10"/>'
            f'<text class="t" x="{W / 2}" y="18">Which cards are neighbours</text>'
            + "".join(out) + "".join(caps)
            + f'<text class="t" x="{W / 2}" y="278">Each pair is scored by element</text></svg>\n')


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")

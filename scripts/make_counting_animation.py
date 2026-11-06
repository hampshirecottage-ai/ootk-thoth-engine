"""Builds static/site/book-t-counting.svg, the animation of Book T's counting and pairing on the
How it works page (templates/method.html, "The Book T Opening of the Key").

One worked pile of twelve cards, laid as the report lays a Book T pile: a ring with the
significator at the top and the cards after it going round to the right (clockwise).

    Counting  from the significator, each card counts on by its Book T number, itself
              included, until the count reaches a card already counted.
    Pairing   the cards either side of the significator, then the next two out, and so on;
              a card left over is read on its own.

The count and the pairs are worked out here by the engine itself (ootk.book_t.count_chain and
pair_round), so the animation always shows what a reading does. The example pile is fixed:
the Knight of Wands as significator (he faces right, so the count goes clockwise).

Same look as scripts/make_front_animation.py. Pure SVG + CSS: no script. Visitors who ask
for reduced motion see the finished count and pairs, still. Run
`python scripts/make_counting_animation.py` after changing anything here.
"""
import math

from ootk import PROJECT_ROOT
from ootk.book_t import count_chain, count_value, direction, pair_round

OUT = PROJECT_ROOT / "static" / "site" / "book-t-counting.svg"

# The example pile, significator first, then the cards after him as they lie (clockwise).
PILE = [
    ("Knight of Wands", "Court", "Kn W"), ("VII - The Chariot", "Major", "VII"),
    ("XI - Lust", "Major", "XI"), ("X - Fortune", "Major", "X"),
    ("5 of Swords - Defeat", "Minor", "5 S"), ("XXI - The Universe", "Major", "XXI"),
    ("8 of Cups - Indolence", "Minor", "8 C"), ("Ace of Cups", "Minor", "A C"),
    ("6 of Wands - Victory", "Minor", "6 W"), ("IV - The Emperor", "Major", "IV"),
    ("XX - The Aeon", "Major", "XX"), ("4 of Disks - Power", "Minor", "4 D"),
]
CARDS = [{"title": t, "arcana_type": a} for t, a, _ in PILE]

W, H = 160, 294
CX, CY, R = 80, 112, 50              # ring centre and radius of the card centres
CW, CH = 15, 21                       # card size
CREAM, INK, LINE, PALE = "#FFE0A0", "#0f2a1b", "#A7E2C0", "#d9f2e3"
START = 1.2                           # first hop starts
HOP = 2.2                             # seconds per hop of the count
PAIR = 1.3                            # seconds per pair
GAP = 1.4                             # pause between counting and pairing
HOLD = 2.4                            # the finished picture stays this long
FADE = 0.6


def angle(k, n=len(PILE)):
    """Card k's place: the significator at the top, then clockwise."""
    return 90.0 - k * 360.0 / n


def point(r, deg):
    a = math.radians(deg)
    return CX + r * math.cos(a), CY - r * math.sin(a)


def short(k):
    return PILE[k][2]


def name(k):
    t = PILE[k][0]
    return t.split(" - ", 1)[1] if PILE[k][1] == "Major" else t.split(" - ", 1)[0]


class Timeline:
    """Every timed element gets its own keyframes on the shared cycle (set once all are in)."""

    def __init__(self):
        self.rules = []
        self.cycle = None

    def add(self, cls, on, off=None, draw=False, dim=None):
        self.rules.append((cls, on, off, draw, dim))
        return cls

    def css(self):
        out = []
        c = self.cycle
        p = lambda s: f"{max(0.0, min(s, c)) / c * 100:.2f}%"  # noqa: E731
        for cls, on, off, draw, dim in self.rules:
            end = off if off is not None else c - FADE
            if draw:   # a line drawn along its length, then held
                held = (f"{p(dim)}{{opacity:1}}{p(dim + 0.4)}{{opacity:.35}}{p(end)}{{opacity:.35;stroke-dashoffset:0}}"
                        if dim else f"{p(end)}{{opacity:1;stroke-dashoffset:0}}")
                frames = (f"0%{{opacity:0;stroke-dashoffset:1}}{p(on - 0.01)}{{opacity:0;stroke-dashoffset:1}}"
                          f"{p(on)}{{opacity:1;stroke-dashoffset:1}}"
                          f"{p(on + 0.9)}{{opacity:1;stroke-dashoffset:0}}{held}"
                          f"{p(end + 0.3)}{{opacity:0;stroke-dashoffset:0}}100%{{opacity:0;stroke-dashoffset:0}}")
            else:
                frames = (f"0%{{opacity:0}}{p(on)}{{opacity:0}}{p(on + 0.3)}{{opacity:1}}"
                          f"{p(end)}{{opacity:1}}{p(end + 0.3)}{{opacity:0}}100%{{opacity:0}}")
            out.append(f".{cls}{{animation:{cls} {c:.1f}s linear infinite}}@keyframes {cls}{{{frames}}}")
        return "".join(out)


def arc(r, k0, k1, n=len(PILE)):
    """The clockwise arc outside the ring from card k0 to card k1 (a full turn when k0 == k1)."""
    steps = (k1 - k0) % n or n
    a0, a1 = angle(k0), angle(k0) - steps * 360.0 / n
    (x0, y0) = point(r, a0)
    if steps == n:   # all the way round: two half-circles
        (xm, ym) = point(r, a0 - 180)
        return f"M{x0:.1f} {y0:.1f}A{r} {r} 0 0 1 {xm:.1f} {ym:.1f}A{r} {r} 0 0 1 {x0:.1f} {y0:.1f}"
    (x1, y1) = point(r, a1)
    big = 1 if steps * 360.0 / n > 180 else 0
    return f"M{x0:.1f} {y0:.1f}A{r} {r} 0 {big} 1 {x1:.1f} {y1:.1f}"


def build():
    step_dir = direction(CARDS[0])
    assert step_dir == 1, "the example significator should count clockwise"
    chain, stop = count_chain(CARDS, 0, step_dir)
    pairs, leftover = pair_round(CARDS, 0)
    tl = Timeline()
    out, caps = [], []

    def cap(cls, title, line, on, off, line2=""):
        tl.add(cls, on, off)
        caps.append(f'<g class="cap {cls}"><text class="h" x="{W / 2}" y="232">{title}</text>'
                    f'<text class="n" x="{W / 2}" y="248">{line}</text>'
                    f'<text class="n" x="{W / 2}" y="260">{line2}</text></g>')

    # the ring of cards
    for k in range(len(PILE)):
        x, y = point(R, angle(k))
        fill = CREAM if k == 0 else PALE
        out.append(f'<g><rect x="{x - CW / 2:.1f}" y="{y - CH / 2:.1f}" width="{CW}" height="{CH}" rx="2" '
                   f'fill="{fill}" class="c"/><text class="l" x="{x:.1f}" y="{y:.1f}" dy="0.35em">{short(k)}</text></g>')
    x, y = point(R, angle(0))
    out.append(f'<text class="s" x="{x:.1f}" y="{y - CH / 2 - 4:.1f}">Significator</text>')
    cls = tl.add("lit_s", 0.4)   # the significator is the first card counted
    out.append(f'<g class="{cls}"><circle cx="{x + CW / 2:.1f}" cy="{y - CH / 2:.1f}" r="5"/>'
               f'<text class="b" x="{x + CW / 2:.1f}" y="{y - CH / 2:.1f}" dy="0.35em">1</text></g>')

    # counting: one arc per hop, the landing card lit and numbered
    t = START
    cap("k0", "Counting", f"From the {name(0)},", 0.2, START, "who faces right: clockwise")
    hops = list(zip(chain, chain[1:] + [stop]))
    for h, (a, b) in enumerate(hops):
        cls_arc = tl.add(f"a{h}", t, draw=True, dim=t + HOP)   # earlier hops dim as the next is drawn
        out.append(f'<path class="hop {cls_arc}" pathLength="1" d="{arc(R + CH / 2 + 4 + 3 * h, a, b)}"/>')
        v = count_value(CARDS[a])
        line2 = "back to a counted card: stop" if b == stop else "itself included"
        cap(f"k{h + 1}", f"Counting · step {h + 1}", f"{name(a)} counts {v}", t, t + HOP, line2)
        if b != stop:
            x, y = point(R, angle(b))
            cls = tl.add(f"lit{h}", t + 0.9)
            out.append(f'<g class="{cls}"><rect x="{x - CW / 2:.1f}" y="{y - CH / 2:.1f}" width="{CW}" height="{CH}" '
                       f'rx="2" fill="{CREAM}" class="c on"/><text class="l" x="{x:.1f}" y="{y:.1f}" dy="0.35em">{short(b)}</text>'
                       f'<circle cx="{x + CW / 2:.1f}" cy="{y - CH / 2:.1f}" r="5"/>'
                       f'<text class="b" x="{x + CW / 2:.1f}" y="{y - CH / 2:.1f}" dy="0.35em">{h + 2}</text></g>')
        t += HOP
    cap("k9", "Counting", f"{len(chain)} cards counted:", t, t + GAP, "they tell the story")
    t += GAP

    # pairing: chords across the ring, working outwards from the significator
    for i, (a, b) in enumerate(pairs):
        (x1, y1), (x2, y2) = point(R - CH / 2 - 3, angle(a)), point(R - CH / 2 - 3, angle(b))
        cls = tl.add(f"p{i}", t, draw=True)
        out.append(f'<path class="pair {cls}" pathLength="1" d="M{x1:.1f} {y1:.1f}L{x2:.1f} {y2:.1f}"/>')
        cap(f"q{i}", f"Pairing · pair {i + 1}", f"{name(a)}", t, t + PAIR, f"with {name(b)}")
        t += PAIR
    if leftover is not None:
        x, y = point(R, angle(leftover))
        cls = tl.add("left", t)
        out.append(f'<rect class="lo {cls}" x="{x - CW / 2 - 3:.1f}" y="{y - CH / 2 - 3:.1f}" width="{CW + 6}" '
                   f'height="{CH + 6}" rx="3"/>')
        cap("q9", "Pairing", f"{name(leftover)} is left over:", t, t + PAIR + HOLD, "it is read on its own")
        t += PAIR + HOLD
    tl.cycle = t + FADE

    css = (
        f".bg{{fill:#2E8A56}}"
        f"text{{text-anchor:middle;fill:{CREAM}}}"
        f".c{{stroke:{INK};stroke-width:.7}}.c.on{{stroke-width:1.4}}"
        f".l{{font:700 6.5px Inter,system-ui,sans-serif;fill:{INK}}}"
        f".s{{font:600 7.5px Inter,system-ui,sans-serif;fill:{LINE}}}"
        f".t{{font:600 8px Inter,system-ui,sans-serif;fill:{LINE}}}"
        f".h{{font:700 11px Inter,system-ui,sans-serif}}.n{{font:600 8px Inter,system-ui,sans-serif}}"
        f"circle{{fill:{INK};stroke:{CREAM};stroke-width:.8}}.b{{font:700 6.5px Inter,system-ui,sans-serif}}"
        f".hop{{fill:none;stroke:{CREAM};stroke-width:1.4;stroke-linecap:round;stroke-dasharray:1 1;opacity:0}}"
        f".pair{{fill:none;stroke:#fff;stroke-width:1.6;stroke-linecap:round;stroke-dasharray:1 1;opacity:0}}"
        f".lo{{fill:none;stroke:#fff;stroke-width:1.6;stroke-dasharray:2 2;opacity:0}}"
        f".cap,[class*=lit]{{opacity:0}}"
        + tl.css()
        + "@media (prefers-reduced-motion:reduce){*{animation:none!important}"
        "[class*=lit],.hop,.pair,.lo{opacity:1!important;stroke-dashoffset:0}.q9{opacity:1!important}}"
    )
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
            f'<style>{css}</style><rect class="bg" width="{W}" height="{H}" rx="10"/>'
            f'<text class="t" x="{W / 2}" y="18">Book T · Counting and pairing</text>'
            + "".join(out) + "".join(caps)
            + f'<text class="t" x="{W / 2}" y="278">Example pile of twelve</text></svg>\n')


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")

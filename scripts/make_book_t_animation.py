"""Builds static/site/book-t-operations.svg, the animation of Book T's five operations on the
How it works page (templates/method.html, "The Book T Opening of the Key").

One scene per operation, cross-fading into the next, then round again:

    1  the deck cut into four packs, Yod, Heh, Vau and Heh final, from right to left
    2  dealt into twelve stacks for the houses (1st house on the left, counter-clockwise)
    3  dealt into twelve stacks for the signs, in their King Scale colours
    4  the significator set down with the 36 cards after it in a ring round him
    5  dealt into ten packs laid out as the Tree of Life, in the Sephiroth's Queen Scale colours

Each scene ends by marking the pile the significator falls in, which is the one that is read.
The piles marked are an example only. Pack subjects come from ootk.book_t (Book T's own); the
order and counts follow book_t.py's docstring.

Same look as the front page (scripts/make_front_animation.py), whose colours and glyphs it
reuses. Pure SVG + CSS: no script. Visitors who ask for reduced motion see the first scene,
still. Run `python scripts/make_book_t_animation.py` after changing anything here.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_front_animation import MALKUTH, QUEEN, SEPH, SIGN_GLYPHS, SIGN_KING, ink  # noqa: E402

from ootk import PROJECT_ROOT  # noqa: E402
from ootk.book_t import IHVH_PACKS, OP4_RING, STACKS  # noqa: E402

OUT = PROJECT_ROOT / "static" / "site" / "book-t-operations.svg"

W, H = 160, 294
SCENE = 7.0          # seconds each operation shows
FADE = 0.6           # cross-fade
CYCLE = SCENE * 5
DEAL = 0.6           # first pile appears this long into its scene
DEAL_SPAN = 3.0      # all piles are down this long after that
MARK = 4.6           # the significator's pile is marked at this point in the scene
CX, CY = 80, 120     # centre of the rings
CREAM, INK, LINE = "#FFE0A0", "#0f2a1b", "#A7E2C0"
HEBREW = ["י", "ה", "ו", "ה"]


def pct(seconds):
    return f"{seconds / CYCLE * 100:.2f}%"


def at(r, deg):
    """0° on the left, counter-clockwise, as on the zodiac wheels."""
    a = math.radians(deg)
    return CX - r * math.cos(a), CY + r * math.sin(a)


def delay(t):
    return f' style="animation-delay:{t:.2f}s"'


def card(x, y, w, h, fill=CREAM, extra=""):
    return f'<rect x="{x - w / 2:.1f}" y="{y - h / 2:.1f}" width="{w}" height="{h}" rx="1.5" fill="{fill}"{extra}/>'


def stack(x, y, w, h, fill=CREAM):
    """A small pile: three cards, each a little up and to the right of the last."""
    return "".join(card(x + k, y - k, w, h, fill, ' class="c"') for k in (0, 1.2, 2.4))


def scene(i, title, line, body, mark_text):
    """One operation: its piles (already wrapped in timed groups), then its caption."""
    a = i * SCENE
    return (f'<g class="sc"{delay(a)}>{body}'
            f'<text class="h" x="{W / 2}" y="242">{title}</text>'
            f'<text class="n" x="{W / 2}" y="258">{line}</text>'
            f'<text class="n m pop"{delay(a + MARK)} x="{W / 2}" y="272">{mark_text}</text></g>')


def deal(a, k, n):
    """When pile k of n is laid down in the scene starting at a."""
    return a + DEAL + DEAL_SPAN * k / max(n - 1, 1)


def ring_marker(x, y, r, a):
    return f'<circle class="mk pop"{delay(a + MARK)} cx="{x:.1f}" cy="{y:.1f}" r="{r}"/>'


def op1():
    a, out = 0.0, []
    xs = [128, 96, 64, 32]                      # Yod on the right, Heh final on the left
    for k, (x, pack) in enumerate(zip(xs, IHVH_PACKS)):
        out.append(f'<g class="pop"{delay(deal(a, k, 4))}>{stack(x, CY, 18, 28)}'
                   f'<text class="hb" x="{x}" y="{CY - 30}">{HEBREW[k]}</text>'
                   f'<text class="s" x="{x}" y="{CY + 30}">{pack["letter"].replace(" final", " f.")}</text></g>')
    out.append(ring_marker(xs[0] + 1, CY - 1, 20, a))
    return scene(0, "1 · The four packs", "Cut into four, right to left",
                 "".join(out), "Read the pack it falls in")


def op_ring(i, n, label, fill, title, line):
    a, out, r = i * SCENE, [], 64
    for k in range(n):
        x, y = at(r, k * 360 / n + 360 / n / 2)
        out.append(f'<g class="pop"{delay(deal(a, k, n))}>{stack(x, y, 14, 20, fill(k))}'
                   f'<text class="l" x="{x + 1.2:.1f}" y="{y - 1.2:.1f}" dy="0.35em" style="fill:{ink(fill(k))}">{label(k)}</text></g>')
    mark = 9 if i == 1 else 4                       # e.g. the 10th house, Leo
    x, y = at(r, mark * 360 / n + 360 / n / 2)
    out.append(ring_marker(x + 1.2, y - 1.2, 15, a))
    return scene(i, title, line, "".join(out), "Read the stack it falls in")


def op4():
    a, out, r = 3 * SCENE, [], 62
    out.append(f'<g class="pop"{delay(a + DEAL - 0.4)}>{card(CX, CY, 20, 30)}'
               f'<text class="l" x="{CX}" y="{CY}" dy="0.35em" style="fill:{INK}">S</text></g>')
    for k in range(OP4_RING):                   # the 36 cards after him, round from the top
        x, y = at(r, 270 - k * 10 - 5)
        out.append(f'<g class="pop"{delay(deal(a, k, OP4_RING))}>{card(x, y, 6, 9)}</g>')
    out.append(ring_marker(CX, CY, 21, a))
    return scene(3, "4 · The ring of 36", "The significator, ringed by the next 36",
                 "".join(out), "The whole ring is read")


def op5():
    a, out, k_, oy = 4 * SCENE, [], 27, 36
    pts = [(CX + x * k_ * 1.25, oy + y * k_) for x, y in SEPH]
    for n, (x, y) in enumerate(pts):
        fill = QUEEN[n] or MALKUTH[0][0]
        out.append(f'<g class="pop"{delay(deal(a, n, 10))}>{stack(x, y, 12, 17, fill)}'
                   f'<text class="l" x="{x + 1.2:.1f}" y="{y - 1.2:.1f}" dy="0.35em" style="fill:{ink(fill)}">{n + 1}</text></g>')
    x, y = pts[5]
    out.append(ring_marker(x + 1.2, y - 1.2, 14, a))
    return scene(4, "5 · The ten Sephiroth", "Dealt into ten packs on the Tree",
                 "".join(out), "Read the pack it falls in")


def build():
    assert STACKS == {2: 12, 3: 12, 5: 10} and OP4_RING == 36   # the counts drawn here
    css = (
        f".bg{{fill:#2E8A56}}"
        f".c{{stroke:{INK};stroke-width:.7}}"
        f".sc{{opacity:0;animation:sc {CYCLE:.0f}s linear infinite}}"
        f".pop{{opacity:0;animation:pop {CYCLE:.0f}s linear infinite}}"
        f".mk{{fill:none;stroke:{CREAM};stroke-width:2.2}}"
        f"text{{text-anchor:middle;fill:{CREAM}}}"
        f".h{{font:700 11px Inter,system-ui,sans-serif}}"
        f".n{{font:600 8.5px Inter,system-ui,sans-serif}}.m{{fill:#fff}}"
        f".hb{{font:700 15px serif}}.s{{font:600 8px Inter,system-ui,sans-serif;fill:{LINE}}}"
        f".l{{font:700 8px Inter,system-ui,sans-serif}}"
        f".t{{font:600 8px Inter,system-ui,sans-serif;fill:{LINE}}}"
        f"@keyframes sc{{0%{{opacity:0}}{pct(FADE)}{{opacity:1}}{pct(SCENE - FADE)}{{opacity:1}}{pct(SCENE)}{{opacity:0}}100%{{opacity:0}}}}"
        # a pile appears and stays for a scene's length; its scene has faded out by then
        f"@keyframes pop{{0%{{opacity:0}}{pct(.25)}{{opacity:1}}{pct(SCENE)}{{opacity:1}}{pct(SCENE + .01)}{{opacity:0}}100%{{opacity:0}}}}"
        f"@media (prefers-reduced-motion:reduce){{.sc,.pop{{animation:none}}.sc:first-of-type,.sc:first-of-type .pop{{opacity:1}}}}"
    )
    body = [
        op1(),
        op_ring(1, 12, lambda k: k + 1, lambda k: CREAM, "2 · The twelve houses",
                "Dealt into twelve stacks"),
        op_ring(2, 12, lambda k: SIGN_GLYPHS[k], lambda k: SIGN_KING[k], "3 · The twelve signs",
                "Dealt again into twelve stacks"),
        op4(),
        op5(),
    ]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
            f'<style>{css}</style><rect class="bg" width="{W}" height="{H}" rx="10"/>'
            f'<text class="t" x="{W / 2}" y="18">Book T · Opening of the Key</text>'
            + "".join(body) + "</svg>\n")


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")

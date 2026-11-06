"""Builds static/site/own-place.svg, the animation of the Own-Place Check on the How it works page
(templates/method.html, "Sign, planet and decan").

One example deal of twelve cards onto the twelve signs wheel, Aries to Pisces. The cards are
laid one by one; each shows the sign it belongs to (read from its attribution), or that it has
none, and a card that landed on its own sign is marked "at home". Then the count, what chance
alone would give, and how often a random deal does as well.

The own places, the count and the odds come from the engine itself (ootk.analysis.own_places
and own_place_distribution), so the animation always matches what a reading reports. The deal
is fixed (the cards and attributions as in the database); two of the twelve are at home.

Same look as scripts/make_aspects_animation.py, whose wheel and keyframes it reuses. Pure SVG +
CSS: no script. Visitors who ask for reduced motion see the finished deal, still. Run
`python scripts/make_own_place_animation.py` after changing anything here.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_aspects_animation import CX, CY, R_IN, R_OUT, at, keyframes, sector  # noqa: E402,I001
from make_front_animation import SIGN_GLYPHS, SIGN_KING, ink  # noqa: E402

from ootk import PROJECT_ROOT  # noqa: E402
from ootk.analysis import own_place_distribution, own_places  # noqa: E402

OUT = PROJECT_ROOT / "static" / "site" / "own-place.svg"

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
         "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
# The example deal, one card per sign from Aries: (title, arcana type, attribution, label).
DEAL = [
    ("9 of Wands - Strength", "Minor", "Moon in Sagittarius", "9 W"),
    ("Queen of Disks", "Court", "Water of Earth - 20° Sagittarius to 20° Capricorn", "Q D"),
    ("Princess of Cups", "Court", "Earth of Water - Libra, Scorpio, Sagittarius quadrant", "Ps C"),
    ("XVI - The Tower", "Major", "Mars", "XVI"),
    ("6 of Swords - Science", "Minor", "Mercury in Aquarius", "6 S"),
    ("9 of Disks - Gain", "Minor", "Venus in Virgo", "9 D"),
    ("VIII - Adjustment", "Major", "Libra", "VIII"),
    ("I - The Magus", "Major", "Mercury", "I"),
    ("Prince of Swords", "Court", "Air of Air - 20° Capricorn to 20° Aquarius", "Pr S"),
    ("2 of Cups - Love", "Minor", "Venus in Cancer", "2 C"),
    ("8 of Wands - Swiftness", "Minor", "Mercury in Sagittarius", "8 W"),
    ("3 of Wands - Virtue", "Minor", "Sun in Aries", "3 W"),
]
CARDS = [{"title": t, "arcana_type": a, "card_attribution": attr} for t, a, attr, _ in DEAL]

W, H = 160, 294
CREAM, INK, LINE = "#FFE0A0", "#0f2a1b", "#A7E2C0"
R_CARD = 41                     # card centres, inside the sign ring
CW, CH = 13, 18
START = 0.6
STEP = 1.7                      # seconds per card
HOLD = 5.5                      # the finished deal and its odds
FADE = 0.5


def name(k):
    t, arcana = DEAL[k][0], DEAL[k][1]
    if arcana == "Major":
        return t.split(" - ", 1)[1]
    return t.split(" - ", 1)[0]


def no_home(k):
    arcana, title = DEAL[k][1], DEAL[k][0]
    if arcana == "Major":
        return "a planet Trump: no sign"
    if title.startswith("Princess"):
        return "a Princess: no sign"
    return "an Ace: no sign"


def build():
    homes = [own_places(c, "sign") for c in CARDS]
    hits = [k for k, h in enumerate(homes) if k in h]
    assert hits == [5, 6], hits    # the 9 of Disks on Virgo, Adjustment on Libra
    dist = own_place_distribution("sign", 12)
    expected = sum(j * p for j, p in enumerate(dist))
    chance = sum(dist[len(hits):])

    timed, lines, cards, marks, caps = [], [], [], [], []
    t = START
    end = START + STEP * len(DEAL) + HOLD

    def cap(cls, on, off, title, line, line2):
        timed.append((cls, on, off, False))
        caps.append(f'<g class="cap {cls}"><text class="h" x="{W / 2}" y="222">{title}</text>'
                    f'<text class="n" x="{W / 2}" y="238">{line}</text>'
                    f'<text class="n" x="{W / 2}" y="250">{line2}</text></g>')

    for k in range(len(DEAL)):
        x, y = at(R_CARD, k * 30 + 15)
        timed.append((f"k{k}", t, end, False))
        cards.append(f'<g class="k k{k}"><rect class="cd" x="{x - CW / 2:.1f}" y="{y - CH / 2:.1f}" '
                     f'width="{CW}" height="{CH}" rx="2"/>'
                     f'<text class="l" x="{x:.1f}" y="{y:.1f}" dy="0.35em">{DEAL[k][3]}</text></g>')
        home = next(iter(homes[k]), None)
        if home is not None:   # its own sign outlined while it is shown
            timed.append((f"o{k}", t + 0.4, t + STEP - 0.5, False))
            marks.append(f'<path class="own o{k}" d="{sector(R_IN, R_OUT, home * 30, home * 30 + 30)}"/>')
        if k in hits:
            timed.append((f"m{k}", t + 0.5, end, False))
            marks.append(f'<rect class="hit m{k}" x="{x - CW / 2 - 2:.1f}" y="{y - CH / 2 - 2:.1f}" '
                         f'width="{CW + 4}" height="{CH + 4}" rx="3"/>')
            line2 = "its own sign: at home"
        elif home is not None:   # a line out to the sign it belongs to
            (x2, y2) = at(R_IN - 2, home * 30 + 15)
            cls = f"p{k}"
            timed.append((cls, t + 0.4, t + STEP - 0.5, True))
            lines.append(f'<path class="pt {cls}" pathLength="1" d="M{x:.1f} {y:.1f}L{x2:.1f} {y2:.1f}"/>')
            line2 = f"belongs in {SIGNS[home]}"
        else:
            line2 = no_home(k)
        cap(f"c{k}", t, t + STEP - 0.5, f"{SIGNS[k]} {SIGN_GLYPHS[k]}", name(k), line2)
        t += STEP

    cap("cfin", t, end, f"{len(hits)} of 12 at home", f"chance alone gives {expected:.2f};",
        f"{len(hits)} or more in {chance:.0%} of deals")

    ring = [f'<circle class="hub" cx="{CX}" cy="{CY}" r="{R_IN}"/>']
    for i in range(12):
        ring.append(f'<path class="sg" fill="{SIGN_KING[i]}" d="{sector(R_IN, R_OUT, i * 30, i * 30 + 30)}"/>')
        x, y = at((R_IN + R_OUT) / 2, i * 30 + 15)
        ring.append(f'<text class="gl" x="{x:.1f}" y="{y:.1f}" dy="0.35em" style="fill:{ink(SIGN_KING[i])}">{SIGN_GLYPHS[i]}</text>')

    cycle = end + FADE + 0.3
    css = (
        f".bg{{fill:#2E8A56}}text{{text-anchor:middle;fill:{CREAM}}}"
        f".sg{{stroke:{INK};stroke-opacity:.6;stroke-width:.6}}.gl{{font:12px serif}}"
        f".hub{{fill:{INK};fill-opacity:.18;stroke:{LINE};stroke-opacity:.35}}"
        f".cd{{fill:{CREAM};stroke:{INK};stroke-width:.7}}.l{{font:700 5.5px Inter,system-ui,sans-serif;fill:{INK}}}"
        f".own{{fill:none;stroke:#fff;stroke-width:2;opacity:0}}"
        f".hit{{fill:none;stroke:#fff;stroke-width:1.6;opacity:0}}"
        f".pt{{fill:none;stroke:{CREAM};stroke-width:1.4;stroke-linecap:round;stroke-dasharray:1 1;opacity:0}}"
        f".k,.cap{{opacity:0}}"
        f".t{{font:600 8px Inter,system-ui,sans-serif;fill:{LINE}}}"
        f".h{{font:700 10px Inter,system-ui,sans-serif}}.n{{font:600 8px Inter,system-ui,sans-serif}}"
        + keyframes(timed, cycle)
        + "@media (prefers-reduced-motion:reduce){*{animation:none!important}.k,.hit,.cfin{opacity:1!important}}"
    )
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
            f'<style>{css}</style><rect class="bg" width="{W}" height="{H}" rx="10"/>'
            f'<text class="t" x="{W / 2}" y="18">Cards in their own place</text>'
            + "".join(ring) + "".join(lines) + "".join(cards) + "".join(marks) + "".join(caps)
            + f'<text class="t" x="{W / 2}" y="278">Example deal on the twelve signs</text></svg>\n')


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")

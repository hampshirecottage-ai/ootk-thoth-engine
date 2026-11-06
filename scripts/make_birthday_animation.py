"""Builds static/site/birthday-significator.svg, the animation of how a birthday gives a
significator on the How it works page (templates/method.html, "From your birth date",
"A significator").

The twelve-sign wheel (King Scale colours, as on the front page) with a ring of the twelve
Knights, Queens and Princes inside it, each ruling 21 degrees of one sign to 20 of the next,
as Book T gives them. The court spans are laid round the wheel, then the Sun goes round to two
example birthdays, and the court card whose span it stands in is picked out. It ends on why a
Princess is never given.

The spans and dates come from the engine itself (ootk.significator.BIRTH_SPANS, SPAN_SIGNS and
card_for_birthday), so the animation always gives the card the start page gives. The Sun's
place on a date is read off the span: its first day is 20 degrees of the sign, the next span's
first day 30 degrees on.

Same look as scripts/make_aspects_animation.py, whose wheel and keyframes it reuses. Pure SVG +
CSS: no script. Visitors who ask for reduced motion see the first birthday picked out, still.
Run `python scripts/make_birthday_animation.py` after changing anything here.
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_aspects_animation import CX, CY, R_IN, R_OUT, at, keyframes, sector  # noqa: E402,I001
from make_front_animation import SIGN_GLYPHS, SIGN_KING, ink  # noqa: E402

from ootk import PROJECT_ROOT  # noqa: E402
from ootk.significator import BIRTH_SPANS, MONTHS, SPAN_SIGNS, card_for_birthday  # noqa: E402

OUT = PROJECT_ROOT / "static" / "site" / "birthday-significator.svg"

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
         "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
BIRTHDAYS = [(7, 14), (2, 5)]       # the examples: 14 July, then 5 February
W, H = 160, 294
CREAM, INK, LINE = "#FFE0A0", "#0f2a1b", "#A7E2C0"
R_SPAN = (36, R_IN - 1)             # the court ring, just inside the signs
R_SUN = 27
SPAN_EACH = 0.45                    # seconds between spans
MOVE = 2.6                          # the Sun's journey to a birthday
SHOW = 3.6                          # its card picked out
FADE = 0.5
RANK = {"Knight": "Kn", "Queen": "Q", "Prince": "Pr"}


def short(title):
    rank, suit = title.split(" of ")
    return f"{RANK[rank]} {suit[0]}"


def span_start(i):
    """Degrees from 0 Aries where span i begins: 20 degrees into its sign."""
    return (SIGNS.index(SPAN_SIGNS[i]) * 30 + 20) % 360


def sun_degree(month, day):
    """The Sun's place (degrees from 0 Aries) on a date, read off the span it falls in."""
    d = date(2001, month, day)
    title = card_for_birthday(month, day)
    i = next(n for n, (_, t) in enumerate(BIRTH_SPANS) if t == title)
    first = date(2001, *BIRTH_SPANS[i][0])
    nxt = date(2001, *BIRTH_SPANS[(i + 1) % 12][0])
    if d < first:
        first = first.replace(year=2000)
    if nxt <= first:
        nxt = nxt.replace(year=nxt.year + 1)
    return (span_start(i) + 30 * (d - first).days / (nxt - first).days) % 360, i


def build():
    assert card_for_birthday(7, 14) == "Prince of Wands" and card_for_birthday(2, 5) == "Prince of Swords"
    timed, spans, marks, caps = [], [], [], []
    t = 0.4

    def cap(cls, on, off, title, line, line2=""):
        timed.append((cls, on, off, False))
        caps.append(f'<g class="cap {cls}"><text class="h" x="{W / 2}" y="222">{title}</text>'
                    f'<text class="n" x="{W / 2}" y="238">{line}</text>'
                    f'<text class="n" x="{W / 2}" y="250">{line2}</text></g>')

    # the court spans, round the wheel from the Prince of Swords
    for i, (_, title) in enumerate(BIRTH_SPANS):
        a = span_start(i)
        timed.append((f"s{i}", t + SPAN_EACH * i, None, False))
        x, y = at(sum(R_SPAN) / 2, a + 15)
        spans.append(f'<g class="sp s{i}"><path class="spn" d="{sector(*R_SPAN, a, a + 30)}"/>'
                     f'<text class="l" x="{x:.1f}" y="{y:.1f}" dy="0.35em">{short(title)}</text></g>')
    spans_end = t + SPAN_EACH * 12 + 0.6
    cap("c0", t, spans_end, "Twelve court cards", "each rules 21° of one sign", "to 20° of the next")
    t = spans_end + FADE

    # the Sun to each birthday, and the card it falls under
    sun_frames, last = [], 0.0
    for b, (m, d) in enumerate(BIRTHDAYS):
        deg, i = sun_degree(m, d)
        title = card_for_birthday(m, d)
        sign, within = SIGNS[int(deg // 30)], deg % 30
        cap(f"b{b}", t, t + MOVE, f"Born {d} {MONTHS[m - 1]}", f"the Sun is near {within:.0f}° {sign}")
        sun_frames.append((t, last, t + MOVE, deg if deg > last else deg + 360))
        last = sun_frames[-1][3]
        on, off = t + MOVE, t + MOVE + SHOW
        a = span_start(i)
        timed.append((f"h{b}", on, off, False))
        marks.append(f'<path class="hi h{b}" d="{sector(*R_SPAN, a, a + 30)}"/>')
        first = date(2001, *BIRTH_SPANS[i][0])
        end_day = date(2001, *BIRTH_SPANS[(i + 1) % 12][0]).toordinal() - 1
        end = date.fromordinal(end_day)
        cap(f"r{b}", on, off, title, f"21° {SPAN_SIGNS[i]} to 20° {SPAN_SIGNS[(i + 1) % 12]}",
            f"about {first.day} {MONTHS[first.month - 1]} to {end.day} {MONTHS[end.month - 1]}")
        t = off + FADE
    sun_off = t - FADE
    cap("cp", t, t + 4.0, "Never a Princess", "Princesses rule quarters", "of the sky, not dates")
    cycle = t + 4.0 + FADE + 0.3
    for k in range(12):   # the spans stay until the end
        timed[k] = (timed[k][0], timed[k][1], cycle - FADE - 0.3, False)

    # the Sun: a disc with a pointer out through both rings, turned round the centre
    p = lambda s: f"{max(0.0, min(s, cycle)) / cycle * 100:.2f}%"  # noqa: E731
    first_on = sun_frames[0][0]
    frames = [(f"0%{{opacity:0;transform:rotate(0deg)}}{p(first_on - .01)}{{opacity:0;transform:rotate(0deg)}}"
               f"{p(first_on + .3)}{{opacity:1;transform:rotate(0deg)}}")]
    for on, a0, off, a1 in sun_frames:
        frames.append(f"{p(on)}{{opacity:1;transform:rotate({-a0:.1f}deg)}}"
                      f"{p(off)}{{opacity:1;transform:rotate({-a1:.1f}deg)}}")
    frames.append(f"{p(sun_off)}{{opacity:1;transform:rotate({-last:.1f}deg)}}"
                  f"{p(sun_off + FADE)}{{opacity:0;transform:rotate({-last:.1f}deg)}}"
                  f"100%{{opacity:0;transform:rotate({-last:.1f}deg)}}")
    (sx, sy), (px, py), (qx, qy) = at(R_SUN, 0), at(R_SPAN[0], 0), at(R_OUT, 0)
    sun = (f'<g class="sun"><path class="ptr" d="M{px:.1f} {py:.1f}L{qx:.1f} {qy:.1f}"/>'
           f'<circle class="sd" cx="{sx:.1f}" cy="{sy:.1f}" r="5"/><circle class="sc" cx="{sx:.1f}" cy="{sy:.1f}" r="1.2"/></g>')

    ring = [f'<circle class="hub" cx="{CX}" cy="{CY}" r="{R_IN}"/>']
    for i in range(12):
        ring.append(f'<path class="sg" fill="{SIGN_KING[i]}" d="{sector(R_IN, R_OUT, i * 30, i * 30 + 30)}"/>')
        x, y = at((R_IN + R_OUT) / 2, i * 30 + 15)
        ring.append(f'<text class="gl" x="{x:.1f}" y="{y:.1f}" dy="0.35em" style="fill:{ink(SIGN_KING[i])}">{SIGN_GLYPHS[i]}</text>')

    css = (
        f".bg{{fill:#2E8A56}}text{{text-anchor:middle;fill:{CREAM}}}"
        f".sg{{stroke:{INK};stroke-opacity:.6;stroke-width:.6}}.gl{{font:12px serif}}"
        f".hub{{fill:{INK};fill-opacity:.18;stroke:{LINE};stroke-opacity:.35}}"
        f".spn{{fill:{CREAM};stroke:{INK};stroke-width:.7}}.l{{font:700 5.5px Inter,system-ui,sans-serif;fill:{INK}}}"
        f".hi{{fill:#fff;fill-opacity:.35;stroke:#fff;stroke-width:2;opacity:0}}"
        f".sun{{opacity:0;transform-origin:{CX}px {CY}px;animation:sun {cycle:.1f}s linear infinite}}"
        f".sd{{fill:#FFA500;stroke:{CREAM};stroke-width:1}}.sc{{fill:{INK}}}"
        f".ptr{{stroke:#fff;stroke-width:1.4;stroke-linecap:round}}"
        f".sp,.cap{{opacity:0}}"
        f".t{{font:600 8px Inter,system-ui,sans-serif;fill:{LINE}}}"
        f".h{{font:700 11px Inter,system-ui,sans-serif}}.n{{font:600 8px Inter,system-ui,sans-serif}}"
        f"@keyframes sun{{{''.join(frames)}}}"
        + keyframes(timed, cycle)
        + "@media (prefers-reduced-motion:reduce){*{animation:none!important}"
        f".sp,.h0,.r0{{opacity:1!important}}.sun{{opacity:1!important;transform:rotate({-sun_frames[0][3]:.1f}deg)}}}}"
    )
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
            f'<style>{css}</style><rect class="bg" width="{W}" height="{H}" rx="10"/>'
            f'<text class="t" x="{W / 2}" y="18">A significator from your birthday</text>'
            + "".join(ring) + "".join(spans) + "".join(marks) + sun + "".join(caps)
            + f'<text class="t" x="{W / 2}" y="278">As Book T gives them</text></svg>\n')


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")

"""Builds static/site/question-to-ai.svg, the animation of a whole first reading on the Start here
page (templates/start.html, "Your first reading, step by step").

One example question goes through the six steps of "Help me shape my question" (the part of
life, a rough question in your own words, what the reading should do, whose question and over
what span, "Anything your AI should know?", and the finished question), then the cards are
drawn, the prompt is saved with "Save prompt as Markdown (.md)", and the file is attached in an
AI with its + button.

The words on screen are the site's own: build() checks each label against the question helper
(templates/_question_helper.html), the composed question against static/js/ask.js and the save
button against templates/report.html, so the animation fails to build rather than drift if
those change. No AI is named; the chat window is a plain "Your AI".

Same look as scripts/make_own_place_animation.py and reuses the keyframes of
scripts/make_aspects_animation.py. Pure SVG + CSS: no script. Visitors who ask for reduced
motion see the last scene, still. Run `python scripts/make_question_animation.py` after changing
anything here.
"""
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_aspects_animation import keyframes  # noqa: E402,I001

from ootk import PROJECT_ROOT  # noqa: E402

OUT = PROJECT_ROOT / "static" / "site" / "question-to-ai.svg"

W, H = 160, 294
CREAM, INK, LINE, WARN = "#FFE0A0", "#0f2a1b", "#A7E2C0", "#c0562a"
PX, PY, PW, PH = 8, 28, 144, 180     # the panel each scene is drawn in
FADE = 0.5

# The example, in the helper's own words.
AREAS = ["Love and relationships", "Work and career", "Money and resources", "Home and family",
         "Health and wellbeing", "Creative work", "Spiritual path", "Something else"]
INTENTS = ["Give me one clear focus", "Help me weigh a decision", "Show where it's heading",
           "Show what's holding me back", "Help bring an idea into being",
           "Show how it affects my whole life", "Show its spiritual meaning",
           "The full picture of a turning point"]
RAW = "Should I take the new job?"
YES_NO = "A yes/no question boxes every card into one answer. The reframe asks how or what instead."
SUBJECT = "the job offer"
QUESTION = ("What is drawing me toward the job offer, and what in me or the situation is "
            "resisting it, over the next three months?")
SITUATION = "Offered a lead role last week."
UNSURE = "Leaving a team I like."
POSITIONS = [("Active Force", "what draws you forward"),
             ("Resistance", "what in you or the situation holds back")]
SAVE = "Save prompt as Markdown (.md)"
FILE = "attach_this_to_your_ai_2026-11-07.md"


def check_against_site():
    helper = html.unescape((PROJECT_ROOT / "templates" / "_question_helper.html").read_text(encoding="utf-8"))
    for s in (["Help me shape my question", "Which part of life does it touch?", "In your own words",
               "What it's about, in a few words", "What do you want the reading to do?",
               "Whose question is it?", "Over what span of time?", "The next three months",
               "Anything your AI should know?", "Add some background (optional)", "The situation now",
               "What you're most unsure about", "Also ask: what am I not asking that I should be?",
               "Your question", "How each position answers it", "Use this question"]
              + AREAS + INTENTS):
        assert s in helper, f"not in the question helper: {s!r}"
    ask = (PROJECT_ROOT / "static" / "js" / "ask.js").read_text(encoding="utf-8")
    assert "What is drawing me toward ${s}, and what in me or the situation is resisting it" in ask
    assert '", over the next three months"' in ask
    assert YES_NO in ask
    for p, a in POSITIONS:
        assert f'["{p}", "{a}"]' in ask, p
    report = (PROJECT_ROOT / "templates" / "report.html").read_text(encoding="utf-8")
    for s in (SAVE, "Send the prompt to your AI", "Save as PDF (print)", "Save as JSON"):
        assert s in report, f"not on the report page: {s!r}"
    assert "attach_this_to_your_ai_" in (PROJECT_ROOT / "static" / "js" / "report.js").read_text(encoding="utf-8")


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "’")


def wrap(s, n):
    lines, cur = [], ""
    for word in s.split():
        if cur and len(cur) + 1 + len(word) > n:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    return lines + [cur] if cur else lines


class Scene:
    """Markup for one scene, with its own timed pieces, shown from t0 to t1."""

    def __init__(self, anim, k, t0, t1):
        self.anim, self.k, self.t0, self.t1, self.n = anim, k, t0, t1, 0
        self.parts = []

    def timed(self, markup, on, off=None, still=True):
        """Markup that fades in at t0 + on and stays to `off` (default the scene's end).
        `still` pieces show in the reduced-motion picture of the last scene."""
        cls = f"s{self.k}e{self.n}"
        self.n += 1
        self.anim.timed.append((cls, self.t0 + on, self.t1 if off is None else self.t0 + off, False))
        self.parts.append(f'<g class="e{" w" if still else ""} {cls}">{markup}</g>')

    def add(self, markup):
        self.parts.append(markup)

    def typed(self, x, y, s, on, cls="v", per=0.12, off=None, still=True):
        """Words appearing one at a time, as if typed: tspans of one text, so the spacing is the
        font's own. Their fill-opacity is animated, since opacity does not apply to a tspan."""
        words = s.split()
        spans = []
        for i, word in enumerate(words):
            c = f"s{self.k}e{self.n}"
            self.n += 1
            self.anim.typing.append((c, self.t0 + on + i * per, self.t1 if off is None else self.t0 + off, False))
            spans.append(f'<tspan class="ty {c}">{esc(word)}{" " if i < len(words) - 1 else ""}</tspan>')
        g = f'<text class="{cls}" x="{x}" y="{y}" xml:space="preserve">{"".join(spans)}</text>'
        if off is not None:   # gone with the rest of the input once sent
            cg = f"s{self.k}e{self.n}"
            self.n += 1
            self.anim.timed.append((cg, self.t0, self.t0 + off, False))
            g = f'<g class="e {cg}">{g}</g>'
        self.parts.append(g)

    def press(self, x, y, w, h, at):
        """A brief flash over a button, as if it were pressed."""
        self.timed(f'<rect class="fl" x="{x}" y="{y}" width="{w}" height="{h}" rx="3"/>', at, at + 0.25)


class Anim:
    def __init__(self):
        self.timed, self.typing, self.scenes, self.caps = [], [], [], []
        self.t = 0.6

    def scene(self, dur, title, line, line2):
        k = len(self.scenes)
        s = Scene(self, k, self.t, self.t + dur)
        self.timed.append((f"s{k}", s.t0, s.t1, False))
        self.timed.append((f"c{k}", s.t0, s.t1, False))
        self.caps.append(f'<g class="cap c{k}"><text class="h" x="{W / 2}" y="224">{esc(title)}</text>'
                         f'<text class="n" x="{W / 2}" y="239">{esc(line)}</text>'
                         f'<text class="n" x="{W / 2}" y="251">{esc(line2)}</text></g>')
        self.scenes.append(s)
        self.t += dur + FADE + 0.1
        return s


def radio(s, x, y, label, chosen_at=None, default=False, unchosen_at=None, sub=None):
    s.add(f'<circle class="rb" cx="{x + 3}" cy="{y - 2}" r="2.4"/>'
          f'<text class="o" x="{x + 9}" y="{y}">{esc(label)}</text>')
    if sub:
        s.add(f'<text class="sub" x="{x + 9}" y="{y + 7}">{esc(sub)}</text>')
    dot = f'<circle class="rd" cx="{x + 3}" cy="{y - 2}" r="1.3"/>'
    if default:
        s.timed(dot, 0, unchosen_at)
    if chosen_at is not None:
        tall = 14 if sub else 9
        s.timed(dot + f'<rect class="sel" x="{x - 2}" y="{y - 7.5}" width="{PW - 12}" height="{tall}" rx="2"/>', chosen_at)


def helper_frame(s, step):
    """The helper's open panel: its summary at the top, Back, the count and Next at the bottom."""
    s.add(f'<rect class="pn" x="{PX}" y="{PY}" width="{PW}" height="{PH}" rx="6"/>'
          f'<text class="sm" x="{PX + 8}" y="{PY + 11}">▾ Help me shape my question</text>')
    by = PY + PH - 17
    s.add(f'<rect class="bt" x="{PX + 6}" y="{by}" width="30" height="12" rx="3"/>'
          f'<text class="b" x="{PX + 21}" y="{by + 8.2}">Back</text>'
          f'<text class="sub" x="{W / 2}" y="{by + 8.2}" style="text-anchor:middle">{step} of 6</text>')
    nx = PX + PW - 36
    label = "Next" if step < 6 else ""
    if label:
        s.add(f'<rect class="bt" x="{nx}" y="{by}" width="30" height="12" rx="3"/>'
              f'<text class="b" x="{nx + 15}" y="{by + 8.2}">Next</text>')
        s.press(nx, by, 30, 12, s.t1 - s.t0 - 0.45)


def legend(s, y, text):
    s.add(f'<text class="lg" x="{PX + 8}" y="{y}">{esc(text)}</text>')


def field(s, y, h=13):
    s.add(f'<rect class="fd" x="{PX + 8}" y="{y}" width="{PW - 16}" height="{h}" rx="2"/>')


def build():
    check_against_site()
    a = Anim()
    x0 = PX + 10

    # 1. Which part of life
    s = a.scene(3.4, "Shape your question", "open the helper and pick", "the part of life it touches")
    helper_frame(s, 1)
    legend(s, PY + 27, "Which part of life does it touch?")
    for i, area in enumerate(AREAS):
        radio(s, x0, PY + 41 + i * 15, area, chosen_at=1.4 if i == 1 else None)

    # 2. In your own words
    s = a.scene(4.8, "In your own words", "a rough question is fine;", "the helper flags a yes/no one")
    helper_frame(s, 2)
    legend(s, PY + 27, "In your own words")
    field(s, PY + 31, 20)
    s.typed(PX + 11, PY + 40, RAW, 0.5)
    hint = wrap(YES_NO, 37)
    s.timed(f'<rect class="hn" x="{PX + 8}" y="{PY + 56}" width="{PW - 16}" height="{6 + 7 * len(hint)}" rx="2"/>'
            f'<rect x="{PX + 8}" y="{PY + 56}" width="2" height="{6 + 7 * len(hint)}" fill="{WARN}"/>'
            + "".join(f'<text class="sub" x="{PX + 13}" y="{PY + 63 + 7 * j}">{esc(t)}</text>'
                      for j, t in enumerate(hint)), 1.4)
    legend(s, PY + 98, "What it's about, in a few words")
    field(s, PY + 102)
    s.typed(PX + 11, PY + 111, SUBJECT, 2.6)

    # 3. What the reading should do
    s = a.scene(3.6, "What it should do", "this picks the spread:", "a decision suggests the Dyad")
    helper_frame(s, 3)
    legend(s, PY + 27, "What do you want the reading to do?")
    y = PY + 41
    for i, intent in enumerate(INTENTS):
        radio(s, x0, y, intent, chosen_at=1.4 if i == 1 else None, sub="Suggests the Dyad" if i == 1 else None)
        y += 20 if i == 1 else 14

    # 4. Whose question, over what span
    s = a.scene(3.8, "Whose, and how long", "yours, over the next", "three months")
    helper_frame(s, 4)
    legend(s, PY + 27, "Whose question is it?")
    for i, who in enumerate(["Mine", "Mainly about someone else", "About us together"]):
        radio(s, x0, PY + 40 + i * 13, who, default=i == 0)
    legend(s, PY + 88, "Over what span of time?")
    for i, span in enumerate(["The next few weeks", "The next three months", "The coming year", "No set window"]):
        radio(s, x0, PY + 101 + i * 13, span, chosen_at=1.6 if i == 1 else None,
              default=i == 3, unchosen_at=1.6 if i == 3 else None)

    # 5. Anything your AI should know?
    s = a.scene(5.0, "Background for your AI", "optional; it goes into", "the prompt with the question")
    helper_frame(s, 5)
    s.add(f'<text class="ld" x="{PX + 8}" y="{PY + 28}">Anything your AI should know?</text>')
    s.add(f'<rect class="bt" x="{PX + 8}" y="{PY + 34}" width="{PW - 16}" height="12" rx="3"/>'
          f'<text class="b" x="{W / 2}" y="{PY + 42.2}">Add some background (optional)</text>')
    s.press(PX + 8, PY + 34, PW - 16, 12, 0.7)
    box = (f'<text class="lg" x="{PX + 8}" y="{PY + 59}">The situation now</text>'
           f'<rect class="fd" x="{PX + 8}" y="{PY + 63}" width="{PW - 16}" height="13" rx="2"/>'
           f'<text class="lg" x="{PX + 8}" y="{PY + 88}">What you’re most unsure about</text>'
           f'<rect class="fd" x="{PX + 8}" y="{PY + 92}" width="{PW - 16}" height="13" rx="2"/>')
    s.timed(box, 1.0)
    s.typed(PX + 11, PY + 72, SITUATION, 1.5)
    s.typed(PX + 11, PY + 101, UNSURE, 2.5)
    cy = PY + 120
    s.add(f'<rect class="cb" x="{PX + 8}" y="{cy - 5}" width="5" height="5" rx="1"/>'
          f'<text class="tk" x="{PX + 10.5}" y="{cy - 0.6}">✓</text>'
          f'<text class="o" x="{PX + 17}" y="{cy}">Also ask: what am I not asking</text>'
          f'<text class="o" x="{PX + 17}" y="{cy + 8}">that I should be?</text>')

    # 6. The finished question
    s = a.scene(4.6, "Your question", "open, and shaped to", "the spread’s positions")
    helper_frame(s, 6)
    s.add(f'<text class="hd" x="{PX + 8}" y="{PY + 27}">YOUR QUESTION</text>')
    q = wrap(QUESTION, 33)
    s.add("".join(f'<text class="q" x="{PX + 8}" y="{PY + 38 + 9 * j}">{esc(t)}</text>' for j, t in enumerate(q)))
    y = PY + 42 + 9 * len(q)
    s.add(f'<text class="sub" x="{PX + 8}" y="{y}">Spread</text><text class="o" x="{PX + 40}" y="{y}">Dyad</text>')
    y += 13
    s.add(f'<text class="hd" x="{PX + 8}" y="{y}">HOW EACH POSITION ANSWERS IT</text>')
    for p, ans in POSITIONS:
        y += 10
        s.add(f'<line class="ln" x1="{PX + 8}" x2="{PX + PW - 8}" y1="{y - 7}" y2="{y - 7}"/>'
              f'<text class="o" x="{PX + 8}" y="{y}"><tspan class="bo">{p}:</tspan> {esc(wrap(ans, 26)[0])}</text>')
        rest = wrap(ans, 26)[1:]
        for t in rest:
            y += 7
            s.add(f'<text class="o" x="{PX + 8}" y="{y}">{esc(t)}</text>')
    by = PY + PH - 34
    s.add(f'<rect class="bt" x="{PX + 8}" y="{by}" width="66" height="12" rx="3"/>'
          f'<text class="b" x="{PX + 41}" y="{by + 8.2}">Use this question</text>')
    s.press(PX + 8, by, 66, 12, 3.4)

    # 7. Draw the cards
    s = a.scene(3.8, "Draw the cards", "the question rides along;", "it doesn’t change the cards")
    s.add(f'<rect class="pn" x="{PX}" y="{PY}" width="{PW}" height="{PH}" rx="6"/>'
          f'<text class="lg" x="{PX + 8}" y="{PY + 14}">Question</text>')
    field(s, PY + 18, 22)
    for j, t in enumerate(wrap(QUESTION, 34)[:2]):
        s.add(f'<text class="v" x="{PX + 11}" y="{PY + 27 + 8 * j}">{esc(t)}{"…" if j else ""}</text>')
    s.add(f'<text class="sub" x="{PX + 8}" y="{PY + 51}">Spread</text><text class="o" x="{PX + 40}" y="{PY + 51}">Dyad</text>')
    s.add(f'<rect class="pr" x="{PX + 8}" y="{PY + 58}" width="{PW - 16}" height="13" rx="3"/>'
          f'<text class="bp" x="{W / 2}" y="{PY + 67}">Draw the cards</text>')
    s.press(PX + 8, PY + 58, PW - 16, 13, 0.8)
    for j, ((p, _), (lab, nm)) in enumerate(zip(POSITIONS, [("6 W", "Victory"), ("VIII", "Adjustment")])):
        cx = W / 2 + (j - 0.5) * 50
        s.timed(f'<rect class="cd" x="{cx - 16}" y="{PY + 84}" width="32" height="50" rx="3"/>'
                f'<text class="cl" x="{cx}" y="{PY + 112}">{lab}</text>'
                f'<text class="o" x="{cx}" y="{PY + 145}" style="text-anchor:middle">{nm}</text>'
                f'<text class="sub" x="{cx}" y="{PY + 154}" style="text-anchor:middle">{p}</text>', 1.3 + 0.5 * j)

    # 8. Save the prompt as Markdown
    s = a.scene(4.2, "Save as Markdown", "one .md file holds the cards,", "the sums and your question")
    s.add(f'<rect class="pn" x="{PX}" y="{PY}" width="{PW}" height="{PH}" rx="6"/>'
          f'<text class="ld" x="{PX + 8}" y="{PY + 15}">Send the prompt to your AI</text>'
          f'<text class="sub" x="{PX + 8}" y="{PY + 26}">Save the prompt as a file, then attach</text>'
          f'<text class="sub" x="{PX + 8}" y="{PY + 33}">it in your AI with +.</text>')
    s.add(f'<rect class="pr" x="{PX + 8}" y="{PY + 40}" width="{PW - 16}" height="14" rx="3"/>'
          f'<text class="bp" x="{W / 2}" y="{PY + 49.5}">{esc(SAVE)}</text>'
          f'<rect class="bt dim" x="{PX + 8}" y="{PY + 58}" width="62" height="11" rx="3"/>'
          f'<text class="b dim" x="{PX + 39}" y="{PY + 65.5}">Save as PDF (print)</text>'
          f'<rect class="bt dim" x="{PX + 74}" y="{PY + 58}" width="62" height="11" rx="3"/>'
          f'<text class="b dim" x="{PX + 105}" y="{PY + 65.5}">Save as JSON</text>')
    s.press(PX + 8, PY + 40, PW - 16, 14, 0.8)
    fx, fy = W / 2 - 14, PY + 88
    s.timed(f'<path class="fi" d="M{fx} {fy}h20l8 8v30h-28z"/><path class="fo" d="M{fx + 20} {fy}v8h8"/>'
            f'<text class="cl" x="{fx + 14}" y="{fy + 24}">.md</text>'
            + "".join(f'<text class="sub" x="{W / 2}" y="{fy + 48 + 8 * j}" style="text-anchor:middle">{t}</text>'
                      for j, t in enumerate([FILE[:23], FILE[23:]]))
            + f'<text class="sub" x="{W / 2}" y="{fy + 70}" style="text-anchor:middle;fill:{LINE}">saved to Downloads</text>', 1.2)

    # 9. Attach it in your AI
    s = a.scene(6.4, "Attach it in your AI", "press + and add the file;", "your AI writes the reading")
    s.add(f'<rect class="pn" x="{PX}" y="{PY}" width="{PW}" height="{PH}" rx="6"/>'
          f'<circle cx="{PX + 12}" cy="{PY + 11}" r="2.5" fill="{LINE}"/>'
          f'<text class="ld" x="{PX + 18}" y="{PY + 14}">Your AI</text>'
          f'<line class="ln" x1="{PX}" x2="{PX + PW}" y1="{PY + 21}" y2="{PY + 21}"/>')
    iy = PY + PH - 22
    s.add(f'<rect class="fd" x="{PX + 6}" y="{iy}" width="{PW - 12}" height="16" rx="8"/>'
          f'<circle class="pl" cx="{PX + 15}" cy="{iy + 8}" r="5"/><text class="pk" x="{PX + 15}" y="{iy + 10.6}">+</text>')
    s.timed(f'<text class="sub" x="{PX + 24}" y="{iy + 10.5}">Ask anything</text>', 0, 1.6, still=False)
    s.press(PX + 10, iy + 3, 10, 10, 0.7)
    chip = f'<rect class="ch" x="{PX + 8}" y="{iy - 15}" width="80" height="12" rx="3"/>' \
           f'<text class="sub" x="{PX + 12}" y="{iy - 6.5}">▤ attach_this_to_your_ai…md</text>'
    s.timed(chip, 1.2, 3.4, still=False)
    s.typed(PX + 24, iy + 10.5, "Please read my cards.", 1.9, cls="v", off=3.4, still=False)
    s.timed(f'<circle class="pr" cx="{PX + PW - 15}" cy="{iy + 8}" r="5"/>'
            f'<text class="pk2" x="{PX + PW - 15}" y="{iy + 10.6}">↑</text>', 2.5, 3.4, still=False)
    s.press(PX + PW - 20, iy + 3, 10, 10, 3.2)
    # The message, sent: the file and the words in a bubble on the right.
    bx = PX + 40
    s.timed(f'<rect class="ub" x="{bx}" y="{PY + 28}" width="{PW - 46}" height="30" rx="5"/>'
            f'<rect class="ch" x="{bx + 4}" y="{PY + 32}" width="{PW - 54}" height="11" rx="2"/>'
            f'<text class="sub" x="{bx + 7}" y="{PY + 39.5}">▤ attach_this_to_your_ai…md</text>'
            f'<text class="v" x="{bx + 5}" y="{PY + 53}">Please read my cards.</text>', 3.5)
    # The reply, line by line.
    s.timed(f'<rect class="ab" x="{PX + 6}" y="{PY + 64}" width="{PW - 30}" height="60" rx="5"/>', 4.0)
    for j, w in enumerate([96, 104, 88, 100, 70]):
        s.timed(f'<rect class="bar" x="{PX + 12}" y="{PY + 71 + 10 * j}" width="{w}" height="4" rx="2"/>', 4.3 + 0.3 * j)

    end = a.t - FADE - 0.1
    cycle = end + FADE + 0.4
    last = len(a.scenes) - 1
    font = "Inter,system-ui,sans-serif"
    css = (
        f".bg{{fill:#2E8A56}}text{{fill:{CREAM}}}.t,.h,.n,.b,.bp,.cl,.pk,.pk2{{text-anchor:middle}}"
        f".pn{{fill:{INK};fill-opacity:.32;stroke:{LINE};stroke-opacity:.35}}"
        f".fd{{fill:{CREAM};fill-opacity:.1;stroke:{LINE};stroke-opacity:.45;stroke-width:.6}}"
        f".hn{{fill:{INK};fill-opacity:.35}}"
        f".bt{{fill:none;stroke:{CREAM};stroke-opacity:.6;stroke-width:.7}}.dim{{opacity:.5}}"
        f".pr{{fill:{CREAM}}}.bp{{font:700 6.5px {font};fill:{INK}}}"
        f".fl{{fill:#fff;opacity:.45}}"
        f".rb{{fill:none;stroke:{CREAM};stroke-width:.7}}.rd{{fill:{CREAM}}}"
        f".sel{{fill:#fff;fill-opacity:.14;stroke:#fff;stroke-width:.8}}"
        f".cb{{fill:{CREAM}}}.tk{{font:700 5px {font};fill:{INK};text-anchor:middle}}"
        f".ln{{stroke:{LINE};stroke-opacity:.35;stroke-width:.5}}"
        f".cd{{fill:{CREAM};stroke:{INK};stroke-width:.7}}.cl{{font:700 8px {font};fill:{INK}}}"
        f".fi{{fill:{CREAM}}}.fo{{fill:none;stroke:{INK};stroke-width:.7}}"
        f".pl{{fill:none;stroke:{CREAM};stroke-width:.8}}.pk{{font:700 9px {font}}}"
        f".pk2{{font:700 7px {font};fill:{INK}}}"
        f".ch{{fill:{CREAM};fill-opacity:.18}}.ub{{fill:{CREAM};fill-opacity:.16}}"
        f".ab{{fill:{INK};fill-opacity:.3}}.bar{{fill:{LINE};fill-opacity:.7}}"
        f".sm{{font:600 6px {font};fill:{LINE}}}.lg{{font:600 6.2px {font};fill:{LINE}}}"
        f".ld{{font:700 7.5px {font}}}.hd{{font:700 5.2px {font};fill:{LINE};letter-spacing:.04em}}"
        f".o{{font:500 6.2px {font}}}.bo{{font-weight:700}}.v{{font:500 6.2px {font}}}"
        f".q{{font:600 7px {font}}}.sub{{font:500 5.2px {font}}}.b{{font:600 6px {font}}}"
        f".t{{font:600 8px {font};fill:{LINE}}}"
        f".h{{font:700 10px {font}}}.n{{font:600 8px {font}}}"
        f".sc,.cap,.e{{opacity:0}}"
        + keyframes(a.timed, cycle)
        + ".ty{fill-opacity:0}" + keyframes(a.typing, cycle).replace("{opacity:", "{fill-opacity:")
        + "@media (prefers-reduced-motion:reduce){*{animation:none!important}"
        + f".s{last},.c{last},.s{last} .w{{opacity:1!important}}}}"
    )
    scenes = "".join(f'<g class="sc s{s.k}">{"".join(s.parts)}</g>' for s in a.scenes)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
            f'<style>{css}</style><rect class="bg" width="{W}" height="{H}" rx="10"/>'
            f'<text class="t" x="{W / 2}" y="18">From question to your AI</text>'
            + scenes + "".join(a.caps)
            + f'<text class="t" x="{W / 2}" y="278">Example: a question about a job</text></svg>\n')


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")

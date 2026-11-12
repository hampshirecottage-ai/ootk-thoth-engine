"""Builds static/site/full-spread.svg, the animation of drawing a full Opening of the Key with
every correspondence switched on, for the Start here page (templates/start.html, Stage 4 of
"Learning stages").

It walks the start page's step-by-step form (templates/index.html, static/js/wizard.js) as a
visitor would: a question typed in; "How deep do you want to go?" set to The Opening of the Key
and the Full Opening of the Key picked; a significator described (me, the person asking, Feel
first, Young and driving things forward: the Prince of Cups); the options left at their
defaults; under "Parts of the AI prompt" the ten main parts already on and all seven extra layers
ticked; the review; Draw my cards; the report's four operations; and Save prompt as Markdown.
The last scene says what the prompt does when every layer makes it too long: it drops the
layers in FIT_ORDER and names them under "Left Out to Fit".

The words on screen are the site's own: check_against_site() checks the labels against the
templates and scripts, and the spread, significator answers and prompt parts against the
tables in ootk.web, ootk.significator and ootk.report, so the animation fails to build rather
than drift if those change. No AI is named.

Same look and helpers as scripts/make_question_animation.py. Pure SVG + CSS: no script.
Visitors who ask for reduced motion see the last scene, still. Run
`python scripts/make_full_spread_animation.py` after changing anything here.
"""
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_aspects_animation import keyframes  # noqa: E402,I001
from make_question_animation import (  # noqa: E402
    CREAM, FADE, H, INK, LINE, PH, PW, PX, PY, W, WARN, Anim, esc, legend, radio, wrap)

from ootk import PROJECT_ROOT  # noqa: E402
from ootk.report import COMPONENTS, DEFAULT_OFF, FIT_ORDER  # noqa: E402
from ootk.significator import LIFE_STAGES, TEMPERAMENTS  # noqa: E402
from ootk.spreads import SPREADS, spread_positions  # noqa: E402

OUT = PROJECT_ROOT / "static" / "site" / "full-spread.svg"

QUESTION = "What do I need to understand about the move to a new city?"
RAIL = ["Question", "Spread", "Significator", "Options", "Draw"]
ASK = ["Help me find my question", "I know what I want to ask", "No question, a general reading"]
DEPTHS = ["A quick look", "How forces meet", "The whole picture", "The Opening of the Key"]
# Stage 4's spreads as the picker's small print names them: (spread key, name, size).
STAGE4 = [("8", "First Operation", "15 cards"), ("9", "Second Operation", "12 cards"),
          ("10", "Third Operation", "12 cards"), ("11", "Fourth Operation", "36 cards"),
          ("12", "Full Opening of the Key", "75 cards"), ("13", "Book T Opening of the Key", "about 78 cards")]
FULL = "12"
SUIT, RANK = "Cups", "Prince"
SIGNIFICATOR = f"{RANK} of {SUIT}"
MAIN = [COMPONENTS[k] for k in COMPONENTS if k not in DEFAULT_OFF]
EXTRA = [COMPONENTS[k] for k in COMPONENTS if k in DEFAULT_OFF]
# The full Opening of the Key's four operations, as the report's Operations table counts them.
OPS = [("Operation 1", "15-card heap", 15), ("Operation 2", "12 houses", 12),
       ("Operation 3", "12 signs", 12), ("Operation 4", "36 decans", 36)]
SAVE = "Save prompt as Markdown (.md)"


def check_against_site():
    import ootk.web as web
    fields = html.unescape((PROJECT_ROOT / "templates" / "_settings_fields.html").read_text(encoding="utf-8"))
    for s in (["How would you like to ask?", "How deep do you want to go?", "Which one fits your question?",
               "Describe", "Birth date", "Any card", "Who is the reading about?", "Me", "Someone else",
               "What should the card stand for?", "Me, the person asking", "The matter the question is about",
               "How do you usually meet life?", "Which fits you best right now?",
               "Which cards should be drawn?", "New cards", "Which tradition should the cards follow?",
               "Thoth, Crowley’s deck", "What kind of story should your AI tell?", "Let the cards decide",
               "Parts of the AI prompt", "Main parts", "Extra layers (off unless you add them)"] + ASK):
        assert s in fields, f"not in the settings form: {s!r}"
    for t in RAIL:
        assert f'data-title="{t}"' in fields + (PROJECT_ROOT / "templates" / "index.html").read_text(encoding="utf-8"), t
    index = (PROJECT_ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    for s in ("Ask your question", "Check your choices, then draw.", "Draw my cards"):
        assert s in index, f"not on the start page: {s!r}"
    wizard = (PROJECT_ROOT / "static" / "js" / "wizard.js").read_text(encoding="utf-8")
    for s in ("Step ${current + 1} of ${steps.length}", '"Extra layers"', '"Significator"', '"Tradition"', '"Story"'):
        assert s in wizard, f"not in wizard.js: {s!r}"
    assert [html.unescape(d[0]) for d in web.SPREAD_DEPTHS] == DEPTHS
    stage4 = web.SPREAD_STAGES[3]
    assert stage4[1] == "The Opening of the Key" and stage4[2] == [k for k, _, _ in STAGE4]
    for key, name, size in STAGE4:
        assert web.spread_label(key) == name and web.spread_size_text(key) == size, key
    assert SPREADS[FULL]["operations"] == ["8", "9", "10", "11"]
    assert [len(spread_positions(k)) for k in SPREADS[FULL]["operations"]] == [n for _, _, n in OPS]
    assert len(spread_positions(FULL)) == 75
    assert TEMPERAMENTS[SUIT].startswith("Feel first") and LIFE_STAGES[RANK] == "Young, and driving things forward"
    assert len(MAIN) == 10 and len(EXTRA) == 7
    assert list(FIT_ORDER[:3]) == ["gods", "angels", "timing"]
    report = (PROJECT_ROOT / "templates" / "report.html").read_text(encoding="utf-8")
    for s in (SAVE, "Send the prompt to your AI", "Where the significator falls", "Operations"):
        assert s in report, f"not on the report page: {s!r}"
    assert "**Left Out to Fit:**" in (PROJECT_ROOT / "src" / "ootk" / "report.py").read_text(encoding="utf-8")


def wizard_frame(s, step, next_at=None, nav=True):
    """The form's panel: its title, the five-step rail with this step lit, and Back, the count
    and Next at the bottom. Returns the y where the step's own content starts."""
    s.add(f'<rect class="pn" x="{PX}" y="{PY}" width="{PW}" height="{PH}" rx="6"/>'
          f'<text class="ld" x="{PX + 8}" y="{PY + 12}">Ask your question</text>')
    x, ry = PX + 8, PY + 17
    for i, t in enumerate(RAIL):
        w = 8 + 2.9 * len(f"{i + 1} {t}")
        if i == 3:   # the rail wraps after Significator, as it does on the site
            x, ry = PX + 8, ry + 10
        cur = i == step
        s.add(f'<rect class="{"rc" if cur else "rl"}" x="{x:.1f}" y="{ry}" width="{w:.1f}" height="8" rx="4"/>'
              f'<text class="rt{" ri" if cur else ""}" x="{x + w / 2:.1f}" y="{ry + 5.6}">{i + 1} {t}</text>')
        x += w + 2.5
    if nav:
        by = PY + PH - 16
        s.add(f'<rect class="bt" x="{PX + 6}" y="{by}" width="28" height="11" rx="3"/>'
              f'<text class="b" x="{PX + 20}" y="{by + 7.6}">Back</text>'
              f'<text class="sub" x="{W / 2}" y="{by + 7.6}" style="text-anchor:middle">Step {step + 1} of 5</text>'
              f'<rect class="pr" x="{PX + PW - 34}" y="{by}" width="28" height="11" rx="3"/>'
              f'<text class="bp" x="{PX + PW - 20}" y="{by + 7.6}">Next</text>')
        s.press(PX + PW - 34, by, 28, 11, (s.t1 - s.t0 - 0.45) if next_at is None else next_at)
    return PY + 46


def check(s, x, y, label, on_at=None, on=False):
    """A checkbox: ticked from the start (`on`) or ticked at `on_at`."""
    s.add(f'<rect class="cx" x="{x}" y="{y - 5}" width="5" height="5" rx="1"/>'
          f'<text class="o" x="{x + 9}" y="{y}">{esc(label)}</text>')
    tick = (f'<rect class="cb" x="{x}" y="{y - 5}" width="5" height="5" rx="1"/>'
            f'<text class="tk" x="{x + 2.5}" y="{y - 0.6}">✓</text>')
    if on:
        s.add(tick)
    elif on_at is not None:
        s.timed(tick + f'<rect class="sel" x="{x - 2}" y="{y - 7}" width="{PW - 12}" height="9" rx="2"/>', on_at)


def build():
    check_against_site()
    a = Anim()
    x0 = PX + 10

    # 1. The question
    s = a.scene(4.4, "Ask your question", "type it in, or let the", "helper shape it with you")
    y = wizard_frame(s, 0)
    legend(s, y + 4, "How would you like to ask?")
    for i, t in enumerate(ASK):
        radio(s, x0, y + 16 + i * 12, t, chosen_at=0.9 if i == 1 else None)
    s.timed(f'<text class="lg" x="{PX + 8}" y="{y + 58}">Question</text>', 1.3)
    s.timed(f'<rect class="fd" x="{PX + 8}" y="{y + 62}" width="{PW - 16}" height="22" rx="2"/>', 1.3)
    for j, t in enumerate(wrap(QUESTION, 34)):
        s.typed(PX + 11, y + 71 + 8 * j, t, 1.6 + j * 0.9)

    # 2. How deep
    s = a.scene(3.4, "Choose the spread", "how deep: the Opening", "of the Key")
    y = wizard_frame(s, 1)
    legend(s, y + 4, "How deep do you want to go?")
    for i, t in enumerate(DEPTHS):
        radio(s, x0, y + 16 + i * 14, t, chosen_at=1.3 if i == 3 else None)
    s.add(f'<text class="sub" x="{PX + 8}" y="{y + 82}">The Golden Dawn’s long method, 12 to about 80 cards</text>')

    # 3. Which one
    s = a.scene(3.8, "Full Opening of the Key", "all four operations", "in one reading: 75 cards")
    y = wizard_frame(s, 1)
    legend(s, y + 4, "Which one fits your question?")
    for i, (key, name, size) in enumerate(STAGE4):
        radio(s, x0, y + 16 + i * 13, name, chosen_at=1.4 if key == FULL else None)
        s.add(f'<text class="sub" x="{PX + PW - 10}" y="{y + 16 + i * 13}" style="text-anchor:end">{size}</text>')

    # 4. The significator: who it stands for
    s = a.scene(3.8, "Describe a significator", "the card that stands for", "you in every operation")
    y = wizard_frame(s, 2, nav=False)
    sx, sw = PX + 8, (PW - 16) / 3
    for i, t in enumerate(["Describe", "Birth date", "Any card"]):
        s.add(f'<rect class="{"rc" if i == 0 else "rl"}" x="{sx + i * sw:.1f}" y="{y}" width="{sw:.1f}" height="10" rx="2"/>'
              f'<text class="rt{" ri" if i == 0 else ""}" x="{sx + i * sw + sw / 2:.1f}" y="{y + 6.8}">{t}</text>')
    legend(s, y + 20, "Who is the reading about?")
    radio(s, x0, y + 31, "Me", chosen_at=0.9)
    radio(s, x0, y + 42, "Someone else")
    q2 = (f'<text class="lg" x="{PX + 8}" y="{y + 58}">What should the card stand for?</text>')
    s.timed(q2, 1.4)
    for i, (t, sub) in enumerate([("Me, the person asking", "Book T, recommended"),
                                  ("The matter the question is about", "a later custom")]):
        s.timed(f'<circle class="rb" cx="{x0 + 3}" cy="{y + 68 + i * 17}" r="2.4"/>'
                f'<text class="o" x="{x0 + 9}" y="{y + 70 + i * 17}">{esc(t)}</text>'
                f'<text class="sub" x="{x0 + 9}" y="{y + 77 + i * 17}">{esc(sub)}</text>', 1.4)
    s.timed(f'<circle class="rd" cx="{x0 + 3}" cy="{y + 68}" r="1.3"/>'
            f'<rect class="sel" x="{x0 - 2}" y="{y + 62.5}" width="{PW - 12}" height="16" rx="2"/>', 2.3)

    # 5. The significator: how you meet life, where you are now
    s = a.scene(4.6, "Feel first, and young", "Cups and a Prince:", "the Prince of Cups")
    y = wizard_frame(s, 2, next_at=4.15)
    legend(s, y + 2, "How do you usually meet life?")
    for i, suit in enumerate(TEMPERAMENTS):
        t = TEMPERAMENTS[suit].split(":")[0]
        s.add(f'<circle class="rb" cx="{x0 + 3}" cy="{y + 8 + i * 9}" r="2.4"/>'
              f'<text class="o" x="{x0 + 9}" y="{y + 10 + i * 9}">{esc(t)}</text>'
              f'<text class="sub" x="{x0 + 62}" y="{y + 10 + i * 9}">{suit}</text>')
        if suit == SUIT:
            s.timed(f'<circle class="rd" cx="{x0 + 3}" cy="{y + 8 + i * 9}" r="1.3"/>'
                    f'<rect class="sel" x="{x0 - 2}" y="{y + 3.5 + i * 9}" width="{PW - 12}" height="9" rx="2"/>', 0.8)
    s.timed(f'<text class="lg" x="{PX + 8}" y="{y + 46}">Which fits you best right now?</text>', 1.2)
    for i, rank in enumerate(LIFE_STAGES):
        s.timed(f'<circle class="rb" cx="{x0 + 3}" cy="{y + 54 + i * 9}" r="2.4"/>'
                f'<text class="o" x="{x0 + 9}" y="{y + 56 + i * 9}">{esc(LIFE_STAGES[rank])}</text>', 1.2)
        if rank == RANK:
            s.timed(f'<circle class="rd" cx="{x0 + 3}" cy="{y + 54 + i * 9}" r="1.3"/>'
                    f'<rect class="sel" x="{x0 - 2}" y="{y + 49.5 + i * 9}" width="{PW - 12}" height="9" rx="2"/>', 2.0)
    cy = y + 88
    s.timed(f'<rect class="hn" x="{PX + 8}" y="{cy}" width="{PW - 16}" height="24" rx="3"/>'
            f'<rect class="cd" x="{PX + 12}" y="{cy + 2}" width="13" height="20" rx="1.5"/>'
            f'<text class="cl" x="{PX + 18.5}" y="{cy + 15}" style="font-size:5px">P♡</text>'
            f'<text class="ld" x="{PX + 31}" y="{cy + 11}">{SIGNIFICATOR}</text>'
            f'<text class="sub" x="{PX + 31}" y="{cy + 19}">Air of Water</text>', 2.6)

    # 6. Options, left at their defaults
    s = a.scene(3.6, "Options", "keep the defaults: new cards,", "Thoth, and let the cards decide")
    y = wizard_frame(s, 3)
    for i, (leg, val) in enumerate([("Which cards should be drawn?", "New cards"),
                                    ("Which tradition should the cards follow?", "Thoth, Crowley’s deck"),
                                    ("What kind of story should your AI tell?", "Let the cards decide")]):
        legend(s, y + 2 + i * 24, leg)
        radio(s, x0, y + 14 + i * 24, val, default=True)
    s.add(f'<text class="sm" x="{PX + 8}" y="{y + 82}">▸ Parts of the AI prompt · standard</text>')
    s.press(PX + 6, y + 75, PW - 12, 9, 2.8)

    # 7. The main parts, on already
    s = a.scene(3.4, "Parts of the AI prompt", "the ten main parts", "are already on")
    y = wizard_frame(s, 3)
    s.add(f'<text class="sm" x="{PX + 8}" y="{y + 2}">▾ Parts of the AI prompt · standard</text>'
          f'<text class="hd" x="{PX + 8}" y="{y + 13}">MAIN PARTS</text>')
    for i, name in enumerate(MAIN):
        check(s, PX + 10, y + 24 + i * 10, name, on=True)

    # 8. Every extra layer
    s = a.scene(5.0, "Add every extra layer", "all 17 parts of the prompt", "on: every correspondence")
    y = wizard_frame(s, 3)
    s.add(f'<text class="sm" x="{PX + 8}" y="{y + 2}">▾ Parts of the AI prompt</text>')
    s.timed(f'<text class="sm" x="{PX + 79}" y="{y + 2}">· standard</text>', 0, 4.0, still=False)
    s.timed(f'<text class="sm" x="{PX + 79}" y="{y + 2}">· 7 added</text>', 4.0)
    s.add(f'<text class="hd" x="{PX + 8}" y="{y + 13}">EXTRA LAYERS (OFF UNLESS YOU ADD THEM)</text>')
    for i, name in enumerate(EXTRA):
        check(s, PX + 10, y + 23 + i * 10, name, on_at=0.6 + 0.33 * i)

    # 9. Check and draw
    s = a.scene(4.2, "Check, then draw", "the review lists your", "choices; then Draw my cards")
    y = wizard_frame(s, 4, nav=False)
    s.add(f'<text class="o" x="{PX + 8}" y="{y + 2}">Check your choices, then draw.</text>')
    rows = [("Question", "What do I need to understand…"), ("Spread", "Full Opening of the Key, 75 cards"),
            ("Significator", SIGNIFICATOR), ("Tradition", "Thoth, Crowley’s deck"),
            ("Story", "Let the cards decide (Auto)"), ("Cards", "New cards, random seed"),
            ("Extra layers", "all seven, from Geomantic"), ("", "figures to Court card hexagrams")]
    for i, (k, v) in enumerate(rows):
        s.add(f'<text class="sub" x="{PX + 8}" y="{y + 14 + i * 10}">{k}</text>'
              f'<text class="o" x="{PX + 42}" y="{y + 14 + i * 10}">{esc(v)}</text>')
    by = PY + PH - 34
    s.add(f'<rect class="pr" x="{PX + 8}" y="{by}" width="{PW - 16}" height="14" rx="3"/>'
          f'<text class="bp" x="{W / 2}" y="{by + 9.5}">Draw my cards</text>')
    s.press(PX + 8, by, PW - 16, 14, 2.9)

    # 10. The report: four operations, 75 cards
    s = a.scene(5.2, "Four operations", "15 + 12 + 12 + 36 cards, and", "where your significator falls")
    s.add(f'<rect class="pn" x="{PX}" y="{PY}" width="{PW}" height="{PH}" rx="6"/>'
          f'<text class="hd" x="{PX + 8}" y="{PY + 12}">YOUR READING · 75 CARDS · THOTH / CROWLEY</text>'
          f'<text class="ld" x="{PX + 8}" y="{PY + 24}">Full Opening of the Key</text>'
          f'<text class="lg" x="{PX + 8}" y="{PY + 38}">Operations</text>')
    y = PY + 44
    for i, (op, what, n) in enumerate(OPS):
        on = 0.5 + 0.9 * i
        cols = 15 if n == 15 else 12
        s.timed(f'<text class="o" x="{PX + 8}" y="{y + 6}"><tspan class="bo">{op}</tspan> · {what}</text>'
                f'<text class="o" x="{PX + PW - 8}" y="{y + 6}" style="text-anchor:end">{n}</text>', on)
        for j in range(n):
            cx = PX + 9 + (j % cols) * 8.6
            cyy = y + 10 + (j // cols) * 9
            sig = j == 0 and i == 0
            s.timed(f'<rect class="{"cs" if sig else "cd"}" x="{cx:.1f}" y="{cyy}" width="6" height="8" rx="1"/>',
                    on + 0.2 + j * 0.012)
        y += 14 + 9 * ((n + cols - 1) // cols)
    s.timed(f'<text class="sub" x="{PX + 8}" y="{PY + PH - 8}">▣ Prince of Cups, the significator, sits first</text>', 4.0)

    # 11. Save the long prompt
    s = a.scene(6.0, "Save as Markdown", "attach the .md in your AI;", "it names anything left out")
    s.add(f'<rect class="pn" x="{PX}" y="{PY}" width="{PW}" height="{PH}" rx="6"/>'
          f'<text class="ld" x="{PX + 8}" y="{PY + 15}">Send the prompt to your AI</text>'
          f'<rect class="pr" x="{PX + 8}" y="{PY + 22}" width="{PW - 16}" height="14" rx="3"/>'
          f'<text class="bp" x="{W / 2}" y="{PY + 31.5}">{esc(SAVE)}</text>')
    s.press(PX + 8, PY + 22, PW - 16, 14, 0.7)
    fx, fy = PX + 10, PY + 46
    s.timed(f'<path class="fi" d="M{fx} {fy}h20l8 8v30h-28z"/><path class="fo" d="M{fx + 20} {fy}v8h8"/>'
            f'<text class="cl" x="{fx + 14}" y="{fy + 24}">.md</text>'
            f'<text class="o" x="{fx + 36}" y="{fy + 12}">All 75 cards and every</text>'
            f'<text class="o" x="{fx + 36}" y="{fy + 20}">part you switched on,</text>'
            f'<text class="o" x="{fx + 36}" y="{fy + 28}">in one file</text>', 1.1)
    note = wrap("With every layer on, a full Opening of the Key comes close to the most some AIs "
                "will read. If one runs over, the prompt drops the gods first, then the angels and "
                "decan dates, and names them under:", 36)
    ny = PY + 88
    s.timed(f'<rect class="hn" x="{PX + 8}" y="{ny}" width="{PW - 16}" height="{14 + 7 * len(note)}" rx="2"/>'
            f'<rect x="{PX + 8}" y="{ny}" width="2" height="{14 + 7 * len(note)}" fill="{WARN}"/>'
            + "".join(f'<text class="sub" x="{PX + 13}" y="{ny + 7 + 7 * j}">{esc(t)}</text>'
                      for j, t in enumerate(note))
            + f'<text class="o bo" x="{PX + 13}" y="{ny + 9 + 7 * len(note)}">Left Out to Fit</text>', 2.4)
    s.timed(f'<text class="sub" x="{W / 2}" y="{PY + PH - 10}" style="text-anchor:middle;fill:{LINE}">'
            f'Then attach it in your AI with +</text>', 4.0)

    end = a.t - FADE - 0.1
    cycle = end + FADE + 0.4
    last = len(a.scenes) - 1
    font = "Inter,system-ui,sans-serif"
    css = (
        f".bg{{fill:#2E8A56}}text{{fill:{CREAM}}}.t,.h,.n,.b,.bp,.cl,.rt{{text-anchor:middle}}"
        f".pn{{fill:{INK};fill-opacity:.32;stroke:{LINE};stroke-opacity:.35}}"
        f".fd{{fill:{CREAM};fill-opacity:.1;stroke:{LINE};stroke-opacity:.45;stroke-width:.6}}"
        f".hn{{fill:{INK};fill-opacity:.35}}"
        f".bt{{fill:none;stroke:{CREAM};stroke-opacity:.6;stroke-width:.7}}"
        f".pr{{fill:{CREAM}}}.bp{{font:700 6.5px {font};fill:{INK}}}"
        f".fl{{fill:#fff;opacity:.45}}"
        f".rl{{fill:none;stroke:{CREAM};stroke-opacity:.45;stroke-width:.5}}.rc{{fill:{CREAM}}}"
        f".rt{{font:600 4.6px {font}}}.ri{{fill:{INK}}}"
        f".rb{{fill:none;stroke:{CREAM};stroke-width:.7}}.rd{{fill:{CREAM}}}"
        f".sel{{fill:#fff;fill-opacity:.14;stroke:#fff;stroke-width:.8}}"
        f".cx{{fill:none;stroke:{CREAM};stroke-width:.6}}"
        f".cb{{fill:{CREAM}}}.tk{{font:700 5px {font};fill:{INK};text-anchor:middle}}"
        f".cd{{fill:{CREAM};stroke:{INK};stroke-width:.5}}.cs{{fill:{WARN};stroke:{CREAM};stroke-width:.6}}"
        f".cl{{font:700 8px {font};fill:{INK}}}"
        f".fi{{fill:{CREAM}}}.fo{{fill:none;stroke:{INK};stroke-width:.7}}"
        f".sm{{font:600 6px {font};fill:{LINE}}}.lg{{font:600 6.2px {font};fill:{LINE}}}"
        f".ld{{font:700 7.5px {font}}}.hd{{font:700 5.2px {font};fill:{LINE};letter-spacing:.04em}}"
        f".o{{font:500 6px {font}}}.bo{{font-weight:700}}.v{{font:500 6.2px {font}}}"
        f".sub{{font:500 5.2px {font}}}.b{{font:600 6px {font}}}"
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
            f'<text class="t" x="{W / 2}" y="18">Drawing a full Opening of the Key</text>'
            + scenes + "".join(a.caps)
            + f'<text class="t" x="{W / 2}" y="278">Every correspondence switched on</text></svg>\n')


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")

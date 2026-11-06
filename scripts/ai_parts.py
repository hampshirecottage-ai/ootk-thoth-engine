#!/usr/bin/env python3
"""Which parts of the prompt does an AI actually use? A leave-one-out round.

The same readings go to an AI many times: once with the full prompt, once with each part
switched off (report.COMPONENTS, the site's "Parts of the AI prompt"), and once with the
correspondences scrambled (each card keeps its name, suit and number but carries another
card's correspondences, so the tables are consistent with each other and wrong for the cards).
Plain code then compares the answers. No AI judges them, and nothing here says whether
readings predict anything.

For each part it reports:
- uses: how often the full answers mention that part's terms (dignities, sign names, Hebrew
  letters, Sephiroth, geomantic figures, angels...), per answer;
- left on: mentions that remain with the part switched off, i.e. supplied from the AI's own
  knowledge (or terms the part shares with another part);
- change, read from each answer's closing summary and recap (where the prompt asks for the
  outcome), against how much two full answers to the same prompt differ (the repeat noise):
  - summary: how different its words are;
  - cards named: how different the set of drawn cards it names is;
  - lean: how often it leans the same way (go ahead / wait) as the full answers.
  A part whose removal changes these no more than a repeat does is one the AI does not lean on.
Scrambled answers also count how often the AI says something does not match.

Birth and year cards are added rather than switched off: they appear only when a birth date is
given, so each reading also goes out once with a fixed birth date ("birth" variant), compared
with the full answers the same way. Running `round` again on a folder from an earlier round
adds just those prompts and sends just their answers.

Usage (needs `pip install anthropic` and ANTHROPIC_API_KEY, like scripts/ai_score.py):
    python scripts/ai_parts.py round [--out output/ai_parts] [--model claude-haiku-5-5]
    python scripts/ai_parts.py build --out output/ai_parts/build     # prompts only, free
    python scripts/ai_parts.py report --out output/ai_parts          # report again, free
    python scripts/ai_parts.py lean --out output/ai_parts            # read each answer's lean (cents)

Each model needs its own --out folder (answers are saved by prompt and run, not by model).
The go-ahead / wait lean of each answer's closing summary is read by Haiku in a second small
batch (it sees only that part of the answer); without it, a keyword guess is used.

round builds the prompts, prints the estimated cost and asks before sending. It sends one
Message Batch (half price, usually done within an hour), saves its id, and waits; if it is
stopped, running it again picks the same batch up. Answers are readings, so keep --out
outside the repo (output/ is ignored).
"""
import argparse
import copy
import json
import os
import random
import re
import sys
import time
from datetime import date, datetime, timezone
from itertools import combinations

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_check import MAPPING, QUESTION, SEEDS, SIGNIFICATOR, card_names, load_reference  # noqa: E402
from ootk.analysis import withheld_summary  # noqa: E402
from ootk.birth_cards import birth_cards_param  # noqa: E402
from ootk.decans import ANGELS  # noqa: E402
from ootk.report import COMPONENTS, analyze_reading  # noqa: E402
from ootk.rules import GEOMANTIC_FIGURES  # noqa: E402
from ootk.shuffle import draw_spread, resolve_significator, significator_places  # noqa: E402
from ootk.spreads import SPREADS, ZODIAC_SIGNS, spread_positions  # noqa: E402

MODEL = "claude-haiku-5-5"
PRICES = {"claude-opus-5-5": (4.00, 20.00), "claude-sonnet-5-5": (2.00, 10.00), "claude-haiku-5-5": (0.10, 0.50)}
BATCH_DISCOUNT = 0.5
SPREAD_KEYS = ("9", "12")         # Houses, and the four-operation Opening of the Key
RUNS = 3                          # answers per prompt: the repeats measure the noise
DRAWN_AT = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)   # fixed, so the decan dates show
SCRAMBLE_SEED = 777
BIRTH_DATE = date(1985, 7, 14)    # any fixed date: birth card VIII Adjustment, year card XIII Death (2026)
ANSWER_TOKENS = {"9": 9_000, "12": 14_000}   # rough answer + thinking, for the estimate
KEEP = {"title", "card_id", "arcana_type", "suit", "number_or_rank"}
EFFORT = {"claude-sonnet-5-5": "medium", "claude-opus-5-5": "medium"}   # Haiku: its own default
LEAN_MODEL = "claude-haiku-5-5"
LEANS = {"go_ahead": 1, "wait": -1, "mixed": 0, "none": 0}
LEAN_SCHEMA = {"type": "object", "properties": {"lean": {"type": "string", "enum": list(LEANS)}},
               "required": ["lean"], "additionalProperties": False}
LEAN_ASK = """Below is the closing part of a tarot reading written for the question "{question}".
Which way does it lean? Answer with one of:
- go_ahead: it leans toward changing jobs this year
- wait: it leans toward not changing now (waiting, staying, holding off)
- mixed: it gives both sides without leaning either way
- none: it does not say which way

<reading_end>
{text}
</reading_end>"""

PLANETS = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")
LETTERS = ("Aleph", "Beth", "Gimel", "Daleth", "Heh", "Hé", "Vau", "Vav", "Zain", "Cheth", "Teth", "Yod",
           "Kaph", "Lamed", "Mem", "Nun", "Samekh", "Ayin", "Peh", "Pé", "Tzaddi", "Qoph", "Resh",
           "Shin", "Tau", "Tav")
SEPHIROTH = ("Kether", "Chokmah", "Binah", "Chesed", "Geburah", "Tiphareth", "Netzach", "Hod",
             "Yesod", "Malkuth")
FIGURES = sorted({f for v in GEOMANTIC_FIGURES.values() for f in v.split(" and ")})


def _words(*terms):
    return re.compile(r"\b(" + "|".join(re.escape(t) for t in terms) + r")\b", re.I)


# What an answer says when it uses a part. Some terms are shared (a sign belongs to astrology,
# a decan date to timing), so read "left on" with that in mind.
TERMS = {
    "elements": re.compile(r"\bdignit|\b(well|ill)[- ]dignified|\b(friendly|contrary|neutral) (pair|element)|"
                           r"\belemental (balance|dignit)", re.I),
    "astrology": _words(*ZODIAC_SIGNS, *PLANETS, "decan", "decans"),
    "hebrew": _words(*LETTERS),
    "tree": re.compile(r"\b(" + "|".join(SEPHIROTH) + r")\b|\bTree of Life\b|\bpath \d+|\bYetziratic\b|"
                       r"\b(King|Queen|Prince|Princess) Scale", re.I),
    "courts": re.compile(r"\b(Fire|Water|Air|Earth) of (Fire|Water|Air|Earth)\b", re.I),
    "numerology": re.compile(r"\bBook T count|\bcounts? of (Trumps|court|Aces)|\b(three|four) of a kind\b|"
                             r"\bbirth card|\byear card", re.I),
    "geomancy": re.compile(r"\bgeomant|\b(" + "|".join(re.escape(f) for f in FIGURES) + r")\b"),
    "geometry": re.compile(r"\bCube of Space\b|\bplatonic\b|\b(tetrahedron|octahedron|icosahedron|"
                           r"dodecahedron)\b|\b(trine|sextile|square|opposition|conjunction)s?\b", re.I),
    "gematria": re.compile(r"\bgematria\b|\bletter values?\b", re.I),
    "titles": re.compile(r"\bLord of\b|\bGolden Dawn titles?\b|\bDaughter of\b|\bSon of\b", re.I),
    "angels": re.compile(r"\bangels?\b|\b(" + "|".join(ANGELS) + r")\b", re.I),
    "timing": re.compile(r"\bday ruler\b|\bdecan dates?\b|\b\d{1,2} (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|"
                         r"Nov|Dec)[a-z]*\b", re.I),
    "gods": re.compile(r"\bgods?\b|\bgoddess", re.I),
    "hexagrams": re.compile(r"\bhexagrams?\b|\bI Ching\b", re.I),
    "solids": re.compile(r"\bplatonic\b|\b(tetrahedron|octahedron|icosahedron|dodecahedron)\b|\bdual\b", re.I),
    "cube_counts": re.compile(r"\bmother ax[ei]s\b|\bdouble directions?\b|\bsimple edges\b", re.I),
    "all_aspects": re.compile(r"\b(trine|sextile|square)s?\b", re.I),
    "hebrew_compare": re.compile(r"\bFrench\b|\bEgyptian\b|\bGolden Dawn letter", re.I),
    "statistics": re.compile(r"\bz ?=|\btrend test\b|\bat random\b|\bodds\b", re.I),
}
assert set(TERMS) == set(COMPONENTS)
BIRTH_TERMS = re.compile(r"\bbirth card|\byear card|\bpersonality card", re.I)
MISMATCH = re.compile(r"\b(does not|doesn't|do not|don't) match|\bmismatch|\binconsisten|\bnormally\b|"
                      r"\busually\b|\btraditionally\b|\berror\b|\bunusual attribution", re.I)


# --- prompts --------------------------------------------------------------------------------

def scramble(rows, seed=SCRAMBLE_SEED):
    """{title: row} where each card keeps its name, kind, suit and number but takes every other
    field from another card of the same kind and suit (a Trump from another Trump)."""
    rnd = random.Random(seed)
    groups = {}
    for title, row in sorted(rows.items()):
        groups.setdefault((row["arcana_type"], row["suit"]), []).append(title)
    out = {}
    for titles in groups.values():
        donors = titles[:]
        while len(titles) > 1 and any(a == b for a, b in zip(titles, donors)):
            rnd.shuffle(donors)
        for title, donor in zip(titles, donors):
            row = copy.deepcopy(rows[donor])
            row.update({k: rows[title][k] for k in KEEP if k in rows[title]})
            out[title] = row
    return out


def build_prompt(ref, seed, spread_key, without=frozenset(), rows=None, birth_cards=""):
    """The prompt the site would build for this draw, with `without` switched off, the card
    rows taken from `rows` (scrambled ones) when given, and `birth_cards` ("16-14-2026") added
    when given. The cards drawn never change."""
    rows = rows or ref["rows"]
    deck = ref["deck"]
    positions = spread_positions(spread_key)
    sig_card = resolve_significator(deck, SIGNIFICATOR)
    titles, pinned = draw_spread(deck, seed, positions, sig_card)
    spread_results = [{"position_number": i, "position_name": name, "card_data": copy.deepcopy(rows[title])}
                      for i, (name, title) in enumerate(zip(positions, titles), start=1)]
    withheld = withheld_summary([rows[c["title"]] for c in deck], titles)
    significator = sig_card["title"] if pinned else "None (spread has no significator position)"
    reading = analyze_reading(SPREADS[spread_key]["name"], spread_key, QUESTION, significator, seed,
                              spread_results, mapping_system=MAPPING, withheld=withheld,
                              significator_places=significator_places(deck, seed, positions, sig_card),
                              drawn_at=DRAWN_AT, local_zone=timezone.utc, without=frozenset(without),
                              birth_cards=birth_cards)
    return reading["analytical_prompt"]


def build(out, ref=None):
    """Writes prompts/<case>.md and cases.json. A part that changes nothing for a reading (no
    court card, so no hexagrams; already left out to fit) gets no prompt of its own there."""
    ref = ref or load_reference()
    os.makedirs(os.path.join(out, "prompts"), exist_ok=True)
    scrambled_rows = scramble(ref["rows"])
    cases, skipped = [], []
    for seed in SEEDS:
        for key in SPREAD_KEYS:
            full = build_prompt(ref, seed, key)
            variants = [("full", full)]
            for part in COMPONENTS:
                cut = build_prompt(ref, seed, key, {part})
                if cut == full:
                    skipped.append(f"s{seed}_sp{key}_no-{part}")
                else:
                    variants.append((f"no-{part}", cut))
            variants.append(("scrambled", build_prompt(ref, seed, key, rows=scrambled_rows)))
            variants.append(("birth", build_prompt(ref, seed, key, birth_cards=BIRTH_CARDS)))
            for variant, prompt in variants:
                case_id = f"s{seed}_sp{key}_{variant}"
                with open(os.path.join(out, "prompts", f"{case_id}.md"), "w", encoding="utf-8") as f:
                    f.write(prompt)
                cases.append({"id": case_id, "seed": seed, "spread": key, "variant": variant, "chars": len(prompt)})
    with open(os.path.join(out, "cases.json"), "w", encoding="utf-8") as f:
        json.dump({"cases": cases, "no_change": skipped}, f, indent=1)
    return cases, skipped


BIRTH_CARDS = birth_cards_param(BIRTH_DATE, DRAWN_AT.date())


def add_birth(build_dir, ref=None):
    """Adds the "birth" variant to a build folder from a round made before it existed, leaving
    every other prompt as it is. Returns how many prompts were added."""
    path = os.path.join(build_dir, "cases.json")
    with open(path, encoding="utf-8") as f:
        info = json.load(f)
    have = {c["id"] for c in info["cases"]}
    readings = sorted({(c["seed"], c["spread"]) for c in info["cases"]})
    added = 0
    for seed, key in readings:
        case_id = f"s{seed}_sp{key}_birth"
        if case_id in have:
            continue
        ref = ref or load_reference()
        prompt = build_prompt(ref, seed, key, birth_cards=BIRTH_CARDS)
        with open(os.path.join(build_dir, "prompts", f"{case_id}.md"), "w", encoding="utf-8") as f:
            f.write(prompt)
        info["cases"].append({"id": case_id, "seed": seed, "spread": key, "variant": "birth", "chars": len(prompt)})
        added += 1
    if added:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(info, f, indent=1)
    return added


# --- sending --------------------------------------------------------------------------------

def estimate(cases, model, runs=RUNS):
    price_in, price_out = PRICES[model]
    total = sum(runs * (c["chars"] / 3.2 * price_in + ANSWER_TOKENS[c["spread"]] * price_out) / 1e6 for c in cases)
    return total * BATCH_DISCOUNT


def custom_id(case_id, run):
    return f"{case_id}__{run}"


def requests_for(build_dir, cases, model, answers, runs=RUNS):
    reqs = []
    for c in cases:
        prompt = None
        for n in range(1, runs + 1):
            if os.path.exists(os.path.join(answers, f"{custom_id(c['id'], n)}.md")):
                continue
            if prompt is None:
                with open(os.path.join(build_dir, "prompts", f"{c['id']}.md"), encoding="utf-8") as f:
                    prompt = f.read()
            # A fresh conversation, no system prompt: what a visitor does when they paste it.
            params = {"model": model, "max_tokens": 32000, "messages": [{"role": "user", "content": prompt}]}
            if EFFORT.get(model):
                params["output_config"] = {"effort": EFFORT[model]}
            reqs.append({"custom_id": custom_id(c["id"], n), "params": params})
    return reqs


def collect(client, batch_id, answers, model):
    """Saves each finished answer as <case>__<run>.md; returns (saved, failed, dollars)."""
    price_in, price_out = PRICES[model]
    saved, failed, spent = 0, [], 0.0
    for result in client.messages.batches.results(batch_id):
        if result.result.type != "succeeded":
            failed.append(f"{result.custom_id}: {result.result.type}")
            continue
        msg = result.result.message
        spent += (msg.usage.input_tokens * price_in + msg.usage.output_tokens * price_out) / 1e6 * BATCH_DISCOUNT
        text = "".join(b.text for b in msg.content if b.type == "text")
        if msg.stop_reason == "refusal" or not text.strip():
            failed.append(f"{result.custom_id}: no answer ({msg.stop_reason})")
            continue
        with open(os.path.join(answers, f"{result.custom_id}.md"), "w", encoding="utf-8") as f:
            f.write(text)
        saved += 1
    return saved, failed, spent


def make_client():
    try:
        import anthropic
    except ImportError:
        sys.exit("This needs the anthropic package: .venv/bin/python -m pip install anthropic")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Set your key first, in this Terminal window only: export ANTHROPIC_API_KEY=sk-ant-...")
    return anthropic.Anthropic()


def wait_for(client, batch_id, wait):
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        if batch.processing_status == "ended":
            return
        counts = batch.request_counts
        print(f"{time.strftime('%H:%M')} still working: {counts.processing} to go, {counts.succeeded} done")
        time.sleep(wait)


def answer_paths(answers):
    return sorted(p for p in os.listdir(answers) if re.fullmatch(r"s\d+_sp\d+_.+__\d+\.md", p))


def lean_requests(answers):
    """One short classification per answer that has no <answer>.lean.json yet: which way its
    closing summary leans. A small AI reads only that part, never the prompt."""
    reqs = []
    for path in answer_paths(answers):
        if os.path.exists(os.path.join(answers, path[:-3] + ".lean.json")):
            continue
        with open(os.path.join(answers, path), encoding="utf-8") as f:
            tail = summary(f.read())[-8000:]
        reqs.append({"custom_id": path[:-3], "params": {
            "model": LEAN_MODEL, "max_tokens": 4000,
            "output_config": {"effort": "low", "format": {"type": "json_schema", "schema": LEAN_SCHEMA}},
            "messages": [{"role": "user", "content": LEAN_ASK.format(question=QUESTION, text=tail)}]}})
    return reqs


def leans(out, ask=input, client=None, wait=60):
    """Reads the lean of every answer that has none yet, as one Haiku batch (a few cents)."""
    answers = os.path.join(out, "answers")
    batch_file = os.path.join(out, "lean_batch.json")
    client = client or make_client()
    if os.path.exists(batch_file):
        with open(batch_file, encoding="utf-8") as f:
            batch_id = json.load(f)["id"]
        print(f"Picking up lean batch {batch_id}.")
    else:
        reqs = lean_requests(answers)
        if not reqs:
            return 0
        if ask is not None and ask(f"Read the lean of {len(reqs)} answers with {LEAN_MODEL}: about "
                                   f"${len(reqs) * 0.0004:.2f}. Go ahead? [y/N] ").strip().lower() != "y":
            print("Nothing sent.")
            return 0
        batch_id = client.messages.batches.create(requests=reqs).id
        with open(batch_file, "w", encoding="utf-8") as f:
            json.dump({"id": batch_id}, f)
        print(f"Sent lean batch {batch_id}.")
    wait_for(client, batch_id, wait)
    saved = 0
    for result in client.messages.batches.results(batch_id):
        if result.result.type != "succeeded":
            continue
        text = next((b.text for b in result.result.message.content if b.type == "text"), "")
        try:
            value = json.loads(text)["lean"]
        except (ValueError, KeyError, TypeError):
            continue
        if value in LEANS:
            with open(os.path.join(answers, f"{result.custom_id}.lean.json"), "w", encoding="utf-8") as f:
                json.dump({"lean": value}, f)
            saved += 1
    os.remove(batch_file)
    print(f"Read the lean of {saved} answers.")
    return saved


def round_(out, model=MODEL, ask=input, client=None, wait=60):
    build_dir, answers = os.path.join(out, "build"), os.path.join(out, "answers")
    os.makedirs(answers, exist_ok=True)
    batch_file = os.path.join(out, "batch.json")
    if not os.path.exists(os.path.join(build_dir, "cases.json")):
        build(build_dir)
    elif not os.path.exists(batch_file) and add_birth(build_dir):
        print("Added the birth card prompts to this folder's earlier round.")
    with open(os.path.join(build_dir, "cases.json"), encoding="utf-8") as f:
        cases = json.load(f)["cases"]
    client = client or make_client()
    if os.path.exists(batch_file):
        with open(batch_file, encoding="utf-8") as f:
            batch_id = json.load(f)["id"]
        print(f"Picking up batch {batch_id}.")
    else:
        reqs = requests_for(build_dir, cases, model, answers)
        if not reqs:
            print("Every answer is already saved.")
            leans(out, ask=ask, client=client, wait=wait)
            return report(out)
        dollars = estimate([c for c in cases if any(r["custom_id"].startswith(c["id"] + "__") for r in reqs)], model)
        if ask(f"{len(reqs)} answers from {model}, sent as one batch at half price: roughly "
               f"${dollars:.2f}. Go ahead? [y/N] ").strip().lower() != "y":
            print("Nothing sent.")
            return None
        batch = client.messages.batches.create(requests=reqs)
        batch_id = batch.id
        with open(batch_file, "w", encoding="utf-8") as f:
            json.dump({"id": batch_id, "model": model, "requests": len(reqs)}, f)
        print(f"Sent batch {batch_id}. It usually finishes within an hour; this waits for it "
              "(you can stop and run the same command again later).")
    wait_for(client, batch_id, wait)
    saved, failed, spent = collect(client, batch_id, answers, model)
    os.remove(batch_file)
    print(f"Saved {saved} answers, about ${spent:.2f}." + (f" {len(failed)} failed:" if failed else ""))
    for line in failed:
        print("  " + line)
    leans(out, ask=None, client=client, wait=wait)      # a few cents, covered by the go-ahead above
    return report(out)


# --- report ---------------------------------------------------------------------------------

def mentions(text):
    return {part: len(rx.findall(text)) for part, rx in TERMS.items()}


STOP = set("""that this with from have will your into they them their there what when where which
while about would could should these those than then been being more most some such only also
very just over even much many each other your yours here like make made does doing""".split())
SUMMARY_HEAD = re.compile(r"^[ \t]*(#+|\*\*).*\b(summary|recap|synthesis)\b", re.I | re.M)
POSITIVE = re.compile(r"\b(yes|go ahead|favou?rable|move forward|make the (change|move|leap)|take the (leap|step|job)|"
                      r"green light|worth (it|making|taking)|time to (change|move|go)|supports? (a |the )?change)\b", re.I)
CAUTION = re.compile(r"\b(not yet|wait|hold off|hold back|delay|stay put|stay where|caution|cautious|"
                     r"unfavou?rable|not the right time|too soon|reconsider|hesitat\w*|premature)\b", re.I)


def word_set(text):
    return {w for w in re.findall(r"[a-z][a-z'-]{3,}", text.lower()) if w not in STOP}


def summary(answer):
    """The closing summary and recap: from the first summary/recap heading to the end, or the
    last quarter of the answer when it has no such heading."""
    m = SUMMARY_HEAD.search(answer)
    return answer[m.start():] if m else answer[len(answer) * 3 // 4:]


def lean(text):
    """+1 leans toward going ahead, -1 toward waiting, 0 neither or both equally."""
    pos, neg = len(POSITIVE.findall(text)), len(CAUTION.findall(text))
    return (pos > neg) - (neg > pos)


def card_patterns(ref):
    """{title: regex} matching a card's Thoth or Waite names (not its bare title word)."""
    out = {}
    for card in ref["deck"]:
        names = [n for n, kind in card_names(card["title"]) if kind != "short"]
        out[card["title"]] = re.compile("|".join(r"\b" + re.escape(n) + r"\b" for n in names), re.I)
    return out


def cards_named(text, patterns):
    return {title for title, rx in patterns.items() if rx.search(text)}


def set_distance(a, b):
    return 1 - len(a & b) / len(a | b) if a | b else 0.0


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else None


def report(out):
    build_dir, answers = os.path.join(out, "build"), os.path.join(out, "answers")
    with open(os.path.join(build_dir, "cases.json"), encoding="utf-8") as f:
        info = json.load(f)
    patterns = card_patterns(load_reference())
    texts = {}
    for path in sorted(os.listdir(answers)):
        m = re.fullmatch(r"(s\d+_sp\d+)_(.+)__(\d+)\.md", path)
        if m:
            with open(os.path.join(answers, path), encoding="utf-8") as f:
                text = f.read()
            tail = summary(text)
            lean_path = os.path.join(answers, path[:-3] + ".lean.json")
            if os.path.exists(lean_path):
                with open(lean_path, encoding="utf-8") as f:
                    value, read_by_ai = LEANS[json.load(f)["lean"]], True
            else:
                value, read_by_ai = lean(tail), False
            texts.setdefault((m[1], m[2]), []).append(
                {"text": text, "words": word_set(tail), "cards": cards_named(tail, patterns), "lean": value,
                 "lean_by_ai": read_by_ai})
    readings = sorted({r for r, _ in texts})
    full = {r: texts.get((r, "full"), []) for r in readings}

    def pairs(variant):
        if variant == "full":
            return [(a, b) for r in readings for a, b in combinations(full[r], 2)]
        return [(v, f) for r in readings for v in texts.get((r, variant), []) for f in full[r]]

    def measures(variant):
        ps = pairs(variant)
        if not ps:
            return None
        return (mean(set_distance(a["words"], b["words"]) for a, b in ps),
                mean(set_distance(a["cards"], b["cards"]) for a, b in ps),
                mean(a["lean"] == b["lean"] for a, b in ps))

    noise = measures("full")
    full_uses = {part: mean(mentions(a["text"])[part] for r in readings for a in full[r]) for part in COMPONENTS}
    leans = [a["lean"] for r in readings for a in full[r]]
    all_answers = [a for v in texts.values() for a in v]
    by_ai = sum(a["lean_by_ai"] for a in all_answers)
    lines = ["# Which parts of the prompt the AI uses", "",
             f"{len(all_answers)} answers, compared on their closing summary and recap. Lean read by "
             + (f"{LEAN_MODEL} for {by_ai} of them, by keywords for the rest." if by_ai else "keywords only.")]
    if noise is None:
        text = "\n".join(lines + ["", "No full answers yet."]) + "\n"
        print(text)
        return text
    lines += [f"Repeat noise (two full answers to the same prompt): summary words **{noise[0]:.2f}**, "
              f"cards named **{noise[1]:.2f}**, same lean **{noise[2]:.0%}**. Full answers lean go-ahead "
              f"{leans.count(1)}, wait {leans.count(-1)}, neither {leans.count(0)}.", "",
              "| Part | Uses (full) | Left on (part off) | Summary words | Cards named | Same lean as full | Readings |",
              "|---|---|---|---|---|---|---|"]
    rows = []
    for part, name in COMPONENTS.items():
        variant = f"no-{part}"
        offs = [a for r in readings for a in texts.get((r, variant), [])]
        n_readings = sum(1 for r in readings if texts.get((r, variant)))
        m = measures(variant)
        if not offs or m is None:
            rows.append((None, f"| {name} | {full_uses[part]:.1f} | - | - | - | - | 0 (no change to the prompt) |"))
            continue
        left = mean(mentions(a["text"])[part] for a in offs)
        score = (m[0] - noise[0]) + (m[1] - noise[1]) + (noise[2] - m[2])
        rows.append((score, f"| {name} | {full_uses[part]:.1f} | {left:.1f} | {m[0] - noise[0]:+.2f} | "
                            f"{m[1] - noise[1]:+.2f} | {m[2]:.0%} | {n_readings} |"))
    lines += [row for _, row in sorted(rows, key=lambda r: (r[0] is None, -(r[0] or 0)))]
    births = [a for r in readings for a in texts.get((r, "birth"), [])]
    m = measures("birth")
    if births and m:
        named = mean(len(BIRTH_TERMS.findall(a["text"])) for a in births)
        lines += ["", f"**Birth and year cards added** (born {BIRTH_DATE.isoformat()}): summary words "
                      f"{m[0] - noise[0]:+.2f}, cards named {m[1] - noise[1]:+.2f}, same lean {m[2]:.0%} "
                      f"({sum(1 for r in readings if texts.get((r, 'birth')))} readings); birth or year card "
                      f"mentioned {named:.1f} times per answer."]
    scr = [a for r in readings for a in texts.get((r, "scrambled"), [])]
    m = measures("scrambled")
    if scr and m:
        flags = mean(len(MISMATCH.findall(a["text"])) for a in scr)
        base = mean(len(MISMATCH.findall(a["text"])) for r in readings for a in full[r])
        lines += ["", f"**Scrambled correspondences:** summary words {m[0] - noise[0]:+.2f}, cards named "
                      f"{m[1] - noise[1]:+.2f}, same lean {m[2]:.0%}; 'does not match' words per answer "
                      f"{flags:.1f} (full answers: {base:.1f})."]
    if info.get("no_change"):
        lines += ["", "Parts that changed nothing for a reading, so were not sent: "
                  + ", ".join(info["no_change"]) + "."]
    lines += ["", "Summary words and cards named are distances over the repeat noise: 0 means switching the "
              "part off changed the summary no more than asking again did; higher means it changed more. "
              "Same lean is how often an answer leans the same way as a full answer (compare with the noise "
              "line). Uses and left on are term counts per whole answer. Rows are ordered by how much they "
              "change, most first."]
    text = "\n".join(lines) + "\n"
    with open(os.path.join(out, "results.md"), "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    return text


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("round", help="build, send one batch (asks first), wait, report")
    p.add_argument("--out", default=os.path.join("output", "ai_parts"))
    p.add_argument("--model", default=MODEL, choices=sorted(PRICES))
    p = sub.add_parser("build", help="write the prompts only (free)")
    p.add_argument("--out", default=os.path.join("output", "ai_parts", "build"))
    p = sub.add_parser("lean", help="read each saved answer's lean with Haiku (a few cents), then report")
    p.add_argument("--out", default=os.path.join("output", "ai_parts"))
    p = sub.add_parser("report", help="write results.md from the saved answers (free)")
    p.add_argument("--out", default=os.path.join("output", "ai_parts"))
    args = parser.parse_args(argv)
    if args.command == "round":
        round_(args.out, args.model)
    elif args.command == "lean":
        leans(args.out)
        report(args.out)
    elif args.command == "build":
        cases, skipped = build(args.out)
        print(f"{len(cases)} prompts ({len(skipped)} switches changed nothing for a reading), "
              f"{sum(c['chars'] for c in cases):,} characters. Estimate with {MODEL}: "
              f"${estimate(cases, MODEL):.2f}")
    else:
        report(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

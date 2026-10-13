#!/usr/bin/env python3
"""Builds the prompt set for checking what AIs write back from the OOTK prompt.

Step 1 of the AI answer check: no AI is called and nothing costs money. For a fixed set of
seeds and spreads it writes each prompt exactly as the site would build it, plus a truth file
holding everything the engine knows about that reading (cards, correspondences, dignities,
aspects, framework, Own-Place Check, where the Significator falls), so a later step can score
an AI's answer against it with plain code.

Usage:
    python scripts/ai_check.py build --out ai_check/2026-10-13

Writes, under --out:
    cases.json            one row per prompt: id, seed, spread, variant, files, size
    deck.json             all 78 cards with their facts and every name an AI might use for them
    prompts/<id>.md       the prompt to send
    truth/<id>.json       what the engine knows about that prompt's reading

Variants (see /mnt/project-files/reviews/ai-answer-testing-2026-10-13/plan.md):
    full        the prompt as the site builds it
    cut40/cut85 the OOTK prompt cut at 40% / 85% of its length (does the AI notice?)
    planted     one card's sign changed in section 1 only (does the AI flag it, per rule 2?)
    cardsonly   header, cards and the closing rules, no sections 2-6 (do the tables matter?)

The card rows come from tests/fixtures/reference_cards.json, so no database is needed, and
the full prompts match tests/test_prompt_snapshots.py for the same seed and settings.
Answers are readings, so keep the output out of the repo (output/ and reports/ are ignored).
"""
import argparse
import copy
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from ootk.analysis import derive_primary_element, withheld_summary  # noqa: E402
from ootk.report import CARDS, ELEMENTS, SPATIAL, analyze_reading, end_of_prompt_marker  # noqa: E402
from ootk.shuffle import draw_spread, operation_number, resolve_significator, significator_places  # noqa: E402
from ootk.spreads import SPREADS, ZODIAC_SIGNS, spread_positions  # noqa: E402
from ootk.visual import RWS_COURTS, RWS_SUITS, RWS_TRUMPS  # noqa: E402

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "reference_cards.json")

# 408850 is the snapshot seed; the others were picked by pick_seeds() so that between them the
# set holds every framework, an unusual Own-Place result and a Significator among the printed
# cards of a later operation (see coverage() for what each one adds).
SEEDS = ("408850", "100020", "100126", "100000")
# The smallest prompt, a line, the paths of the Tree, a wheel with the Own-Place Check, and the
# full four-operation Opening of the Key.
SPREAD_KEYS = ("1", "3", "7", "9", "12")
QUESTION = "Should I change jobs this year?"
NO_QUESTION_SEED = "100000"            # one reading per spread without a question
SIGNIFICATOR = "Queen of Cups"
MAPPING = "thoth"
CUTS = (("cut40", "408850", 0.40), ("cut85", "408850", 0.85), ("cut85", "100020", 0.85))
PLANTED_SEED = "408850"
CARDS_ONLY = tuple((key, seed) for key in ("9", "12") for seed in SEEDS)   # Houses and OOTK: 8 prompts

FRAMEWORKS = ("Divine Light Flow", "Incarnational Life Path", "Post-Mortem Return")
NUMBER_WORDS = {"2": "Two", "3": "Three", "4": "Four", "5": "Five", "6": "Six", "7": "Seven",
                "8": "Eight", "9": "Nine", "10": "Ten"}
_SECTION = re.compile(r"^## (\d+)\. ", re.M)
_POSITION = re.compile(r"^### Position (\d+):", re.M)


def load_reference():
    with open(FIXTURE, encoding="utf-8") as f:
        return json.load(f)


# --- the reading, built the same way as tests/test_prompt_snapshots.py --------------------

def build_reading(ref, seed, spread_key, question=QUESTION):
    """(reading, positions, titles, significator title or None, withheld) for one draw."""
    deck = ref["deck"]
    positions = spread_positions(spread_key)
    sig_card = resolve_significator(deck, SIGNIFICATOR)
    titles, pinned = draw_spread(deck, seed, positions, sig_card)
    spread_results = [
        {"position_number": i, "position_name": name, "card_data": copy.deepcopy(ref["rows"][title])}
        for i, (name, title) in enumerate(zip(positions, titles), start=1)
    ]
    withheld = withheld_summary([ref["rows"][c["title"]] for c in deck], titles)
    significator = sig_card["title"] if pinned else "None (spread has no significator position)"
    reading = analyze_reading(SPREADS[spread_key]["name"], spread_key, question, significator, seed,
                              spread_results, mapping_system=MAPPING, withheld=withheld,
                              significator_places=significator_places(deck, seed, positions, sig_card))
    return reading, positions, titles, (sig_card["title"] if pinned else None), withheld


# --- every name an AI might use for a card -------------------------------------------------

def card_names(title):
    """[(name, kind)] for one card. kind: thoth (its name here), waite (the Rider-Waite name,
    another deck), short (a Thoth title word such as 'Truce' or 'Lust', which can also be an
    ordinary word, so a scorer should only count it next to a card cue)."""
    names = [(title, "thoth")]
    m = re.fullmatch(r"(\d+) of (\w+) - (.+)", title)
    if m:
        num, suit, word = m.groups()
        names += [(f"{num} of {suit}", "thoth"), (f"{NUMBER_WORDS[num]} of {suit}", "thoth"), (word, "short")]
        if suit in RWS_SUITS:
            names += [(f"{num} of {RWS_SUITS[suit]}", "waite"), (f"{NUMBER_WORDS[num]} of {RWS_SUITS[suit]}", "waite")]
        return names
    m = re.fullmatch(r"Ace of (\w+)", title)
    if m:
        if m[1] in RWS_SUITS:
            names.append((f"Ace of {RWS_SUITS[m[1]]}", "waite"))
        return names
    m = re.fullmatch(r"(Knight|Queen|Prince|Princess) of (\w+)", title)
    if m:
        rank, suit = m.groups()
        waite_rank = RWS_COURTS.get(rank, rank)
        for s in {suit, RWS_SUITS.get(suit, suit)}:
            if (waite_rank, s) != (rank, suit):
                names.append((f"{waite_rank} of {s}", "waite"))
        return names
    m = re.fullmatch(r"([0IVXL]+) - (.+)", title)
    if m:
        numeral, name = m.groups()
        names.append((name, "thoth"))
        if name.startswith("The "):
            names.append((name[4:], "short"))
        names.append((f"Atu {numeral}", "thoth"))
        if title in RWS_TRUMPS:
            names.append((RWS_TRUMPS[title], "waite"))
        if name == "The Magus":
            names.append(("The Magician", "waite"))
        if name == "The Priestess":
            names.append(("The High Priestess", "waite"))
        if name == "Fortune":
            names.append(("Wheel of Fortune", "waite"))
    return names


def card_facts(row):
    """The facts a reading states about a card, from its fixture row (Thoth system)."""
    return {
        "title": row["title"], "arcana": row.get("arcana_type"), "suit": row.get("suit"),
        "element": derive_primary_element(row), "attribution": row.get("attribution"),
        "path_or_sephira": row.get("path_or_sephira"),
        "hebrew_letter": row.get("hebrew_letter"),
        "letters_by_system": {"thoth": row.get("thoth_hebrew_letter"), "golden_dawn": row.get("gd_hebrew_letter"),
                              "french_egyptian": row.get("french_hebrew_letter")},
        "spatial_type": row.get("spatial_type"), "spatial_dimension": row.get("spatial_dimension"),
        "platonic_solid": row.get("platonic_solid"), "king_scale_color": row.get("king_scale_color"),
    }


def deck_table(ref):
    """All 78 cards: facts and names. A Waite name that is also a Thoth title (the Waite Knight
    is the Thoth Prince) is listed under 'collisions': in an answer it means the Thoth card."""
    cards = {t: {**card_facts(row), "names": [{"name": n, "kind": k} for n, k in card_names(t)]}
             for t, row in sorted(ref["rows"].items())}
    thoth = {n["name"].lower() for c in cards.values() for n in c["names"] if n["kind"] == "thoth"}
    collisions = sorted({n["name"] for c in cards.values() for n in c["names"]
                         if n["kind"] == "waite" and n["name"].lower() in thoth})
    return {"mapping_system": MAPPING, "cards": cards, "collisions": collisions}


# --- truth for one reading -----------------------------------------------------------------

def _op(segment_name):
    m = re.match(r"Operation (\d+)", segment_name or "")
    return int(m[1]) if m else None


def truth_for(reading, positions, titles, significator, withheld, seed, spread_key, question, ref):
    dignities = [{"a": d["from_index"] + 1, "b": d["to_index"] + 1,
                  "cards": [titles[d["from_index"]], titles[d["to_index"]]],
                  "score": d["score"], "relationship": d["relationship"], "operation": _op(d.get("segment_name"))}
                 for d in reading["dignity_matrix"]]
    aspects, no_aspect = [], []
    for s in reading["spatial_matrix"] or ():
        pair = {"a": s["from_index"] + 1, "b": s["to_index"] + 1, "operation": _op(s.get("segment_name"))}
        if s.get("aspect_name"):
            aspects.append({**pair, "aspect": s["aspect_name"], "modifier": s["score_modifier"],
                            "card_score": s.get("card_score")})
        else:
            no_aspect.append({**pair, "kind": s.get("aspect")})
    scores = [d["score"] for d in dignities]
    chosen = reading["macro_framework"]
    sig_row = ref["rows"].get(significator) if significator else None
    return {
        "seed": seed, "spread_key": spread_key, "spread_name": SPREADS[spread_key]["name"],
        "question": question, "mapping_system": MAPPING,
        "significator": significator,
        "positions": [{"number": i, "name": re.sub(r"^\[Op \d+\] ", "", name), "operation": operation_number(name)
                       if name.startswith("[Op") else None, "card": title}
                      for i, (name, title) in enumerate(zip(positions, titles), start=1)],
        "cards": {t: card_facts(ref["rows"][t]) for t in dict.fromkeys(titles + ([significator] if sig_row else []))},
        "drawn": sorted(set(titles)),
        "withheld": [c.get("title", c) if isinstance(c, dict) else c for c in (withheld or {}).get("cards", [])],
        "element_counts": reading["element_counts"],
        "dignities": dignities,
        "strongest_pairs": [d for d in dignities if scores and d["score"] == max(scores)],
        "most_strained_pairs": [d for d in dignities if scores and d["score"] == min(scores) and min(scores) < max(scores)],
        "aspects": aspects,
        "pairs_without_aspect": no_aspect,
        "dual_pairings": reading["dual_pairings"],
        "framework": {"chosen": chosen, "basis": reading["framework_basis"],
                      "others": [f for f in FRAMEWORKS if f not in chosen]},
        "own_place": reading["own_place"] or [],
        "significator_places": reading["significator_places"],
        "end_marker": end_of_prompt_marker(len(titles)),
    }


# --- variants ------------------------------------------------------------------------------

def section_spans(prompt):
    """{section number: (start, end)} of each '## n.' section, end exclusive."""
    starts = [(int(m[1]), m.start()) for m in _SECTION.finditer(prompt)]
    return {n: (s, starts[i + 1][1] if i + 1 < len(starts) else len(prompt)) for i, (n, s) in enumerate(starts)}


def cut_prompt(prompt, fraction):
    """The prompt cut at the last line break before `fraction` of its length, and what the
    AI can still see: the last whole position block in section 1 and the section it ends in."""
    cut = prompt.rfind("\n", 0, int(len(prompt) * fraction)) + 1
    visible = prompt[:cut]
    spans = section_spans(prompt)
    in_section = max((n for n, (s, _) in spans.items() if s < cut), default=None)
    positions = [int(m[1]) for m in _POSITION.finditer(visible)]
    cards_end = spans[CARDS][1]
    last_whole = positions[-1] if cut >= cards_end else (positions[-2] if len(positions) > 1 else None)
    return visible, {"cut_at_chars": cut, "full_chars": len(prompt), "cut_in_section": in_section,
                     "last_whole_position": last_whole, "last_visible_line": visible.rstrip("\n").rsplit("\n", 1)[-1]}


def plant_error(prompt, truth):
    """Swaps the sign in one card's Attribution line in section 1 for the opposite sign, so the
    card disagrees with its own element and tradition, and the sections built from the real
    card (2-6) still use the true value. Picks the last position whose attribution names a
    sign. Returns (prompt, planted) or (prompt, None) when no card names a sign."""
    s, e = section_spans(prompt)[CARDS]
    blocks = list(_POSITION.finditer(prompt, s, e))
    for i in range(len(blocks) - 1, -1, -1):
        b_start, b_end = blocks[i].start(), (blocks[i + 1].start() if i + 1 < len(blocks) else e)
        block = prompt[b_start:b_end]
        m = re.search(r"^- \*\*Attribution\*\*: (.*)$", block, re.M)
        if not m:
            continue
        sign = next((x for x in ZODIAC_SIGNS if re.search(rf"\b{x}\b", m[1])), None)
        if not sign:
            continue
        wrong = ZODIAC_SIGNS[(ZODIAC_SIGNS.index(sign) + 6) % 12]
        new_line = re.sub(rf"\b{sign}\b", wrong, m[0], count=1)
        at = b_start + m.start()
        number = int(blocks[i][1])
        return prompt[:at] + new_line + prompt[at + len(m[0]):], {
            "position": number, "card": truth["positions"][number - 1]["card"], "field": "attribution",
            "true_value": m[1], "planted_value": new_line.split(": ", 1)[1],
            "true_sign": sign, "planted_sign": wrong}
    return prompt, None


def cards_only(prompt):
    """The header, section 1 and the closing rules, without sections 2-6 and without the
    rules that point into them. Positions and the end marker are unchanged."""
    spans = section_spans(prompt)
    header = prompt[:spans[CARDS][0]]
    cards = prompt[spans[CARDS][0]:spans[CARDS][1]]
    instructions = prompt[spans[SPATIAL + 1][0]:]
    rules = re.findall(r"^\d+\. \*\*(.+?):\*\* (.*)$", instructions, re.M)
    keep = [(name, text) for name, text in rules if name != "Suggested order"]
    keep.insert(3, ("Suggested order", "Take each position in turn (its name says what it stands for, "
                                       "and section 1 says which card fell there), then draw them together."))
    body = (f"## 2. SYNTHESIS & INTERPRETATION INSTRUCTIONS FOR LLM\n\n"
            "Act as an expert Hermetic scholar and Tarot authority. Interpret the reading from the "
            "cards above, following these rules:\n\n"
            + "".join(f"{i}. **{n}:** {t}\n" for i, (n, t) in enumerate(keep, start=1)))
    marker = prompt.rstrip("\n").rsplit("\n", 1)[-1]
    return header + cards + body + "\n" + marker + "\n"


# --- seeds ---------------------------------------------------------------------------------

def coverage(ref, seed):
    """The features one seed adds to the set, over SPREAD_KEYS."""
    found = set()
    for key in SPREAD_KEYS:
        reading, *_ = build_reading(ref, seed, key)
        for f in FRAMEWORKS:
            if f in reading["macro_framework"]:
                found.add(f"framework: {f}")
        if any(o["unusual"] for o in reading["own_place"] or ()):
            found.add(f"unusual own place (spread {key})")
        if any(p["shown"] for p in reading["significator_places"] if p["op"] > 1):
            found.add("significator printed in a later operation")
    return found


def pick_seeds(ref, first=SEEDS[0], count=4, start=100000, tries=400):
    """Greedy: after `first`, the seeds from start.. that add the most missing features."""
    chosen, have = [first], coverage(ref, first)
    candidates = [(str(start + i), coverage(ref, str(start + i))) for i in range(tries)]
    while len(chosen) < count:
        seed, feats = max(candidates, key=lambda c: (len(c[1] - have), -int(c[0])))
        chosen.append(seed)
        have |= feats
        candidates = [c for c in candidates if c[0] != seed]
    return chosen, have


# --- build ---------------------------------------------------------------------------------

def build(out, ref=None):
    ref = ref or load_reference()
    os.makedirs(os.path.join(out, "prompts"), exist_ok=True)
    os.makedirs(os.path.join(out, "truth"), exist_ok=True)
    cases = []

    def write(case_id, variant, prompt, truth, expect):
        truth = {"case_id": case_id, "variant": variant, **truth, "expect": expect}
        with open(os.path.join(out, "prompts", f"{case_id}.md"), "w", encoding="utf-8") as f:
            f.write(prompt)
        with open(os.path.join(out, "truth", f"{case_id}.json"), "w", encoding="utf-8") as f:
            json.dump(truth, f, ensure_ascii=False, indent=1)
        cases.append({"id": case_id, "variant": variant, "seed": truth["seed"], "spread": truth["spread_key"],
                      "question": bool(truth["question"]), "chars": len(prompt),
                      "prompt": f"prompts/{case_id}.md", "truth": f"truth/{case_id}.json"})

    full = {}
    for seed in SEEDS:
        question = "" if seed == NO_QUESTION_SEED else QUESTION
        for key in SPREAD_KEYS:
            reading, positions, titles, sig, withheld = build_reading(ref, seed, key, question)
            truth = truth_for(reading, positions, titles, sig, withheld, seed, key, question, ref)
            full[(seed, key)] = (reading["analytical_prompt"], truth)
            write(f"s{seed}_sp{key}_full", "full", reading["analytical_prompt"], truth,
                  {"cut_off": False, "planted": None})

    for variant, seed, fraction in CUTS:
        prompt, truth = full[(seed, "12")]
        visible, cut = cut_prompt(prompt, fraction)
        write(f"s{seed}_sp12_{variant}", variant, visible, truth, {"cut_off": True, **cut, "planted": None})

    for key in SPREAD_KEYS:
        prompt, truth = full[(PLANTED_SEED, key)]
        planted_prompt, planted = plant_error(prompt, truth)
        if planted:
            write(f"s{PLANTED_SEED}_sp{key}_planted", "planted", planted_prompt, truth,
                  {"cut_off": False, "planted": planted})

    for key, seed in CARDS_ONLY:
        prompt, truth = full[(seed, key)]
        write(f"s{seed}_sp{key}_cardsonly", "cardsonly", cards_only(prompt), truth,
              {"cut_off": False, "planted": None, "sections_left_out": list(range(ELEMENTS, SPATIAL + 1))})

    with open(os.path.join(out, "deck.json"), "w", encoding="utf-8") as f:
        json.dump(deck_table(ref), f, ensure_ascii=False, indent=1)
    with open(os.path.join(out, "cases.json"), "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=1)
    return cases


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="write the prompts and truth files")
    b.add_argument("--out", required=True, help="output folder (keep it out of the repo)")
    sub.add_parser("seeds", help="show what each seed adds, and the greedy pick")
    args = parser.parse_args(argv)
    if args.command == "seeds":
        ref = load_reference()
        for seed in SEEDS:
            print(seed, sorted(coverage(ref, seed)))
        print("greedy pick:", pick_seeds(ref))
        return 0
    cases = build(args.out)
    by_variant = {}
    for c in cases:
        by_variant[c["variant"]] = by_variant.get(c["variant"], 0) + 1
    print(f"{len(cases)} prompts in {args.out}: " + ", ".join(f"{n} {v}" for v, n in by_variant.items()))
    print(f"total {sum(c['chars'] for c in cases):,} characters")
    return 0


if __name__ == "__main__":
    sys.exit(main())

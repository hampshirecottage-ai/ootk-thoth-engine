#!/usr/bin/env python3
"""Does the lean prompt layout read as well as the full one? A side-by-side round.

The same Book T readings go to an AI in three forms, several times each:
- current: the prompt as the site built it before 2026-11-16 (full layout, no timing rule);
- timing:  the same prompt, with the Timeline rule naming Book T's timing card (the last small
           card on the closing operation's Count) and its decan window;
- lean:    the lean layout (report.LAYOUTS: positions one line each, the count and pairs next,
           each card's correspondences once) with that timing rule: the site's prompt now.
The cards, counts, pairs and scores are the same in all three (tests/test_lean_layout.py).
Plain code compares the answers. No AI judges them, and nothing here says whether a reading
comes true.

For each form it reports:
- prompt size (characters, and input tokens from the API);
- timing: how often the first Timeline line overlaps the timing card's window, and how often
  two answers to the same prompt give overlapping first windows (consistency);
- invented cards: cards named that were not drawn (by any name, Thoth or Waite);
- count coverage: share of the cards on the Counts that the answer names;
- lean: how often two answers to the same prompt lean the same way (go ahead / wait), read by
  Haiku from the closing part only (scripts/ai_parts.py), or a keyword guess without it;
- answer length, and any false "the prompt is cut off" claim.

Usage (needs `pip install anthropic` and ANTHROPIC_API_KEY, like scripts/ai_parts.py):
    python scripts/ai_lean.py build --out output/ai_lean/build          # prompts only, free
    python scripts/ai_lean.py round --out output/ai_lean_sonnet --model claude-sonnet-5-5
    python scripts/ai_lean.py report --out output/ai_lean_sonnet        # report again, free

round builds the prompts, prints the estimated cost and asks before sending one Message Batch
(half price). If it is stopped, running it again picks the same batch up. Each model needs its
own --out folder. Answers are readings, so keep --out outside the repo (output/ is ignored).
"""
import argparse
import copy
import json
import os
import re
import sys
from datetime import date, datetime, timezone
from itertools import combinations

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ai_parts  # noqa: E402
from ai_check import QUESTION, SEEDS, SIGNIFICATOR, card_names, load_reference  # noqa: E402
from ootk import book_t  # noqa: E402
from ootk.analysis import withheld_summary  # noqa: E402
from ootk.decans import decan_window  # noqa: E402
from ootk.report import analyze_reading, book_t_timing  # noqa: E402
from ootk.shuffle import resolve_significator  # noqa: E402
from ootk.spreads import BOOK_T_KEY, BOOK_T_SPREAD, spread_segments  # noqa: E402

MODEL = "claude-sonnet-5-5"
RUNS = 3
DRAWN_AT = datetime(2026, 11, 15, 20, 0, tzinfo=timezone.utc)   # fixed, so the dates are too
# What "Should I change jobs this year?" expects in Book T: the Yod pack (work), the 10th house
# or else the 6th, Capricorn, Tiphareth (as tests/test_prompt_snapshots.py).
EXPECT = "1,10/6,10,6"
# "current" is the prompt as it was before the lean layout became the default (2026-11-16).
VARIANTS = {"current": {"layout": "full", "timing_rule": False},
            "timing": {"layout": "full", "timing_rule": True},
            "lean": {"layout": "lean", "timing_rule": True}}
ANSWER_TOKENS = 14_000            # rough answer + thinking, for the estimate
DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")
CUT_CLAIM = re.compile(r"\b(cut off|truncated|is missing|incomplete prompt|rest of the prompt)\b", re.I)


# --- prompts --------------------------------------------------------------------------------

def reading(ref, seed, **settings):
    """(analyze_reading result, spread_results, ops) for one Book T draw."""
    deck = ref["deck"]
    sig = resolve_significator(deck, SIGNIFICATOR)
    ops = book_t.opening_of_the_key(deck, seed, sig, book_t.parse_expect(EXPECT))
    placed = book_t.positions(ops)
    results = [{"position_number": i, "position_name": name, "card_data": copy.deepcopy(ref["rows"][c["title"]])}
               for i, (name, c) in enumerate(placed, start=1)]
    withheld = withheld_summary([ref["rows"][c["title"]] for c in deck], [c["title"] for _, c in placed])
    out = analyze_reading(BOOK_T_SPREAD["name"], BOOK_T_KEY, QUESTION, sig["title"], seed, results,
                          withheld=withheld, book_t_ops=ops, drawn_at=DRAWN_AT, **settings)
    return out, results, ops


def truth(ref, seed):
    _, results, ops = reading(ref, seed)
    timing = book_t_timing(results, ops, DRAWN_AT)
    window = decan_window(timing["title"], DRAWN_AT) if timing else None
    read = [o for o in ops if o["status"] != "abandoned"]
    starts = [s for _, s, _, _ in spread_segments(results, BOOK_T_KEY)]
    counted = sorted({results[s + k]["card_data"]["title"] for o, s in zip(read, starts) for k in o["chain_at"]})
    return {"seed": seed, "drawn": sorted({r["card_data"]["title"] for r in results}),
            "counted": counted,
            "timing": timing and {"pos": timing["pos"], "card": timing["title"], "how": timing["how"],
                                  "start": window[0].date().isoformat(), "end": window[1].date().isoformat()}}


def build(out, ref=None):
    ref = ref or load_reference()
    os.makedirs(os.path.join(out, "prompts"), exist_ok=True)
    cases = []
    for seed in SEEDS:
        t = truth(ref, seed)
        for variant, settings in VARIANTS.items():
            prompt = reading(ref, seed, **settings)[0]["analytical_prompt"]
            case_id = f"s{seed}_sp{BOOK_T_KEY}_{variant}"
            with open(os.path.join(out, "prompts", f"{case_id}.md"), "w", encoding="utf-8") as f:
                f.write(prompt)
            cases.append({"id": case_id, "seed": seed, "variant": variant, "chars": len(prompt)})
        with open(os.path.join(out, f"truth_{seed}.json"), "w", encoding="utf-8") as f:
            json.dump(t, f, ensure_ascii=False, indent=1)
    with open(os.path.join(out, "cases.json"), "w", encoding="utf-8") as f:
        json.dump({"drawn_at": DRAWN_AT.isoformat(), "question": QUESTION, "cases": cases}, f, indent=1)
    return cases


def estimate(cases, model, runs=RUNS):
    price_in, price_out = ai_parts.PRICES[model]
    total = sum(runs * (c["chars"] / 3.2 * price_in + ANSWER_TOKENS * price_out) / 1e6 for c in cases)
    return total * ai_parts.BATCH_DISCOUNT


# --- the round ------------------------------------------------------------------------------

def collect(client, batch_id, answers, model):
    """ai_parts.collect, also keeping each answer's token counts."""
    usage = {}
    for result in client.messages.batches.results(batch_id):
        if result.result.type == "succeeded":
            u = result.result.message.usage
            usage[result.custom_id] = {"input": u.input_tokens, "output": u.output_tokens,
                                       "stop": result.result.message.stop_reason}
    path = os.path.join(answers, "usage.json")
    old = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    with open(path, "w", encoding="utf-8") as f:
        json.dump({**old, **usage}, f, indent=1)
    return ai_parts.collect(client, batch_id, answers, model)


def round_(out, model=MODEL, ask=input, client=None, wait=60, runs=RUNS):
    build_dir, answers = os.path.join(out, "build"), os.path.join(out, "answers")
    os.makedirs(answers, exist_ok=True)
    batch_file = os.path.join(out, "batch.json")
    if not os.path.exists(os.path.join(build_dir, "cases.json")):
        build(build_dir)
    with open(os.path.join(build_dir, "cases.json"), encoding="utf-8") as f:
        cases = json.load(f)["cases"]
    client = client or ai_parts.make_client()
    if os.path.exists(batch_file):
        with open(batch_file, encoding="utf-8") as f:
            batch_id = json.load(f)["id"]
        print(f"Picking up batch {batch_id}.")
    else:
        reqs = ai_parts.requests_for(build_dir, cases, model, answers, runs=runs)
        if reqs:
            todo = [c for c in cases if any(r["custom_id"].startswith(c["id"] + "__") for r in reqs)]
            if ask(f"{len(reqs)} answers from {model}, sent as one batch at half price: roughly "
                   f"${estimate(todo, model, runs):.2f}. Go ahead? [y/N] ").strip().lower() != "y":
                print("Nothing sent.")
                return None
            batch_id = client.messages.batches.create(requests=reqs).id
            with open(batch_file, "w", encoding="utf-8") as f:
                json.dump({"id": batch_id, "model": model, "requests": len(reqs)}, f)
            print(f"Sent batch {batch_id}. It usually finishes within an hour; this waits for it "
                  "(you can stop and run the same command again later).")
        else:
            batch_id = None
            print("Every answer is already saved.")
    if batch_id:
        ai_parts.wait_for(client, batch_id, wait)
        saved, failed, spent = collect(client, batch_id, answers, model)
        os.remove(batch_file)
        print(f"Saved {saved} answers, about ${spent:.2f}." + (f" {len(failed)} failed:" if failed else ""))
        for line in failed:
            print("  " + line)
    ai_parts.leans(out, ask=None, client=client, wait=wait)   # a few cents, covered by the go-ahead
    return report(out)


# --- report ---------------------------------------------------------------------------------

def timeline(answer):
    """[(start, end)] dates of each line under the answer's `## Timeline` heading."""
    m = re.search(r"^#+\s*Timeline\s*$(.*)", answer, re.M | re.S | re.I)
    if not m:
        return []
    spans = []
    for line in m[1].splitlines():
        if re.match(r"^#+\s", line):
            break
        days = DATE.findall(line)
        if days:
            spans.append((days[0], days[1] if len(days) > 1 else days[0]))
    return spans


def overlaps(a, b, slack=1):
    """Do two (start, end) ISO spans overlap, allowing `slack` days at either end?"""
    if not a or not b:
        return False
    a0, a1, b0, b1 = (date.fromisoformat(x).toordinal() for x in (*a, *b))
    return a0 <= b1 + slack and b0 <= a1 + slack


def score_answer(text, t, patterns, lean_file=None):
    spans = timeline(text)
    first = spans[0] if spans else None
    window = (t["timing"]["start"], t["timing"]["end"]) if t["timing"] else None
    named = ai_parts.cards_named(text, patterns)
    # A Waite name that is also a drawn card's Thoth name (the Thoth Knight is the Waite King,
    # the Thoth Prince the Waite Knight) names the drawn card, not another one.
    drawn_names = {t_.lower() for t_ in t["drawn"]}
    named = {c for c in named if c in t["drawn"] or not any(
        n.lower() in drawn_names for n, kind in card_names(c) if kind == "waite")}
    if lean_file and os.path.exists(lean_file):
        with open(lean_file, encoding="utf-8") as f:
            lean = ai_parts.LEANS[json.load(f)["lean"]]
    else:
        lean = ai_parts.lean(ai_parts.summary(text))
    return {"first": first, "lines": len(spans), "on_rule": overlaps(first, window),
            "rule_anywhere": any(overlaps(s, window) for s in spans),
            "invented": sorted(named - set(t["drawn"])),
            "count_coverage": len(named & set(t["counted"])) / len(t["counted"]) if t["counted"] else None,
            "lean": lean, "words": len(text.split()), "cut_claim": bool(CUT_CLAIM.search(text))}


def pct(x):
    return "-" if x is None else f"{x:.0%}"


def report(out):
    build_dir, answers = os.path.join(out, "build"), os.path.join(out, "answers")
    with open(os.path.join(build_dir, "cases.json"), encoding="utf-8") as f:
        cases = json.load(f)["cases"]
    usage_path = os.path.join(answers, "usage.json")
    usage = json.load(open(usage_path, encoding="utf-8")) if os.path.exists(usage_path) else {}
    patterns = ai_parts.card_patterns(load_reference())
    rows, detail = [], []
    for variant in VARIANTS:
        scored, chars, tokens, same_first, same_lean, invented = [], [], [], [], [], []
        for c in (c for c in cases if c["variant"] == variant):
            with open(os.path.join(build_dir, f"truth_{c['seed']}.json"), encoding="utf-8") as f:
                t = json.load(f)
            chars.append(c["chars"])
            these = []
            for name in sorted(os.listdir(answers)):
                if not re.fullmatch(re.escape(c["id"]) + r"__\d+\.md", name):
                    continue
                with open(os.path.join(answers, name), encoding="utf-8") as f:
                    s = score_answer(f.read(), t, patterns, os.path.join(answers, name[:-3] + ".lean.json"))
                these.append(s)
                if name[:-3] in usage:
                    tokens.append(usage[name[:-3]]["input"])
                invented += s["invented"]
                detail.append(f"| {name[:-3]} | {s['first'] and ' to '.join(s['first']) or 'none'} | "
                              f"{'yes' if s['on_rule'] else 'no'} | {s['lines']} | {pct(s['count_coverage'])} | "
                              f"{', '.join(s['invented']) or '-'} | {s['lean']:+d} | {s['words']} |")
            for a, b in combinations(these, 2):
                same_first.append(overlaps(a["first"], b["first"]))
                same_lean.append(a["lean"] == b["lean"])
            scored += these
        rows.append(f"| {variant} | {ai_parts.mean(chars) or 0:,.0f} | "
                    f"{(f'{ai_parts.mean(tokens):,.0f}' if tokens else '-')} | {len(scored)} | "
                    f"{pct(ai_parts.mean(s['on_rule'] for s in scored))} | {pct(ai_parts.mean(same_first))} | "
                    f"{pct(ai_parts.mean(s['count_coverage'] for s in scored if s['count_coverage'] is not None))} | "
                    f"{len(invented)} | {pct(ai_parts.mean(same_lean))} | "
                    f"{ai_parts.mean(s['words'] for s in scored) or 0:,.0f} | {sum(s['cut_claim'] for s in scored)} |")
    md = ("# Lean prompt round\n\n"
          "| Form | Prompt chars | Input tokens | Answers | First Timeline line on the timing card | "
          "Repeats give the same first window | Count cards named | Invented cards | Repeats lean the same way | "
          "Words | Says cut off |\n|---|---|---|---|---|---|---|---|---|---|---|\n" + "\n".join(rows) +
          "\n\n## Each answer\n\n| Answer | First Timeline window | On the timing card | Timeline lines | "
          "Count cards named | Invented cards | Lean | Words |\n|---|---|---|---|---|---|---|---|\n"
          + "\n".join(detail) + "\n")
    with open(os.path.join(out, "results.md"), "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    return md


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="write the prompts and truth files (free)")
    b.add_argument("--out", required=True)
    r = sub.add_parser("round", help="send the prompts to an AI, then report")
    r.add_argument("--out", required=True)
    r.add_argument("--model", default=MODEL, choices=sorted(ai_parts.PRICES))
    r.add_argument("--runs", type=int, default=RUNS)
    p = sub.add_parser("report", help="score the saved answers again (free)")
    p.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.command == "build":
        cases = build(args.out)
        for c in cases:
            print(f"{c['id']}: {c['chars']:,} characters")
        return 0
    if args.command == "round":
        round_(args.out, args.model, runs=args.runs)
        return 0
    report(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

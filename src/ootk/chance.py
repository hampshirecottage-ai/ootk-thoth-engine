"""How unusual is this reading? Each headline number set beside what random shuffles of the same
spread give, so a report only calls a number unusual when chance seldom reaches it.

The ranges come from chance.json: for every spread, CHANCE_DRAWS seeded random draws (each with a
random court card as Significator, as a querent would choose one) run through the same analyses
as a reading, and the count of draws giving each value. scripts/make_chance_table.py writes it;
rerun that whenever a rule that changes these numbers changes (tests/test_chance.py checks one
spread draw for draw). The dignity total needs no table: its chance comes from the deck's own
elements (analysis.dignity_chance).

A number is unusual when random shuffles reach it, or go further, CHANCE_UNUSUAL_P of the time or
less: the same 5% bar each way as the dignity headline, the framework trend and the Own-Place
Check. With several checks on one reading, some random shuffles trip one of them, so the table
also keeps how often a random shuffle shows at least one unusual number, and the report says so.
"""
import json
import random
from functools import lru_cache
from pathlib import Path

from ootk.analysis import (
    CHANCE_UNUSUAL_P, analyze_elemental_balance, book_t_counts, calculate_elemental_dignities, card_is_dignified,
    dignity_chance, evaluate_macro_framework, own_place_check,
)

CHANCE_FILE = Path(__file__).with_name("chance.json")
CHANCE_DRAWS = 4000
FOUR = ("Fire", "Water", "Air", "Earth")
MIN_POSITIONS = 3            # one or two cards give too few numbers to compare

# key: (label, which way can be unusual, the report component it belongs to)
MEASURES = {
    "leader": ("Most cards of one element", "high", "elements"),
    "weakest": ("Fewest cards of one element", "low", "elements"),
    "ill": ("Ill-dignified cards", "both", "elements"),
    "majors": ("Trumps", "both", "numerology"),
    "kinds": ("Ranks falling three or four times", "both", "numerology"),
    "descent": ("Tree lens chosen by the cards", "high", "tree"),
    "ascent": ("Tree lens chosen by the cards", "high", "tree"),
}


def reading_measures(spread_key, spread_results, dignity_matrix=None, framework_basis=None):
    """The table's numbers for one reading: {measure: value}. `framework_basis` is
    evaluate_macro_framework()'s; a lens the querent chose has no chance, so it is left out."""
    n = len(spread_results)
    if dignity_matrix is None:
        dignity_matrix = calculate_elemental_dignities(spread_results, spread_key)
    if framework_basis is None:
        framework_basis = evaluate_macro_framework(spread_results)[1]
    counts = analyze_elemental_balance(spread_results)
    four = [counts.get(e, 0) for e in FOUR]
    found = {
        "leader": max(four), "weakest": min(four),
        "_names": {"leader": _and_names([e for e, c in zip(FOUR, four) if c == max(four)]),
                   "weakest": _and_names([e for e, c in zip(FOUR, four) if c == min(four)])},
        "ill": sum(not card_is_dignified(i, dignity_matrix) for i in range(n)),
        "majors": sum(1 for i in spread_results if i["card_data"].get("arcana_type") == "Major"),
        "kinds": sum(len(seg["kinds"]) for seg in book_t_counts(spread_results, spread_key)),
    }
    if not framework_basis.startswith("forced by"):
        found["descent"] = int(framework_basis.startswith("auto: rank rises"))
        found["ascent"] = int(framework_basis.startswith("auto: rank falls"))
    return found


def _and_names(names):
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


# ---------- the table ----------

def simulate(spread_key, draws=CHANCE_DRAWS):
    """{measure: {value: draws giving it}, "_unusual": draws with at least one unusual number,
    "_draws": draws} for `spread_key`, from seeded random draws: the same every run. Uses the
    site's own draw (web.seeded_draw) with the card tables already loaded."""
    from ootk import web       # the draw lives in the web app; imported here to avoid a cycle
    from ootk.spreads import BOOK_T_KEY, spread_positions
    deck = web.reference_deck()
    rows = web.reference_rows("thoth")
    courts = sorted(c["title"] for c in deck if rows[c["title"]].get("arcana_type") == "Court")
    found = []
    for i in range(draws):
        seed = str(i + 1)
        sig = random.Random(f"{spread_key}:{seed}").choice(courts)
        if spread_key == BOOK_T_KEY:
            titles, positions, _ = web.book_t_draw(deck, seed, sig, "1,1,1,1")
        else:
            titles, _ = web.seeded_draw(deck, seed, spread_key, sig)
            positions = spread_positions(spread_key)
        results = [{"position_number": k + 1, "position_name": p, "card_data": dict(rows[t])}
                   for k, (p, t) in enumerate(zip(positions, titles))]
        dignity = calculate_elemental_dignities(results, spread_key)
        scores = [d["score"] for d in dignity]
        found.append((reading_measures(spread_key, results, dignity), len(scores), sum(scores),
                      own_place_check(results, spread_key)))
    table = {}
    for key in MEASURES:
        hist = {}
        for values, *_ in found:
            if key in values:
                hist[values[key]] = hist.get(values[key], 0) + 1
        table[key] = {str(v): hist[v] for v in sorted(hist)}
    unusual = 0
    for values, pairs, net, own in found:
        rows_ = rows_for(values, table, pairs, net, own, draws)
        unusual += any(r["unusual"] for r in rows_)
    return dict(table, _draws=draws, _unusual=unusual)


@lru_cache(maxsize=1)
def chance_table():
    """chance.json, or {} when it is missing (the box is then left out)."""
    try:
        return json.loads(CHANCE_FILE.read_text())
    except (OSError, ValueError):
        return {}


def _tails(hist, value, draws):
    """(share of draws at or above `value`, share at or below it)."""
    hi = sum(c for v, c in hist.items() if int(v) >= value)
    lo = sum(c for v, c in hist.items() if int(v) <= value)
    return hi / draws, lo / draws


def _usual_range(hist, draws, way):
    """The values a random shuffle gives that the box would not call unusual: (low, high)."""
    keep = [int(v) for v in hist
            if not _is_unusual(_tails(hist, int(v), draws), way)]
    return (min(keep), max(keep)) if keep else (None, None)


def _is_unusual(tails, way):
    hi, lo = tails
    return ((way in ("high", "both") and hi <= CHANCE_UNUSUAL_P)
            or (way in ("low", "both") and lo <= CHANCE_UNUSUAL_P))


def _one_in(p):
    return f"about 1 in {max(2, round(1 / p)):,}" if p > 0 else f"none of {CHANCE_DRAWS:,}"


def rows_for(values, table, pairs, net, own_place, draws, off=frozenset()):
    """The box's rows: each number, what chance gives and whether it is unusual. A measure is
    left out when every random shuffle gives the same value (it says nothing about this draw),
    or when its part of the reading is switched off."""
    rows = []
    lens_done = False
    for key, (label, way, part) in MEASURES.items():
        hist = table.get(key) or {}
        if part in off or key not in values or len(hist) < 2:
            continue
        if key in ("descent", "ascent"):
            if lens_done:
                continue
            lens_done = True
            down, up = values.get("descent", 0), values.get("ascent", 0)
            p_down = int((table.get("descent") or {}).get("1", 0)) / draws
            p_up = int((table.get("ascent") or {}).get("1", 0)) / draws
            if down or up:
                p = p_down if down else p_up
                rows.append({"key": "lens", "label": label,
                             "value": "Yes, running down the Tree" if down else "Yes, running up the Tree",
                             "usual": "No (the default lens)", "unusual": p <= CHANCE_UNUSUAL_P,
                             "verdict": "unusual" if p <= CHANCE_UNUSUAL_P else "not unusual",
                             "odds": f"{_one_in(p)} random shuffles do this"})
            else:
                rows.append({"key": "lens", "label": label, "value": "No (the default lens)",
                             "usual": "No (the default lens)", "unusual": False,
                             "verdict": "usual",
                             "odds": f"{1 - p_down - p_up:.0%} of random shuffles stay on it"})
            continue
        value = values[key]
        hi, lo = _tails(hist, value, draws)
        unusual = _is_unusual((hi, lo), way)
        low, high = _usual_range(hist, draws, way)
        usual = (f"up to {high}" if way == "high" else f"{low} or more" if way == "low"
                 else f"{low} to {high}" if low != high else f"{low}")
        verdict, odds = "usual", ""
        if unusual:
            word = "high" if (way == "high" or (way == "both" and hi <= CHANCE_UNUSUAL_P)) else "low"
            verdict, odds = f"unusually {word}", f"{_one_in(hi if word == 'high' else lo)} random shuffles go this far"
        name = values.get("_names", {}).get(key)
        if low == high and not unusual:
            continue            # nearly every shuffle gives the same value: nothing to compare
        rows.append({"key": key, "label": label, "value": f"{value} ({name})" if name else str(value),
                     "usual": usual, "unusual": unusual, "verdict": verdict, "odds": odds})
    if pairs and "elements" not in off:
        c = dignity_chance(pairs, net)
        p = c["p_high"] if c["lean"] == "above" else c["p_low"]
        rows.insert(0, {
            "key": "dignity", "label": "Elemental dignity total", "value": f"{net:+d}",
            "usual": f"{c['low']:+d} to {c['high']:+d}",
            "unusual": c["lean"] != "usual",
            "verdict": ("usual" if c["lean"] == "usual" else
                        f"unusually {'favourable' if c['lean'] == 'above' else 'unfavourable'}"),
            "odds": "" if c["lean"] == "usual" else f"{_one_in(p)} random shuffles go this far"})
    for check in (own_place or ()) if "astrology" not in off else ():
        rows.append({
            "key": "own_place", "label": f"Cards {check['noun']}" + (f", {check['label'].split(' (')[0]}"
                                                       if check["label"].startswith("Op") else ""),
            "value": str(check["count"]), "usual": f"about {check['expected']:.1f}",
            "unusual": check["unusual"],
            "verdict": "unusually high" if check["unusual"] else "usual",
            "odds": f"{_one_in(check['chance'])} random shuffles go this far" if check["unusual"] else ""})
    return rows


def chance_view(spread_key, spread_results, dignity_matrix, framework_basis, own_place,
                off=frozenset()):
    """The box for one reading: {"rows", "unusual" (rows that are), "any_rate" (share of random
    shuffles showing at least one unusual number)}, or None when there is nothing to compare."""
    table = chance_table().get(str(spread_key))
    if not table or len(spread_results) < MIN_POSITIONS:
        return None
    scores = [d["score"] for d in dignity_matrix]
    values = reading_measures(spread_key, spread_results, dignity_matrix, framework_basis)
    rows = rows_for(values, table, len(scores), sum(scores), own_place, table["_draws"], off)
    if not rows:
        return None
    return {"rows": rows, "unusual": [r for r in rows if r["unusual"]],
            "any_rate": table["_unusual"] / table["_draws"]}


def chance_sentence(view):
    """The prompt's line: what stands out against chance and how often a random shuffle shows as
    much, so the AI neither overreads an ordinary number nor makes much of a single flag."""
    if not view:
        return ""
    others = [r["label"].lower() for r in view["rows"] if not r["unusual"]]
    if not view["unusual"]:
        return (f"Compared with random shuffles of this spread, none of the {len(others)} numbers "
                f"checked ({', '.join(others)}) is unusual, so read them as ordinary for this spread.")
    named = "; ".join(f"{r['label'].lower()}, {r['value']}, {r['verdict']} ({r['odds']})"
                      for r in view["unusual"])
    rest = (f" The other {len(others)} numbers checked ({', '.join(others)}) are in the usual range."
            if others else "")
    return (f"Compared with random shuffles of this spread, these stand out: {named}.{rest} Random shuffles show at "
            f"least one unusual number {view['any_rate']:.0%} of the time, so weigh a single one "
            f"lightly.")

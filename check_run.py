#!/usr/bin/env python3
"""Sanity-checks a saved OOTK 4-operation (spread 12) run against the fixes made so far.

Usage:
    python src/spread_engine.py --spread 12 --seed 77 --mapping french_egyptian \
        --significator "Knight of Swords" --topic "Is everything working correctly?" | tee run.txt
    python check_run.py run.txt

Exits 0 if every check passes, 1 otherwise. WARN lines are known data gaps, not failures.
"""
import re
import sys
from collections import Counter

# Operation ranges for spread 12: Key (15), Houses (12), Zodiac (12), Decans (36).
OPS = {1: (1, 15), 2: (16, 27), 3: (28, 39), 4: (40, 75)}
EXPECTED_ASPECT_PAIRS = {2: 42, 3: 42, 4: 126}
EXPECTED_OP1_PAIRS = 14
RING_ASPECTS = {"Opposition", "Square", "Trine", "Sextile"}

# French/Egyptian rows for the 22 Majors, as returned by the verification query:
# name -> (letter, path, attribution)
FRENCH_MAJORS = {
    "The Fool": ("Shin", "Path 31 (Yesod-Malkuth)", "Unnumbered / Primeval Spirit"),
    "The Magus": ("Aleph", "Path 11 (Kether-Chokmah)", "Air / Magus Spirit"),
    "The Priestess": ("Beth", "Path 12 (Kether-Binah)", "Mercury"),
    "The Empress": ("Gimel", "Path 13 (Chokmah-Binah)", "Venus"),
    "The Emperor": ("Daleth", "Path 14 (Chokmah-Tiphareth)", "Aries"),
    "The Hierophant": ("Heh", "Path 15 (Chokmah-Chesed)", "Taurus"),
    "The Lovers": ("Vav", "Path 16 (Binah-Tiphareth)", "Gemini"),
    "The Chariot": ("Zain", "Path 17 (Binah-Geburah)", "Cancer"),
    "Lust": ("Cheth", "Path 18 (Chesed-Geburah)", "Strength / Leo"),
    "The Hermit": ("Teth", "Path 19 (Chesed-Tiphareth)", "Virgo"),
    "Fortune": ("Yod", "Path 20 (Chesed-Netzach)", "Jupiter"),
    "Adjustment": ("Kaph", "Path 21 (Geburah-Tiphareth)", "Justice / Libra"),
    "The Hanged Man": ("Lamed", "Path 22 (Geburah-Hod)", "Water"),
    "Death": ("Mem", "Path 23 (Tiphareth-Netzach)", "Scorpio"),
    "Art": ("Nun", "Path 24 (Tiphareth-Hod)", "Sagittarius"),
    "The Devil": ("Samekh", "Path 25 (Tiphareth-Yesod)", "Capricorn"),
    "The Tower": ("Ayin", "Path 26 (Chesed-Hod)", "Mars"),
    "The Star": ("Peh", "Path 27 (Netzach-Hod)", "Aquarius"),
    "The Moon": ("Tzaddi", "Path 28 (Netzach-Yesod)", "Pisces"),
    "The Sun": ("Qoph", "Path 29 (Netzach-Malkuth)", "Sun"),
    "The Aeon": ("Resh", "Path 30 (Hod-Malkuth)", "Fire / Spirit"),
    "The Universe": ("Tav", "Path 32 (Malkuth-Universe)", "Saturn / Earth"),
}

results = []  # (status, label, detail)


def check(ok, label, detail=""):
    results.append(("PASS" if ok else "FAIL", label, detail))
    return ok


def warn(label, detail=""):
    results.append(("WARN", label, detail))


def op_of(pos):
    for n, (a, b) in OPS.items():
        if a <= pos <= b:
            return n
    return None


def main(path):
    text = open(path, encoding="utf-8").read()
    lines = text.splitlines()

    # ---------- draw log ----------
    draws = []
    pinned = None
    for ln in lines:
        m = re.match(r"^--> (PRNG Auto-Drawn|Significator \(pinned\)): (.+)$", ln)
        if m:
            draws.append(m.group(2).strip())
            if m.group(1).startswith("Significator"):
                pinned = m.group(2).strip()
    check(len(draws) == 75, "75 cards drawn", f"found {len(draws)}")
    check(pinned is not None, "significator pinned at Position 1",
          f"pinned: {pinned}" if pinned else "no 'Significator (pinned)' line found")
    check(bool(draws) and pinned == draws[0], "pinned card is Position 1")
    check(len(set(draws)) == len(draws), "no card drawn twice",
          ", ".join(c for c, n in Counter(draws).items() if n > 1))
    if pinned:
        check(draws.count(pinned) == 1, "significator appears exactly once", f"{draws.count(pinned)}x")

    # ---------- header ----------
    m = re.search(r"\*\*Significator:\*\* (.+)", text)
    check(bool(m) and m.group(1).strip() == pinned, "header significator matches Position 1",
          f"header: {m.group(1).strip() if m else None}")
    french = "French / Egyptian" in text
    m = re.search(r"\*\*Framework Basis:\*\* (.+)", text)
    check(bool(m), "framework basis line present", m.group(1)[:90] if m else "no '**Framework Basis:**' line")

    # ---------- split sections ----------
    parts = re.split(r"\n## (\d)\. ", text)
    sections = {int(parts[i]): parts[i + 1] for i in range(1, len(parts) - 1, 2)}
    for n in range(1, 8):
        check(n in sections, f"section {n} present")
    if not all(n in sections for n in (1, 2, 4, 5, 6)):
        return

    # ---------- section 1: elements ----------
    elems = {}
    for e, c in re.findall(r"\* \*\*(\w+)\s*\*\*:[^\d\n]*(\d+) \(", sections[1]):
        elems[e] = int(c)
    check(sum(elems.values()) == 75, "element counts sum to 75", str(elems))
    check(elems.get("Spirit", -1) == 0, "Spirit bucket is empty (no unparsed Majors)",
          f"Spirit = {elems.get('Spirit')}")

    # ---------- section 2: spatial type totals ----------
    totals = [int(x) for x in re.findall(r": `(\d+)`", sections[2])[:4]]
    check(len(totals) == 4 and sum(totals) == 75, "spatial type totals sum to 75", str(totals))

    # ---------- section 4: dignity ----------
    s4 = sections[4]
    check(len(re.findall(r"^\*\*Operation \d", s4, re.M)) == 4, "section 4 has 4 operation headings")
    pairs = [(int(a), int(b)) for a, b in
             re.findall(r"^\* \*\*Pos (\d+) \(.*\) <-> Pos (\d+) \(.*\)\*\*: `Score", s4, re.M)]
    check(len(pairs) == 71, "71 dignity pairs (74 minus 3 boundary pairs)", f"found {len(pairs)}")
    check(all(b == a + 1 for a, b in pairs), "dignity pairs are consecutive")
    crossing = [(a, b) for a, b in pairs if op_of(a) != op_of(b)]
    check(not crossing, "no dignity pair crosses an operation boundary", str(crossing[:5]))

    # ---------- section 5: spatial ----------
    s5 = sections[5]
    check("No spatial layout" not in s5, "section 5 is populated")
    seg_text = {}
    segs = re.split(r"^\*\*Operation (\d):[^\n]*\*\*\n", s5, flags=re.M)
    for i in range(1, len(segs) - 1, 2):
        seg_text[int(segs[i])] = segs[i + 1]
    check(sorted(seg_text) == [1, 2, 3, 4], "section 5 has 4 operation headings", str(sorted(seg_text)))

    if 1 in seg_text:
        op1 = [(int(a), int(b)) for a, b in
               re.findall(r"^\* \*\*Pos (\d+) \(.*\) <-> Pos (\d+) \(.*\)\*\*:", seg_text[1], re.M)]
        check(len(op1) == EXPECTED_OP1_PAIRS, f"Op 1 has {EXPECTED_OP1_PAIRS} consecutive spatial pairs",
              f"found {len(op1)}")
        check(all(b == a + 1 for a, b in op1), "Op 1 spatial pairs are consecutive")
    for n, expected in EXPECTED_ASPECT_PAIRS.items():
        t = seg_text.get(n, "")
        ring = [(int(a), int(b)) for a, b in
                re.findall(r"^\* Pos (\d+) \(.*\) <-> Pos (\d+) \(", t, re.M)]
        check(len(ring) == expected, f"Op {n} has {expected} aspect pairs", f"found {len(ring)}")
        lo, hi = OPS[n]
        check(all(lo <= a <= hi and lo <= b <= hi for a, b in ring), f"Op {n} aspect pairs stay inside the operation")
        groups = set(re.findall(r"^_(\w+) \(", t, re.M))
        check(groups == RING_ASPECTS, f"Op {n} has all four aspect groups", str(sorted(groups)))

    # ---------- section 6: per-card French mapping ----------
    blocks = re.split(r"^### Position (\d+): ", sections[6], flags=re.M)
    cards = {}
    for i in range(1, len(blocks) - 1, 2):
        cards[int(blocks[i])] = blocks[i + 1]
    check(len(cards) == 75, "75 card blocks in section 6", f"found {len(cards)}")

    drawn_in_s6 = [re.search(r"- \*\*Card Drawn\*\*: (.+)", b).group(1).strip() for _, b in sorted(cards.items())
                   if re.search(r"- \*\*Card Drawn\*\*: (.+)", b)]
    check(drawn_in_s6 == draws, "section 6 card order matches the draw log")

    majors_checked = 0
    bad = []
    for pos, block in sorted(cards.items()):
        title = re.search(r"- \*\*Card Drawn\*\*: (.+)", block).group(1).strip()
        if "Major |" not in block:
            continue
        name = title.split(" - ", 1)[-1]
        exp = FRENCH_MAJORS.get(name)
        if not exp:
            bad.append(f"Pos {pos} {title}: unknown Major")
            continue
        letter, mpath, attr = exp
        path_line = re.search(r"- \*\*Path/Sephira\*\*: (.+)", block).group(1)
        attr_line = re.search(r"- \*\*Attribution\*\*: (.+)", block).group(1).strip()
        frl = re.search(r"French/Egyptian: `([^`]*)`", block).group(1)
        if french:
            majors_checked += 1
            if not path_line.startswith(mpath + " ("):
                bad.append(f"Pos {pos} {title}: path '{path_line}' expected '{mpath}'")
            if f"({letter} (" not in path_line:
                bad.append(f"Pos {pos} {title}: letter in '{path_line}' expected {letter}")
            if attr_line != attr:
                bad.append(f"Pos {pos} {title}: attribution '{attr_line}' expected '{attr}'")
            if not frl.startswith(letter + " ("):
                bad.append(f"Pos {pos} {title}: French letter '{frl}' expected {letter}")
    if french:
        check(not bad, f"all {majors_checked} drawn Majors match the verified French/Egyptian table",
              "; ".join(bad[:6]))
    else:
        warn("mapping is golden_dawn, French Major check skipped")

    # ---------- known data gaps (not failures) ----------
    dots = len(re.findall(r"- \*\*Attribution\*\*: \.\.\.$", sections[6], re.M))
    if dots:
        warn(f"{dots} card(s) show '...' as attribution", "known data gap: correspondences row 32 etc.")

    # ---------- report ----------
    width = max(len(r[1]) for r in results)
    for status, label, detail in results:
        print(f"[{status}] {label.ljust(width)}  {detail}".rstrip())
    fails = sum(1 for r in results if r[0] == "FAIL")
    warns = sum(1 for r in results if r[0] == "WARN")
    print(f"\n{len(results) - fails - warns} passed, {fails} failed, {warns} warnings")
    return fails


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python check_run.py run.txt")
    sys.exit(1 if main(sys.argv[1]) else 0)

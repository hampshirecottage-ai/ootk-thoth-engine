#!/usr/bin/env python3
"""Sanity-checks a saved OOTK 4-operation (spread 12) run against the fixes made so far.

Usage:
    ootk --spread 12 --seed 12345 --mapping french_egyptian \
        --significator "Knight of Swords" --topic "Is everything working correctly?" | tee run.txt
    python scripts/check_run.py run.txt

Exits 0 if every check passes, 1 otherwise. WARN lines are known data gaps, not failures.
"""
import re
import sys
from collections import Counter

# Operation ranges for spread 12: Key (15), Houses (12), Zodiac (12), Decans (36).
OPS = {1: (1, 15), 2: (16, 27), 3: (28, 39), 4: (40, 75)}
EXPECTED_ASPECT_PAIRS = {2: 42, 3: 42, 4: 126}
# Op 1 scores its named pairs (2-3, 4-5, ... 12-13) and the significator with 14 and 15.
OP1_PAIRS = [(2, 3), (4, 5), (6, 7), (8, 9), (10, 11), (12, 13), (1, 14), (1, 15)]
RING_ASPECTS = {"Opposition", "Square", "Trine", "Sextile"}

# French/Egyptian rows for the 22 Majors (Levi/Papus letters; paths on the standard tree):
# name -> (letter, path, attribution)
FRENCH_MAJORS = {
    "The Fool": ("Shin", "Path 31 (Hod-Malkuth)", "Unnumbered / Primeval Spirit"),
    "The Magus": ("Aleph", "Path 11 (Kether-Chokmah)", "Mercury"),
    "The Priestess": ("Beth", "Path 12 (Kether-Binah)", "Moon"),
    "The Empress": ("Gimel", "Path 13 (Kether-Tiphareth)", "Venus"),
    "The Emperor": ("Daleth", "Path 14 (Chokmah-Binah)", "Aries"),
    "The Hierophant": ("Heh", "Path 15 (Chokmah-Tiphareth)", "Taurus"),
    "The Lovers": ("Vav", "Path 16 (Chokmah-Chesed)", "Gemini"),
    "The Chariot": ("Zain", "Path 17 (Binah-Tiphareth)", "Cancer"),
    "Adjustment": ("Cheth", "Path 18 (Binah-Geburah)", "Justice / Libra"),
    "The Hermit": ("Teth", "Path 19 (Chesed-Geburah)", "Virgo"),
    "Fortune": ("Yod", "Path 20 (Chesed-Tiphareth)", "Jupiter"),
    "Lust": ("Kaph", "Path 21 (Chesed-Netzach)", "Strength / Leo"),
    "The Hanged Man": ("Lamed", "Path 22 (Geburah-Tiphareth)", "Water"),
    "Death": ("Mem", "Path 23 (Geburah-Hod)", "Scorpio"),
    "Art": ("Nun", "Path 24 (Tiphareth-Netzach)", "Sagittarius"),
    "The Devil": ("Samekh", "Path 25 (Tiphareth-Yesod)", "Capricorn"),
    "The Tower": ("Ayin", "Path 26 (Tiphareth-Hod)", "Mars"),
    "The Star": ("Peh", "Path 27 (Netzach-Hod)", "Aquarius"),
    "The Moon": ("Tzaddi", "Path 28 (Netzach-Yesod)", "Pisces"),
    "The Sun": ("Qoph", "Path 29 (Netzach-Malkuth)", "Sun"),
    "The Aeon": ("Resh", "Path 30 (Hod-Yesod)", "Fire / Spirit"),
    "The Universe": ("Tav", "Path 32 (Yesod-Malkuth)", "Saturn / Earth"),
}

# Sefer Yetzirah class of each letter (both spellings used in the data).
LETTER_TYPES = {
    **{l: "Mother_Axis" for l in ("Aleph", "Mem", "Shin")},
    **{l: "Double_Direction" for l in ("Beth", "Gimel", "Daleth", "Kaph", "Peh", "Resh", "Tav", "Tau")},
    **{l: "Simple_Edge" for l in ("Heh", "Vav", "Zain", "Cheth", "Teth", "Yod", "Lamed", "Nun",
                                    "Samekh", "Ayin", "Tzaddi", "Qoph")},
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
    # Each operation reshuffles the whole deck, so a card may repeat across operations but
    # never inside one.
    twice = [f"Op {n}: {c}" for n, (lo, hi) in OPS.items()
             for c, k in Counter(draws[lo - 1:hi]).items() if k > 1]
    check(not twice, "no card drawn twice within an operation", ", ".join(twice))
    if pinned:
        check(draws[:15].count(pinned) == 1, "significator appears once in Op 1",
              f"{draws[:15].count(pinned)}x")

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
    # Op 1's heap pairs (8), then neighbours within each wheel (11 + 11 + 35) plus the pair that
    # closes each full ring (houses, signs, decans): 27<->16, 39<->28, 75<->40.
    ring_closures = {(hi, lo) for n, (lo, hi) in OPS.items() if n in EXPECTED_ASPECT_PAIRS}
    check(len(pairs) == 68, "68 dignity pairs (8 heap pairs + 57 neighbours + 3 ring closures)",
          f"found {len(pairs)}")
    check([p for p in pairs if op_of(p[0]) == 1] == OP1_PAIRS, "Op 1 scores its named pairs")
    wheel = [p for p in pairs if op_of(p[0]) != 1]
    check(all(b == a + 1 or (a, b) in ring_closures for a, b in wheel),
          "wheel dignity pairs are neighbours or ring closures",
          str([p for p in wheel if p[1] != p[0] + 1 and p not in ring_closures][:5]))
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
        check(op1 == OP1_PAIRS, f"Op 1 has its {len(OP1_PAIRS)} heap pairs", f"found {op1[:8]}")
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
    check(dots == 0, "no card shows '...' as attribution", f"{dots} card(s)")

    # ---------- spatial type follows the letter shown ----------
    mismatched = []
    for pos, block in sorted(cards.items()):
        if "Major |" not in block:
            continue
        letter = re.search(r"- \*\*Path/Sephira\*\*: .*\((\w+) \(", block)
        stype = re.search(r"- \*\*Spatial Dimension\*\*: `(\w+)`", block)
        if letter and stype and LETTER_TYPES.get(letter.group(1)) not in (None, stype.group(1)):
            mismatched.append(f"Pos {pos} {letter.group(1)}={stype.group(1)}")
    check(not mismatched, "Majors' spatial type matches their active letter", "; ".join(mismatched[:6]))

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

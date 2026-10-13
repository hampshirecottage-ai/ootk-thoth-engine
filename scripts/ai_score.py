#!/usr/bin/env python3
"""Scores AI answers to the OOTK test prompts against what the engine knows.

Steps 2 and 3 of the AI answer check. run (or pilot) sends the prompts to Claude and saves
the answers; answers from other AIs can be saved by hand. Each answer then goes through two
stages:

1. extract: an AI turns the answer into a fixed-shape list of claims (which card it puts
   where, each correspondence and pair score it states, what it says about the prompt being
   complete, the closing outcome...). It sees only the answer and the position names, never
   the truth file, so it cannot "fix" what the answer said. Needs ANTHROPIC_API_KEY and the
   anthropic package (pip install anthropic). A claims file can also be written by hand.
2. score: plain code compares those claims with truth/<case>.json from scripts/ai_check.py.
   The facts are scored by code, not by an AI's opinion.

Answers are files named <case id>__<ai>__<run>.md, e.g. s408850_sp3_full__claude-app__1.md,
in one folder; claims go next to them as .claims.json and scores as .score.json.

Usage:
    python scripts/ai_score.py pilot                    # the whole pilot, into output/ai_check
    python scripts/ai_score.py run --build BUILD --answers ANSWERS --cases all [--runs 2]
    python scripts/ai_score.py extract --build BUILD --answers ANSWERS [--model claude-sonnet-5-5]
    python scripts/ai_score.py score   --build BUILD --answers ANSWERS

run, extract and pilot call the Claude API: they need `pip install anthropic` and
ANTHROPIC_API_KEY set in the shell, and each prints what it cost.
"""
import argparse
import glob
import json
import os
import re
import sys
import unicodedata

EXTRACT_MODEL = "claude-sonnet-5-5"
ELEMENTS = ("Fire", "Water", "Air", "Earth", "Spirit")
SIGNS = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius",
         "Capricorn", "Aquarius", "Pisces")
PLANETS = ("Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon")
SEPHIROTH = {"kether": "crown", "chokmah": "wisdom", "binah": "understanding", "chesed": "mercy",
             "geburah": "severity", "tiphareth": "beauty", "netzach": "victory", "hod": "splendour",
             "yesod": "foundation", "malkuth": "kingdom"}
SEPHIRA_SPELLINGS = {"chokhmah": "chokmah", "hokmah": "chokmah", "gevurah": "geburah", "tipheret": "tiphareth",
                     "tiferet": "tiphareth", "tipharet": "tiphareth", "keter": "kether", "netsach": "netzach",
                     "malkut": "malkuth", "strength": "geburah", "splendor": "splendour"}
LETTERS = {"aleph": ("alef",), "beth": ("bet", "beit"), "gimel": (), "daleth": ("dalet",),
           "he": ("heh", "hé", "hei", "hay"), "vau": ("vav", "waw"), "zayin": (), "cheth": ("chet", "heth", "het"),
           "teth": ("tet",), "yod": ("yud",), "kaph": ("kaf",), "lamed": (), "mem": (), "nun": (),
           "samekh": ("samech",), "ayin": (), "peh": ("pe",), "tzaddi": ("tzadi", "tsade", "tzaddik", "tzade"),
           "qoph": ("kuf", "qof", "koph"), "resh": (), "shin": (), "tav": ("tau", "taw")}
LETTER_OF = {v: k for k, alts in LETTERS.items() for v in (k,) + alts}
SOLIDS = {"tetrahedron": "Tetrahedron", "octahedron": "Octahedron", "icosahedron": "Icosahedron",
          "dodecahedron": "Dodecahedron", "hexahedron": "Hexahedron (Cube)", "cube": "Hexahedron (Cube)"}
CUBE_TYPES = {"mother": "Mother_Axis", "double": "Double_Direction", "simple": "Simple_Edge",
              "sephira": "Sephira_Point", "nodal": "Sephira_Point"}
QUALITY_SIGN = {"strong": 1, "friendly": 1, "neutral": 0, "contrary": -1}
# Words that should not appear in the plain-language recap (rule 6).
TECH_TERMS = ("sephira", "sephiroth", "decan", "dignity", "dignities", "ill-dignified", "tetrahedron",
              "octahedron", "icosahedron", "dodecahedron", "hexahedron", "cube of space", "simple edge",
              "mother letter", "double letter", "chesed", "netzach", "chokmah", "binah", "geburah", "tiphareth",
              "hod", "yesod", "malkuth", "kether", "trine", "sextile", "square aspect", "opposition",
              "liber 777", "king scale", "framework", "operation", "significator", "tzaddi", "aleph",
              "qoph", "teth", "heh", "vau", "book t", "own-place", "elemental")

POSITION_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["position", "card"],
                   "properties": {"position": {"type": "integer"}, "card": {"type": "string"}}}
CLAIMS_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["prompt_status", "last_position_seen", "interprets_reading", "inconsistencies_flagged",
                 "framework_named", "positions", "card_facts", "pair_claims", "element_counts",
                 "own_place_treated_as_significant", "says_significator_mismatch", "relates_to_question",
                 "framework_used_as_lens", "likely_outcome", "outcome_offered_as_possibility",
                 "leaves_decision_to_querent", "recap_heading"],
    "properties": {
        "prompt_status": {"type": "string", "enum": ["says_complete", "says_cut_off", "not_mentioned"]},
        "last_position_seen": {"type": "integer", "description": "position the answer says it could see last, 0 if it does not say"},
        "interprets_reading": {"type": "boolean", "description": "does it go on to interpret the cards"},
        "inconsistencies_flagged": {"type": "array", "items": {"type": "string"},
                                    "description": "each problem or inconsistency in the data that the answer points out, in its words"},
        "framework_named": {"type": "string", "description": "the framework or lens it names, '' if none"},
        "positions": {"type": "array", "items": POSITION_SCHEMA,
                      "description": "every position the answer discusses, with the card it says is there, as written"},
        "card_facts": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["card", "attribute", "value"],
            "properties": {
                "card": {"type": "string"},
                "attribute": {"type": "string", "enum": ["element", "sign_or_planet", "hebrew_letter", "sephira",
                                                         "solid", "colour", "cube_type"]},
                "value": {"type": "string"}}},
            "description": "every correspondence the answer states for a drawn card, one per value"},
        "pair_claims": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["position_a", "position_b", "card_a", "card_b", "dignity_score", "dignity_quality",
                         "aspect", "says_strongest", "says_most_strained"],
            "properties": {
                "position_a": {"type": "integer"}, "position_b": {"type": "integer"},
                "card_a": {"type": "string"}, "card_b": {"type": "string"},
                "dignity_score": {"type": "string", "description": "e.g. '+2', '-2', '' if not stated"},
                "dignity_quality": {"type": "string", "enum": ["strong", "friendly", "neutral", "contrary", "not_stated"]},
                "aspect": {"type": "string", "enum": ["opposition", "square", "trine", "sextile", "conjunction", "not_stated"]},
                "says_strongest": {"type": "boolean"}, "says_most_strained": {"type": "boolean"}}},
            "description": "every pair of cards or positions the answer scores, rates or links by an aspect; "
                           "two different positions, and a score only where the text plainly gives it to these two"},
        "element_counts": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["element", "count"],
            "properties": {"element": {"type": "string", "enum": list(ELEMENTS)}, "count": {"type": "integer"}}},
            "description": "element counts it states; convert percentages to counts only if the total is given"},
        "own_place_treated_as_significant": {"type": "boolean",
                                             "description": "does it lean on the Own-Place Check; false if it does not mention one"},
        "says_significator_mismatch": {"type": "boolean",
                                       "description": "does it say the Significator's place disagrees with the printed cards"},
        "relates_to_question": {"type": "boolean"},
        "framework_used_as_lens": {"type": "integer", "description": "0 not used, 1 named only, 2 shapes the reading"},
        "likely_outcome": {"type": "string", "description": "its likely outcome in one sentence, '' if none"},
        "outcome_offered_as_possibility": {"type": "boolean"},
        "leaves_decision_to_querent": {"type": "boolean"},
        "recap_heading": {"type": "string", "description": "the exact heading line of its plain-language recap, '' if none"},
    },
}
EXTRACT_INSTRUCTIONS = """You are checking a tarot reading an AI wrote from a data prompt. Do not judge or correct it.
Record only what the reading itself says, as the JSON schema asks. Copy card names and values as written.
Give positions as numbers using the position list below; use 0 when the reading does not tie a claim to a position.
Record a card fact only where the reading states it for a card in this reading, not general remarks
about other cards (for example "Heh is the Star" is not a fact about a drawn card).
Some position names hold a card in brackets, such as "Decan 10: Venus in Cancer (2 of Cups)". That card names
the place only; the card drawn there is the one the reading puts on it ("the Queen of Cups sits at Venus in
Cancer (2 of Cups)" records that decan's position as the Queen of Cups). Never record a bracketed place card as drawn.
In a chain such as "A -> B (+2) -> C", a score belongs to the link it is written on only when that is clear;
otherwise leave dignity_score empty.

Position list:
{positions}

The reading:
<reading>
{answer}
</reading>"""


# --- names ---------------------------------------------------------------------------------

def fold(text):
    """Lower case, accents removed, punctuation to spaces."""
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+\-]", " ", text.lower())).strip()


class Names:
    """Maps any name an answer uses for a card (Thoth, Waite, numerals, short titles) to its
    Thoth title. Thoth names win over Waite ones (the Waite Knight is the Thoth Prince)."""

    def __init__(self, deck):
        self.by_name, self.ambiguous = {}, set()
        for kind in ("thoth", "short", "waite"):
            seen = {}
            for title, card in deck["cards"].items():
                for n in card["names"]:
                    if n["kind"] == kind:
                        seen.setdefault(fold(n["name"]), set()).add(title)
            for name, titles in seen.items():
                if name in self.by_name:
                    # A full Thoth name beats a Waite one; a short title against a Waite name
                    # ('Strength': the 9 of Wands, or the Waite name of Lust) cannot be told apart.
                    if kind == "waite" and self.by_name[name] not in titles and name not in self.thoth_full:
                        self.ambiguous.add(name)
                    continue
                if len(titles) > 1:
                    self.ambiguous.add(name)
                self.by_name[name] = sorted(titles)[0]
            if kind == "thoth":
                self.thoth_full = set(self.by_name)
        for name in self.ambiguous:
            self.by_name.pop(name, None)
        self.keys = sorted(self.by_name, key=len, reverse=True)

    def title(self, written):
        """The Thoth title for a card as written in an answer, or None (unknown, or a name that
        two cards share)."""
        f = fold(written).removeprefix("the ")
        if f in self.ambiguous:
            return None
        if f in self.by_name:
            return self.by_name[f]
        f = f" {fold(written)} "
        for key in self.keys:
            if len(key) > 3 and f" {key} " in f:
                return self.by_name[key]
        return None


def tokens(text):
    return set(fold(text).split())


def letter(text):
    """The canonical letter name in text ('ה (Hé)' -> 'he'), or None."""
    for t in fold(text).split():
        if t in LETTER_OF:
            return LETTER_OF[t]
    return None


def sephira(text):
    for t in fold(text).split():
        t = SEPHIRA_SPELLINGS.get(t, t)
        if t in SEPHIROTH:
            return t
        for k, english in SEPHIROTH.items():
            if t == english:
                return k
    return None


# --- comparing one fact --------------------------------------------------------------------

def check_fact(fact, truth_card):
    """(ok, note). ok is True, False or None (cannot be checked from the data)."""
    attr, value = fact["attribute"], fact["value"]
    if attr == "element":
        said = [e for e in ELEMENTS if e.lower() in tokens(value)]
        if not said:
            return None, "no element word"
        attribution = truth_card.get("attribution") or ""
        court = re.match(r"(\w+) of (\w+)", attribution) if truth_card.get("arcana") == "Court" else None
        allowed = {truth_card["element"]} | ({court[1], court[2]} if court else set())
        return all(e in allowed for e in said), f"data: {truth_card['element']}" + (f" ({court[0]})" if court else "")
    if attr == "sign_or_planet":
        said = [w for w in SIGNS + PLANETS if w.lower() in tokens(value)]
        if not said:
            return None, "no sign or planet word"
        attribution = tokens(truth_card.get("attribution") or "")
        return all(w.lower() in attribution for w in said), f"data: {truth_card.get('attribution')}"
    if attr == "hebrew_letter":
        said = letter(value)
        if not said:
            s = sephira(value)
            if s:
                return s == sephira(truth_card.get("hebrew_letter") or ""), f"data: {truth_card.get('hebrew_letter')}"
            return None, "no letter name"
        real = letter(truth_card.get("hebrew_letter") or "")
        if said == real:
            return True, f"data: {truth_card.get('hebrew_letter')}"
        others = [s for s, v in (truth_card.get("letters_by_system") or {}).items() if v and letter(v) == said]
        return False, f"data: {truth_card.get('hebrew_letter')}" + (f"; that is the {others[0]} letter" if others else "")
    if attr == "sephira":
        said = sephira(value)
        real = sephira(truth_card.get("hebrew_letter") or "") or sephira(truth_card.get("path_or_sephira") or "")
        if not said or not real:
            return None, "not a sephira card"
        return said == real, f"data: {truth_card.get('path_or_sephira')}"
    if attr == "solid":
        said = {SOLIDS[t] for t in tokens(value) if t in SOLIDS}
        if not said:
            return None, "no solid name"
        return said == {truth_card.get("platonic_solid")}, f"data: {truth_card.get('platonic_solid')}"
    if attr == "colour":
        real = fold(truth_card.get("king_scale_color") or "")
        return (fold(value) in real or real in fold(value)), f"data: {truth_card.get('king_scale_color')}"
    if attr == "cube_type":
        said = {CUBE_TYPES[t] for t in tokens(value) if t in CUBE_TYPES}
        if not said:
            return None, "no cube type word"
        real = truth_card.get("spatial_type") or "Sephira_Point"
        return real in said, f"data: {real}"
    return None, "unknown attribute"


# --- scoring one answer --------------------------------------------------------------------

def scored_pairs(truth):
    """{frozenset(a, b): {"score", "aspect"}} for every pair the prompt scores or links."""
    pairs = {}
    for d in truth["dignities"]:
        pairs.setdefault(frozenset((d["a"], d["b"])), {})["score"] = d["score"]
    for a in truth["aspects"]:
        p = pairs.setdefault(frozenset((a["a"], a["b"])), {})
        p["aspect"] = a["aspect"].lower()
        if a.get("card_score") is not None:
            p.setdefault("score", a["card_score"])
    return pairs


def positions_of(truth, title):
    return [p["number"] for p in truth["positions"] if p["card"] == title]


def place_cards(truth, names):
    """{position: card title} for the decan positions, whose names hold a card in brackets, such
    as "Decan 10: Venus in Cancer (2 of Cups)". That card names the place; it is not drawn there."""
    places = {}
    for p in truth["positions"]:
        m = re.fullmatch(r"Decan \d+: .*\(([^()]*)\)\s*", p["name"])
        title = names.title(m.group(1)) if m else None
        if title:
            places[p["number"]] = title
    return places


def pair_positions(truth, by_number, places, names, c):
    """The two positions a pair claim means, or None. Uses the claimed numbers when they are two
    real positions; otherwise finds each card (at its claimed position if it is there, else where
    it was drawn, else the decan it names), keeping to one operation when a card was drawn more
    than once."""
    a, b = c["position_a"], c["position_b"]
    if a in by_number and b in by_number and a != b:
        return a, b

    def where(card, hint):
        title = names.title(card)
        if hint in by_number and title in (by_number[hint]["card"], places.get(hint)):
            return [hint]
        return positions_of(truth, title) or [n for n, t in places.items() if t == title]
    pa, pb = where(c["card_a"], a), where(c["card_b"], b)
    if len(pa) == 1 and len(pb) > 1:
        pb = [n for n in pb if by_number[n]["operation"] == by_number[pa[0]]["operation"]]
    elif len(pb) == 1 and len(pa) > 1:
        pa = [n for n in pa if by_number[n]["operation"] == by_number[pb[0]]["operation"]]
    if len(pa) == 1 and len(pb) == 1 and pa != pb:
        return pa[0], pb[0]
    return None


def score_answer(claims, truth, names, answer_text):
    errors, notes = [], []
    expect = truth["expect"]
    drawn = set(truth["drawn"])
    by_number = {p["number"]: p for p in truth["positions"]}
    places = place_cards(truth, names)

    def err(check, what):
        errors.append({"check": check, "what": what})

    # A1, A2: cards and positions
    covered = set()
    for p in claims["positions"]:
        title = names.title(p["card"])
        if title is None:
            notes.append(f"could not read the card name {p['card']!r}")
            continue
        if places.get(p["position"]) == title or (title in places.values() and title not in drawn
                                                   and title != truth.get("significator")):
            # The card named in a decan's name ("Decan 10: Venus in Cancer (2 of Cups)"), not one drawn.
            notes.append(f"place card, not a drawn card: {p['card']!r} at position {p['position']}")
            continue
        if title not in drawn and title != truth.get("significator"):
            err("A1 invented card", f"{p['card']!r} (read as {title}) is not in this reading")
        elif p["position"] in by_number:
            if by_number[p["position"]]["card"] != title:
                err("A2 wrong position", f"position {p['position']}: says {title}, drawn {by_number[p['position']]['card']}")
            else:
                covered.add(p["position"])
        elif p["position"]:
            err("A2 wrong position", f"position {p['position']} does not exist ({p['card']!r})")
    # A3, A4: correspondences
    checked = 0
    for fact in claims["card_facts"]:
        title = names.title(fact["card"])
        if title not in truth["cards"]:
            notes.append(f"fact about a card not in the reading: {fact}")
            continue
        ok, note = check_fact(fact, truth["cards"][title])
        if ok is None:
            continue
        checked += 1
        if not ok:
            err("A4 other system" if "letter" in note and "that is the" in note else "A3 wrong correspondence",
                f"{title}: {fact['attribute']} {fact['value']!r} ({note})")
    # A5, A6: pairs
    pairs = scored_pairs(truth)
    all_scores = [p["score"] for p in pairs.values() if "score" in p]
    no_aspect = {frozenset((x["a"], x["b"])) for x in truth["pairs_without_aspect"]}
    for c in claims["pair_claims"]:
        found = pair_positions(truth, by_number, places, names, c)
        if found is None:
            notes.append(f"pair not tied to positions: {c['card_a']} / {c['card_b']}")
            continue
        a, b = found
        key, label = frozenset((a, b)), f"positions {a} and {b}"
        real = pairs.get(key, {})
        stated = int(c["dignity_score"].replace("+", "")) if re.fullmatch(r"[+-]?\d", c["dignity_score"].strip()) else None
        if stated is not None:
            if "score" not in real:
                err("A5 wrong dignity", f"{label}: gives {c['dignity_score']}, but the prompt scores no such pair")
            elif stated != real["score"]:
                err("A5 wrong dignity", f"{label}: gives {c['dignity_score']}, data {real['score']:+d}")
        if c["dignity_quality"] in QUALITY_SIGN and "score" in real:
            if QUALITY_SIGN[c["dignity_quality"]] != (real["score"] > 0) - (real["score"] < 0):
                err("A5 wrong dignity", f"{label}: calls it {c['dignity_quality']}, data {real['score']:+d}")
        if c["aspect"] != "not_stated":
            if key in no_aspect or not truth["aspects"]:
                err("A6 wrong aspect", f"{label}: says {c['aspect']}, the layout gives this pair no aspect")
            elif real.get("aspect") != c["aspect"]:
                err("A6 wrong aspect", f"{label}: says {c['aspect']}, data {real.get('aspect', 'none')}")
        if "score" in real and all_scores:
            if c["says_strongest"] and real["score"] != max(all_scores):
                err("B5 strongest pair", f"{label} called strongest at {real['score']:+d}; top score is {max(all_scores):+d}")
            if c["says_most_strained"] and real["score"] != min(all_scores):
                err("B5 most strained pair", f"{label} called most strained at {real['score']:+d}; lowest is {min(all_scores):+d}")
    # element counts
    for e in claims["element_counts"]:
        if e["element"] in truth["element_counts"] and e["count"] != truth["element_counts"][e["element"]]:
            err("A3 wrong element count", f"{e['element']} {e['count']}, data {truth['element_counts'][e['element']]}")
    # A7 framework
    named = claims["framework_named"]
    if any(o.lower() in named.lower() for o in truth["framework"]["others"]):
        err("A7 wrong framework", f"names {named!r}; the prompt chose {truth['framework']['chosen']!r}")
    # A8, A9
    if claims["says_significator_mismatch"]:
        err("A8 significator misread", "says the Significator's place disagrees with the printed cards")
    if claims["own_place_treated_as_significant"] and truth["own_place"] and not any(o["unusual"] for o in truth["own_place"]):
        err("A9 own place overread", "treats the Own-Place Check as significant; the prompt marks it not unusual")

    # B4 coverage, B7 recap, B rules
    n = len(truth["positions"])
    tail = [p for p in by_number if p > n - max(1, n // 5)]
    recap = recap_text(answer_text, claims["recap_heading"])
    terms = sorted({t for t in TECH_TERMS if re.search(rf"\b{re.escape(t)}\b", recap.lower())}) if recap else []
    rules = {
        "B1 relates to question": claims["relates_to_question"] if truth["question"] else True,
        "B3 framework as lens": claims["framework_used_as_lens"] >= 2,
        "B6 likely outcome": bool(claims["likely_outcome"].strip()),
        "B6 offered as possibility": claims["outcome_offered_as_possibility"],
        "B6 decision left to querent": claims["leaves_decision_to_querent"],
        "B7 plain recap": bool(recap) and not terms,
    }
    # C1, C3
    special = {}
    if expect.get("cut_off"):
        special["C1 says cut off"] = claims["prompt_status"] == "says_cut_off"
        special["C1 does not interpret"] = not claims["interprets_reading"]
    elif claims["prompt_status"] == "says_cut_off":
        err("C1 false cut-off", "says the prompt was cut off, but it was complete")
    planted = expect.get("planted")
    if planted:
        flagged = " ".join(claims["inconsistencies_flagged"])
        hit = names.title(planted["card"]) and (
            any(names.title(x) == planted["card"] for x in claims["inconsistencies_flagged"])
            or planted["planted_sign"].lower() in flagged.lower())
        special["C3 planted error flagged"] = bool(hit)
        used = [f for f in claims["card_facts"] if names.title(f["card"]) == planted["card"]
                and f["attribute"] == "sign_or_planet"]
        special["C3 used"] = ("planted value" if any(planted["planted_sign"].lower() in f["value"].lower() for f in used)
                              else "true value" if any(planted["true_sign"].lower() in f["value"].lower() for f in used)
                              else "neither")
        # the planted value disagrees with the truth on purpose, so it is not an answer error
        errors = [e for e in errors if not (e["check"].startswith("A3") and planted["card"] in e["what"]
                                            and planted["planted_sign"] in e["what"])]
    hard = [e for e in errors if e["check"][0] == "A"]
    return {
        "case_id": truth["case_id"], "variant": truth["variant"],
        "hard_errors": len(hard), "errors": errors,
        "facts_checked": checked, "pairs_checked": len(claims["pair_claims"]),
        "coverage": len(covered) / n, "coverage_last_fifth": len(covered & set(tail)) / len(tail),
        "positions_missed": sorted(set(by_number) - covered),
        "rules": rules, "recap_terms": terms, "special": special,
        "prompt_status": claims["prompt_status"], "likely_outcome": claims["likely_outcome"],
        "notes": notes,
    }


def recap_text(answer, heading):
    """The text after the recap heading (or the last paragraph when there is none)."""
    if heading and heading.strip() in answer:
        return answer.split(heading.strip(), 1)[1]
    m = list(re.finditer(r"^.*recap.*$", answer, re.I | re.M))
    if m:
        return answer[m[-1].end():]
    paras = [p for p in answer.split("\n\n") if p.strip()]
    return paras[-1] if paras else ""


# --- files ---------------------------------------------------------------------------------

def answer_files(answers):
    for path in sorted(glob.glob(os.path.join(answers, "*.md"))):
        m = re.fullmatch(r"(.+?)__(.+?)__(\w+)\.md", os.path.basename(path))
        if m:
            yield path, m[1], m[2], m[3]


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f) if path.endswith(".json") else f.read()


# List prices in US dollars per million tokens (input, output), for the cost each run prints.
PRICES = {"claude-opus-5-5": (4.00, 20.00), "claude-sonnet-5-5": (2.00, 10.00), "claude-haiku-5-5": (0.10, 0.50)}
ANSWER_MODEL = "claude-opus-5-5"
# The pilot: the snapshot seed's five full prompts, each answered twice.
PILOT_SEED, PILOT_RUNS = "408850", 2


def cost(model, usage):
    """Dollars for one response's usage, or 0.0 for a model without a listed price."""
    price_in, price_out = PRICES.get(model, (0.0, 0.0))
    tokens_in = (usage.input_tokens + (getattr(usage, "cache_creation_input_tokens", 0) or 0)
                 + (getattr(usage, "cache_read_input_tokens", 0) or 0))
    return (tokens_in * price_in + usage.output_tokens * price_out) / 1_000_000


def make_client():
    try:
        import anthropic
    except ImportError:
        sys.exit("This needs the anthropic package: .venv/bin/python -m pip install anthropic")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Set your key first, in this Terminal window only: export ANTHROPIC_API_KEY=sk-ant-...")
    return anthropic.Anthropic()


def ai_label(model):
    """'claude-opus-5-5' -> 'opus-5-5', the middle part of an answer's file name."""
    return model.removeprefix("claude-")


def run(client, build, answers, case_ids, model=ANSWER_MODEL, runs=1, effort="medium"):
    """Sends each prompt to `model` as a fresh conversation, like pasting it into a new chat,
    and saves the answer as <case>__<ai>__<run>.md with a .meta.json beside it (the model that
    actually answered, tokens, cost, stop reason). Answers already saved are not sent again.
    Returns the total cost of the calls made."""
    os.makedirs(answers, exist_ok=True)
    total = 0.0
    for case_id in case_ids:
        prompt = load(os.path.join(build, "prompts", f"{case_id}.md"))
        for n in range(1, runs + 1):
            base = os.path.join(answers, f"{case_id}__{ai_label(model)}__{n}")
            if os.path.exists(base + ".md"):
                continue
            # A fresh conversation per run, no system prompt: what a visitor does when they
            # paste the prompt. Server-side fallbacks answer on another model if this one
            # declines; the meta file records which model answered.
            with client.beta.messages.stream(
                    model=model, max_tokens=64000, output_config={"effort": effort},
                    betas=["server-side-fallback-2026-07-01"], fallbacks="default",
                    messages=[{"role": "user", "content": prompt}]) as stream:
                response = stream.get_final_message()
            spent = cost(model, response.usage)
            total += spent
            meta = {"case_id": case_id, "run": n, "requested_model": model, "served_model": response.model,
                    "effort": effort, "stop_reason": response.stop_reason,
                    "input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens,
                    "cost_usd": round(spent, 4)}
            with open(base + ".meta.json", "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=1)
            text = "".join(b.text for b in response.content if b.type == "text")
            if response.stop_reason == "refusal" or not text.strip():
                print(f"{case_id} run {n}: no answer ({response.stop_reason}), see {base}.meta.json")
                continue
            with open(base + ".md", "w", encoding="utf-8") as f:
                f.write(text)
            print(f"{case_id} run {n}: {meta['input_tokens']:,} in, {meta['output_tokens']:,} out, ${spent:.3f}"
                  + (f" (answered by {response.model})" if response.model != model else ""))
    return total


def extract(client, build, answers, model=EXTRACT_MODEL, again=False):
    """Writes <answer>.claims.json for every answer that has none (every answer, with again=True,
    after the extract instructions change). Returns the total cost."""
    total = 0.0
    for path, case_id, ai, run_n in answer_files(answers):
        out = path[:-3] + ".claims.json"
        if os.path.exists(out) and not again:
            continue
        truth = load(os.path.join(build, "truth", f"{case_id}.json"))
        positions = "\n".join(f"{p['number']}. {p['name']}" for p in truth["positions"])
        response = client.messages.create(
            model=model, max_tokens=16000, output_config={"effort": "low", "format": {"type": "json_schema", "schema": CLAIMS_SCHEMA}},
            messages=[{"role": "user", "content": EXTRACT_INSTRUCTIONS.format(positions=positions, answer=load(path))}])
        text = next((b.text for b in response.content if b.type == "text"), "")
        if response.stop_reason != "end_turn" or not text:
            print(f"{os.path.basename(path)}: claims not extracted ({response.stop_reason})")
            continue
        spent = cost(model, response.usage)
        total += spent
        with open(out, "w", encoding="utf-8") as f:
            json.dump(json.loads(text), f, ensure_ascii=False, indent=1)
        print(f"{os.path.basename(out)}: {response.usage.input_tokens:,} in, {response.usage.output_tokens:,} out, ${spent:.3f}")
    return total


def score(build, answers):
    names = Names(load(os.path.join(build, "deck.json")))
    rows = []
    for path, case_id, ai, run_n in answer_files(answers):
        claims_path = path[:-3] + ".claims.json"
        if not os.path.exists(claims_path):
            print(f"no claims yet for {os.path.basename(path)} (run extract)")
            continue
        truth = load(os.path.join(build, "truth", f"{case_id}.json"))
        result = {"ai": ai, "run": run_n, **score_answer(load(claims_path), truth, names, load(path))}
        with open(path[:-3] + ".score.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=1)
        rows.append(result)
    with open(os.path.join(answers, "results.md"), "w", encoding="utf-8") as f:
        f.write(results_md(rows))
    print(results_md(rows))


def results_md(rows):
    lines = ["| Answer | AI | Hard errors | Facts checked | Pairs | Coverage | Rules met | Special |",
             "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        met = sum(bool(v) for v in r["rules"].values())
        special = ", ".join(f"{k}: {v}" for k, v in r["special"].items()) or "-"
        lines.append(f"| {r['case_id']} #{r['run']} | {r['ai']} | {r['hard_errors']} | {r['facts_checked']} | "
                     f"{r['pairs_checked']} | {r['coverage']:.0%} | {met}/{len(r['rules'])} | {special} |")
    for r in rows:
        if r["errors"] or not all(r["rules"].values()):
            lines.append(f"\n**{r['case_id']} #{r['run']} ({r['ai']})**")
            lines += [f"- {e['check']}: {e['what']}" for e in r["errors"]]
            lines += [f"- {k}: not met" + (f" ({', '.join(r['recap_terms'])})" if k.startswith("B7") and r["recap_terms"] else "")
                      for k, v in r["rules"].items() if not v]
    return "\n".join(lines) + "\n"


def pilot(client, out, model=ANSWER_MODEL):
    """Builds the prompt set into <out>/build, answers the pilot prompts into <out>/answers,
    extracts and scores them. Safe to run again: finished steps are skipped."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import ai_check
    build, answers = os.path.join(out, "build"), os.path.join(out, "answers")
    if not os.path.exists(os.path.join(build, "cases.json")):
        ai_check.build(build)
    cases = [f"s{PILOT_SEED}_sp{key}_full" for key in ai_check.SPREAD_KEYS]
    spent = run(client, build, answers, cases, model=model, runs=PILOT_RUNS)
    spent += extract(client, build, answers)
    score(build, answers)
    print(f"This run cost about ${spent:.2f}. Results: {os.path.join(answers, 'results.md')}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("pilot", help="build, answer the 10 pilot prompts, extract and score")
    p.add_argument("--out", default=os.path.join("output", "ai_check"), help="folder for everything (default output/ai_check, not committed)")
    p.add_argument("--model", default=ANSWER_MODEL)
    p = sub.add_parser("run", help="send prompts to Claude and save the answers")
    p.add_argument("--build", required=True)
    p.add_argument("--answers", required=True)
    p.add_argument("--cases", required=True, help="comma-separated case ids, or 'all' for every case in cases.json")
    p.add_argument("--model", default=ANSWER_MODEL)
    p.add_argument("--runs", type=int, default=1)
    p.add_argument("--effort", default="medium")
    for name in ("extract", "score"):
        p = sub.add_parser(name)
        p.add_argument("--build", required=True, help="folder written by scripts/ai_check.py build")
        p.add_argument("--answers", required=True, help="folder of <case>__<ai>__<run>.md answers")
        if name == "extract":
            p.add_argument("--model", default=EXTRACT_MODEL)
            p.add_argument("--again", action="store_true", help="extract again even where claims exist")
    args = parser.parse_args(argv)
    if args.command == "pilot":
        pilot(make_client(), args.out, args.model)
    elif args.command == "run":
        cases = ([c["id"] for c in load(os.path.join(args.build, "cases.json"))] if args.cases == "all"
                 else [c.strip() for c in args.cases.split(",") if c.strip()])
        print(f"total ${run(make_client(), args.build, args.answers, cases, args.model, args.runs, args.effort):.2f}")
    elif args.command == "extract":
        print(f"total ${extract(make_client(), args.build, args.answers, args.model, args.again):.2f}")
    else:
        score(args.build, args.answers)
    return 0


if __name__ == "__main__":
    sys.exit(main())

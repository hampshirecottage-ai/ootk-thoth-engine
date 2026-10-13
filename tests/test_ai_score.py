"""scripts/ai_score.py must catch each kind of error, and pass an answer that has none."""
import copy
import json
import os
import sys

import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))

import ai_check  # noqa: E402
import ai_score  # noqa: E402

ANSWER = "Reading...\n\n5. Plain-language recap\nYou are thinking hard about it. Take your time and check the facts.\n"


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = str(tmp_path_factory.mktemp("ai_check"))
    ai_check.build(out)

    def truth(case_id):
        with open(os.path.join(out, "truth", f"{case_id}.json"), encoding="utf-8") as f:
            return json.load(f)
    with open(os.path.join(out, "deck.json"), encoding="utf-8") as f:
        return truth, ai_score.Names(json.load(f))


def clean_claims(truth):
    """Claims that say only true things about the reading."""
    pos = truth["positions"]
    pairs = [{"position_a": d["a"], "position_b": d["b"], "card_a": d["cards"][0], "card_b": d["cards"][1],
              "dignity_score": f"{d['score']:+d}", "dignity_quality": "not_stated", "aspect": "not_stated",
              "says_strongest": False, "says_most_strained": False} for d in truth["dignities"]]
    facts = [{"card": t, "attribute": "solid", "value": c["platonic_solid"]} for t, c in truth["cards"].items()]
    facts += [{"card": t, "attribute": "hebrew_letter", "value": c["hebrew_letter"]} for t, c in truth["cards"].items()
              if c["hebrew_letter"]]
    return {
        "prompt_status": "says_complete", "last_position_seen": 0, "interprets_reading": True,
        "inconsistencies_flagged": [], "framework_named": truth["framework"]["chosen"],
        "positions": [{"position": p["number"], "card": p["card"]} for p in pos],
        "card_facts": facts, "pair_claims": pairs,
        "element_counts": [{"element": e, "count": n} for e, n in truth["element_counts"].items()],
        "own_place_treated_as_significant": False, "says_significator_mismatch": False,
        "relates_to_question": True, "framework_used_as_lens": 2, "likely_outcome": "A slow change.",
        "outcome_offered_as_possibility": True, "leaves_decision_to_querent": True,
        "recap_heading": "5. Plain-language recap",
    }


@pytest.mark.parametrize("case_id", ["s408850_sp3_full", "s408850_sp9_full", "s408850_sp12_full"])
def test_true_claims_score_clean(built, case_id):
    truth, names = built
    t = truth(case_id)
    result = ai_score.score_answer(clean_claims(t), t, names, ANSWER)
    assert result["errors"] == []
    assert result["coverage"] == 1 and all(result["rules"].values())


def checks(result):
    return {e["check"] for e in result["errors"]}


def test_catches_each_error(built):
    truth, names = built
    t = truth("s408850_sp9_full")
    claims = clean_claims(t)
    claims["positions"].append({"position": 0, "card": "The Tower"})                      # not drawn
    claims["positions"][3]["card"] = "Lust"                                               # drawn, but at position 5
    claims["card_facts"].append({"card": "Prince of Swords", "attribute": "hebrew_letter", "value": "Tzaddi"})
    claims["card_facts"].append({"card": "7 of Cups", "attribute": "sign_or_planet", "value": "Venus in Taurus"})
    claims["pair_claims"][0]["dignity_score"] = "-2"
    claims["pair_claims"].append({**claims["pair_claims"][1], "position_a": 1, "position_b": 7, "dignity_score": "",
                                  "aspect": "trine"})
    claims["framework_named"] = "Divine Light Flow"
    claims["own_place_treated_as_significant"] = True
    claims["recap_heading"] = ""
    result = ai_score.score_answer(claims, t, names, "...\nRecap\nThe Chesed dignity is strong.\n")
    assert {"A1 invented card", "A2 wrong position", "A4 other system", "A3 wrong correspondence",
            "A5 wrong dignity", "A6 wrong aspect", "A7 wrong framework", "A9 own place overread"} <= checks(result)
    assert not result["rules"]["B7 plain recap"] and "chesed" in result["recap_terms"]
    assert 4 in result["positions_missed"]


def test_mentioning_an_undrawn_card_as_a_meaning_is_not_an_error(built):
    truth, names = built
    t = truth("s408850_sp3_full")
    claims = clean_claims(t)
    claims["card_facts"].append({"card": "Prince of Swords", "attribute": "hebrew_letter", "value": "Heh, the Star's letter"})
    assert ai_score.score_answer(claims, t, names, ANSWER)["errors"] == []


def test_cut_and_planted_prompts(built):
    truth, names = built
    t = truth("s408850_sp12_cut40")
    claims = clean_claims(t)
    assert ai_score.score_answer(claims, t, names, ANSWER)["special"] == {
        "C1 says cut off": False, "C1 does not interpret": False}
    claims.update(prompt_status="says_cut_off", interprets_reading=False)
    assert all(ai_score.score_answer(claims, t, names, ANSWER)["special"].values())

    t = truth("s408850_sp3_planted")
    planted = t["expect"]["planted"]
    claims = clean_claims(t)
    claims["card_facts"].append({"card": planted["card"], "attribute": "sign_or_planet",
                                 "value": planted["planted_value"]})
    result = ai_score.score_answer(claims, t, names, ANSWER)
    assert result["special"] == {"C3 planted error flagged": False, "C3 used": "planted value"}
    assert result["hard_errors"] == 0
    claims["inconsistencies_flagged"] = [f"The 7 of Cups is given as {planted['planted_value']}, but Cups are Water"]
    assert ai_score.score_answer(claims, t, names, ANSWER)["special"]["C3 planted error flagged"]


def test_false_cut_off_claim(built):
    truth, names = built
    t = truth("s408850_sp1_full")
    claims = copy.deepcopy(clean_claims(t))
    claims["prompt_status"] = "says_cut_off"
    assert "C1 false cut-off" in checks(ai_score.score_answer(claims, t, names, ANSWER))


def test_names_read_every_spelling(built):
    _, names = built
    assert names.title("Lust (XI)") == "XI - Lust"
    assert names.title("Strength") is None        # the Thoth 9 of Wands, or the Waite name of Lust
    assert names.title("Temperance") == "XIV - Art"
    assert names.title("4 of Swords, Truce") == "4 of Swords - Truce"
    assert names.title("Five of Pentacles") == "5 of Disks - Worry"
    assert names.title("Knight of Cups") == "Knight of Cups"          # the Thoth Knight, not the Waite one
    assert names.title("Page of Wands") == "Princess of Wands"
    assert names.title("the Hierophant") == "V - The Hierophant"


def test_decan_place_cards_are_not_drawn_cards(built):
    # Decan names hold a card ("Decan 10: Venus in Cancer (2 of Cups)"); naming it is not a claim it was drawn.
    truth, names = built
    t = truth("s408850_sp12_full")
    places = ai_score.place_cards(t, names)
    assert len(places) == 36 and min(places) == 40
    by_number = {p["number"]: p for p in t["positions"]}
    n, place = next((n, c) for n, c in sorted(places.items()) if c not in t["drawn"])
    m, drawn_place = next((m, c) for m, c in sorted(places.items()) if c in t["drawn"] and by_number[m]["card"] != c)
    claims = clean_claims(t)
    claims["positions"] += [{"position": n, "card": place}, {"position": m, "card": drawn_place}]
    result = ai_score.score_answer(claims, t, names, ANSWER)
    assert result["errors"] == [] and len([x for x in result["notes"] if x.startswith("place card")]) == 2


def test_pair_given_one_position_twice_is_found_by_its_cards(built):
    truth, names = built
    t = truth("s408850_sp12_full")
    places = ai_score.place_cards(t, names)
    by_number = {p["number"]: p for p in t["positions"]}
    aspect = next(a for a in t["aspects"] if a["operation"] == 4 and places[a["a"]] not in t["drawn"]
                  and len(ai_score.positions_of(t, by_number[a["b"]]["card"])) == 1)
    pair = {"position_a": aspect["a"], "position_b": aspect["a"], "card_a": places[aspect["a"]],
            "card_b": by_number[aspect["b"]]["card"], "dignity_score": "", "dignity_quality": "not_stated",
            "aspect": aspect["aspect"].lower(), "says_strongest": False, "says_most_strained": False}
    assert ai_score.pair_positions(t, by_number, places, names, pair) == (aspect["a"], aspect["b"], False)
    claims = clean_claims(t)
    claims["pair_claims"].append(pair)
    assert ai_score.score_answer(claims, t, names, ANSWER)["errors"] == []
    wrong = {**pair, "aspect": next(x for x in ("trine", "square") if x != pair["aspect"])}
    claims["pair_claims"][-1] = wrong
    assert "A6 wrong aspect" in checks(ai_score.score_answer(claims, t, names, ANSWER))


def test_own_place_not_checked_where_the_spread_has_none(built):
    truth, names = built
    t = truth("s408850_sp7_full")
    assert t["own_place"] == []
    claims = clean_claims(t)
    claims["own_place_treated_as_significant"] = True
    assert ai_score.score_answer(claims, t, names, ANSWER)["errors"] == []


def test_ootk_number_slips_go_to_check_by_hand(built):
    # Opening of the Key place names repeat their own numbers ("9. Sagittarius" is position 36), so a
    # card claimed one place off, but drawn once in that operation, is listed to check by hand.
    truth, names = built
    t = truth("s408850_sp12_full")
    by_number = {p["number"]: p for p in t["positions"]}
    once = [p for p in t["positions"] if p["operation"] == 3 and len(ai_score.positions_of(t, p["card"])) == 1]
    p, q = once[0], next(x for x in t["positions"] if x["operation"] == 3 and x["card"] != once[0]["card"])
    claims = clean_claims(t)
    claims["positions"].append({"position": q["number"], "card": p["card"]})
    result = ai_score.score_answer(claims, t, names, ANSWER)
    assert result["errors"] == [] and [e["check"] for e in result["check_by_hand"]] == ["A2 wrong position?"]

    # A pair claimed at the wrong numbers is read by its cards; true claims raise nothing.
    aspect = next(a for a in t["aspects"] if a["operation"] == 3
                  and all(len(ai_score.positions_of(t, by_number[n]["card"])) == 1 for n in (a["a"], a["b"])))
    off = next(n for n in range(28, 40) if n not in (aspect["a"], aspect["b"]))
    pair = {"position_a": aspect["a"], "position_b": off, "card_a": by_number[aspect["a"]]["card"],
            "card_b": by_number[aspect["b"]]["card"], "dignity_score": "", "dignity_quality": "not_stated",
            "aspect": aspect["aspect"].lower(), "says_strongest": False, "says_most_strained": False}
    claims = clean_claims(t)
    claims["pair_claims"].append(pair)
    result = ai_score.score_answer(claims, t, names, ANSWER)
    assert result["errors"] == [] and result["check_by_hand"] == []
    claims["pair_claims"][-1] = {**pair, "aspect": next(x for x in ("trine", "square") if x != pair["aspect"])}
    result = ai_score.score_answer(claims, t, names, ANSWER)
    assert result["errors"] == [] and [e["check"] for e in result["check_by_hand"]] == ["A6 wrong aspect?"]
    assert "Check by hand" in ai_score.results_md([{**result, "ai": "x", "run": 1}])


def test_other_spreads_keep_hard_position_errors(built):
    truth, names = built
    t = truth("s408850_sp9_full")
    claims = clean_claims(t)
    claims["positions"][3]["card"] = claims["positions"][4]["card"]
    result = ai_score.score_answer(claims, t, names, ANSWER)
    assert "A2 wrong position" in checks(result) and result["check_by_hand"] == []

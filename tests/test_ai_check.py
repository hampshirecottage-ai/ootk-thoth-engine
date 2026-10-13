"""scripts/ai_check.py builds the prompts an AI is tested on, and the truth to score it against.

The full prompts must be the ones the site builds, so they are compared with the saved
snapshots; the variants must differ from them only in the way each one says.
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))

import ai_check  # noqa: E402
from test_prompt_snapshots import SEED, SPREAD_KEYS  # noqa: E402


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("ai_check")
    cases = ai_check.build(str(out))
    return out, {c["id"]: c for c in cases}


def read(out, case, kind):
    path = os.path.join(out, case[kind])
    with open(path, encoding="utf-8") as f:
        return json.load(f) if kind == "truth" else f.read()


def test_case_counts(built):
    _, cases = built
    variants = [c["variant"] for c in cases.values()]
    assert variants.count("full") == len(ai_check.SEEDS) * len(ai_check.SPREAD_KEYS)
    assert variants.count("cardsonly") == len(ai_check.CARDS_ONLY)
    assert variants.count("planted") == len(ai_check.SPREAD_KEYS)
    assert variants.count("cut40") + variants.count("cut85") == len(ai_check.CUTS)


@pytest.mark.parametrize("spread_key", [k for k in ai_check.SPREAD_KEYS if k in SPREAD_KEYS])
def test_full_prompt_matches_snapshot(built, spread_key):
    out, cases = built
    prompt = read(out, cases[f"s{SEED}_sp{spread_key}_full"], "prompt")
    with open(os.path.join(HERE, "prompt_snapshots", f"spread_{spread_key}.md"), encoding="utf-8") as f:
        assert prompt == f.read()


def test_truth_matches_prompt(built):
    out, cases = built
    for case in cases.values():
        if case["variant"] != "full":
            continue
        prompt, truth = read(out, case, "prompt"), read(out, case, "truth")
        assert prompt.rstrip().endswith(truth["end_marker"])
        for p in truth["positions"]:
            assert f"### Position {p['number']}:" in prompt
            assert f"- **Card Drawn**: {p['card']}" in prompt
        assert truth["framework"]["chosen"] in prompt
        assert set(truth["cards"]) >= set(truth["drawn"])


def test_seeds_cover_every_framework_and_unusual_own_place(built):
    out, cases = built
    truths = [read(out, c, "truth") for c in cases.values() if c["variant"] == "full"]
    chosen = " ".join(t["framework"]["chosen"] for t in truths)
    assert all(f in chosen for f in ai_check.FRAMEWORKS)
    assert any(o["unusual"] for t in truths for o in t["own_place"])
    assert any(p["shown"] and p["op"] > 1 for t in truths for p in t["significator_places"])
    assert any(not t["question"] for t in truths)


def test_cut_prompts_lose_the_end_marker(built):
    out, cases = built
    for case in cases.values():
        if not case["variant"].startswith("cut"):
            continue
        prompt, truth = read(out, case, "prompt"), read(out, case, "truth")
        full = read(out, cases[f"s{truth['seed']}_sp12_full"], "prompt")
        assert full.startswith(prompt) and len(prompt) < len(full)
        assert truth["end_marker"] not in prompt.split("\n", 2)[2]   # only the header names it
        assert prompt.rstrip("\n").endswith(truth["expect"]["last_visible_line"])


def test_planted_prompt_changes_one_line(built):
    out, cases = built
    for case in cases.values():
        if case["variant"] != "planted":
            continue
        truth = read(out, case, "truth")
        full = read(out, cases[case["id"].replace("planted", "full")], "prompt").splitlines()
        changed = [(a, b) for a, b in zip(full, read(out, case, "prompt").splitlines()) if a != b]
        planted = truth["expect"]["planted"]
        assert changed == [(f"- **Attribution**: {planted['true_value']}",
                            f"- **Attribution**: {planted['planted_value']}")]
        assert planted["true_sign"] != planted["planted_sign"]


def test_cards_only_keeps_cards_and_drops_tables(built):
    out, cases = built
    for case in cases.values():
        if case["variant"] != "cardsonly":
            continue
        prompt, truth = read(out, case, "prompt"), read(out, case, "truth")
        assert "ELEMENTAL VECTOR" not in prompt and "PAIRWISE ELEMENTAL DIGNITY" not in prompt
        assert all(f"- **Card Drawn**: {p['card']}" in prompt for p in truth["positions"])
        assert "Plain-Language Recap" in prompt and prompt.rstrip().endswith(truth["end_marker"])


def test_deck_names_every_card():
    deck = ai_check.deck_table(ai_check.load_reference())
    assert len(deck["cards"]) == 78
    names = {n["name"] for c in deck["cards"].values() for n in c["names"]}
    assert {"Strength", "Five of Pentacles", "Page of Cups", "The World", "Lust"} <= names
    assert "Knight of Cups" in deck["collisions"]

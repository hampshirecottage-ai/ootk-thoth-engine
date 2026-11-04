"""scripts/ai_parts.py: the leave-one-out round. Building, sending (with a stand-in client, so
nothing is spent) and the code-only report."""
import json
import os
import sys
from types import SimpleNamespace

import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))

import ai_parts  # noqa: E402
from ootk.report import COMPONENTS  # noqa: E402


@pytest.fixture(scope="module")
def ref():
    return ai_parts.load_reference()


def test_scramble_keeps_names_and_suits(ref):
    rows = ref["rows"]
    mixed = ai_parts.scramble(rows)
    assert set(mixed) == set(rows)
    moved = 0
    for title, row in mixed.items():
        for key in ai_parts.KEEP & set(row):
            assert row[key] == rows[title][key]
        moved += row["attribution"] != rows[title]["attribution"]
    assert moved > 60
    assert ai_parts.scramble(rows) == mixed          # same every time


def test_each_switch_changes_its_prompt_and_not_the_cards(ref):
    full = ai_parts.build_prompt(ref, "408850", "9")
    cards = [line for line in full.splitlines() if line.startswith("- **Card Drawn**")]
    for part in COMPONENTS:
        cut = ai_parts.build_prompt(ref, "408850", "9", {part})
        assert [line for line in cut.splitlines() if line.startswith("- **Card Drawn**")] == cards
    scrambled = ai_parts.build_prompt(ref, "408850", "9", rows=ai_parts.scramble(ref["rows"]))
    assert [line for line in scrambled.splitlines() if line.startswith("- **Card Drawn**")] == cards
    assert scrambled != full


def fake_batch_client(answer_for):
    """A stand-in for anthropic.Anthropic() that answers a batch at once."""
    sent = {}

    def create(requests):
        sent["requests"] = requests
        return SimpleNamespace(id="msgbatch_test")

    def results(batch_id):
        for r in sent["requests"]:
            if "format" in r["params"].get("output_config", {}):      # the lean reading
                text = json.dumps({"lean": "wait" if "_full__" in r["custom_id"] else "go_ahead"})
            else:
                text = answer_for(r["custom_id"])
            msg = SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], stop_reason="end_turn",
                                  usage=SimpleNamespace(input_tokens=1000, output_tokens=500))
            yield SimpleNamespace(custom_id=r["custom_id"], result=SimpleNamespace(type="succeeded", message=msg))

    batches = SimpleNamespace(
        create=create, results=results,
        retrieve=lambda batch_id: SimpleNamespace(processing_status="ended",
                                                  request_counts=SimpleNamespace(processing=0, succeeded=0)))
    return SimpleNamespace(messages=SimpleNamespace(batches=batches)), sent


def test_round_asks_sends_one_batch_and_reports(tmp_path, monkeypatch):
    monkeypatch.setattr(ai_parts, "SEEDS", ("408850",))
    monkeypatch.setattr(ai_parts, "SPREAD_KEYS", ("9",))

    def answer(cid):
        if "_full__" in cid:
            return "The Lovers sits in Gemini; the dignity is friendly. Aleph and Tiphareth matter."
        if "_no-astrology__" in cid:
            return "The Lovers with a friendly dignity. Aleph and Tiphareth matter."
        return "Something else entirely about the reading."

    client, sent = fake_batch_client(answer)
    out = str(tmp_path)
    assert ai_parts.round_(out, ask=lambda q: "n", client=client) is None
    assert "requests" not in sent

    text = ai_parts.round_(out, ask=lambda q: "y", client=client, wait=0)
    with open(os.path.join(out, "build", "cases.json"), encoding="utf-8") as f:
        n_cases = len(json.load(f)["cases"])
    assert len(sent["requests"]) == n_cases * ai_parts.RUNS
    assert all(r["params"]["model"] == "claude-haiku-5-5" for r in sent["requests"])
    assert not os.path.exists(os.path.join(out, "batch.json"))
    assert "Repeat noise" in text and "Scrambled correspondences" in text
    assert f"Lean read by claude-haiku-5-5 for {n_cases * ai_parts.RUNS} of them" in text
    assert "same lean **100%**" in text
    astro = next(line for line in text.splitlines() if line.startswith("| Astrology"))
    assert astro.split("|")[2].strip() == "1.0" and astro.split("|")[3].strip() == "0.0"

    # Everything saved: running again sends nothing.
    sent.clear()
    ai_parts.round_(out, ask=lambda q: "y", client=client, wait=0)
    assert "requests" not in sent


def test_terms_cover_every_part():
    assert set(ai_parts.TERMS) == set(COMPONENTS)
    found = ai_parts.mentions("Fire of Water in Leo; Aleph; Kether; Puer; trine; gematria; Lord of War; "
                              "angel Vehuiah; day ruler; gods; hexagram; dignity; Book T count")
    assert all(found[p] >= 1 for p in COMPONENTS), found


def test_summary_lean_and_cards(ref):
    answer = ("## Position 1\nThe Lovers in Gemini.\n\n## Closing Summary\nThe Lovers and the Ace of Cups "
              "say go ahead: the time is favourable.\n\n## Plain-Language Recap\nMake the change.")
    tail = ai_parts.summary(answer)
    assert tail.startswith("## Closing Summary") and "Position 1" not in tail
    assert ai_parts.lean(tail) == 1
    assert ai_parts.lean("Not yet: wait and hold off.") == -1
    assert ai_parts.lean("Nothing either way.") == 0
    named = ai_parts.cards_named(tail, ai_parts.card_patterns(ref))
    assert {t for t in named if "Lovers" in t} and {t for t in named if t.startswith("Ace of Cups")}
    assert ai_parts.set_distance({1, 2}, {2, 3}) == pytest.approx(2 / 3)

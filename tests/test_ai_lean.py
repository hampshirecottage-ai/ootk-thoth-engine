"""scripts/ai_lean.py, without calling any AI: the prompts it builds and how it scores answers."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import ai_lean  # noqa: E402


def test_build_writes_three_forms_per_seed(tmp_path):
    cases = ai_lean.build(str(tmp_path))
    assert len(cases) == len(ai_lean.SEEDS) * len(ai_lean.VARIANTS)
    by = {(c["seed"], c["variant"]): c["chars"] for c in cases}
    for seed in ai_lean.SEEDS:
        assert by[(seed, "lean")] < by[(seed, "current")] < by[(seed, "timing")]
    lean = (tmp_path / "prompts" / "s408850_sp13_lean.md").read_text(encoding="utf-8")
    current = (tmp_path / "prompts" / "s408850_sp13_current.md").read_text(encoding="utf-8")
    assert "Book T times the matter" in lean and "Book T times the matter" not in current
    t = json.loads((tmp_path / "truth_408850.json").read_text(encoding="utf-8"))
    assert t["timing"] == {"pos": 77, "card": "3 of Cups - Abundance", "how": "count",
                           "start": "2027-07-02", "end": "2027-07-12"}
    assert "Queen of Cups" in t["counted"]


def test_timeline_and_overlap():
    answer = "Text\n\n## Timeline\n- the turn: 2027-07-03 to 2027-07-11\n- a day: 2026-12-02\n\n## After\n- x: 2030-01-01\n"
    assert ai_lean.timeline(answer) == [("2027-07-03", "2027-07-11"), ("2026-12-02", "2026-12-02")]
    assert ai_lean.overlaps(("2027-07-03", "2027-07-11"), ("2027-07-02", "2027-07-12"))
    assert ai_lean.overlaps(("2027-07-13", "2027-07-20"), ("2027-07-02", "2027-07-12"))     # one day slack
    assert not ai_lean.overlaps(("2027-08-01", "2027-08-10"), ("2027-07-02", "2027-07-12"))
    assert not ai_lean.overlaps(None, ("2027-07-02", "2027-07-12"))
    assert ai_lean.timeline("no timeline here") == []


def test_score_answer_counts_invented_cards_and_timing():
    import ai_parts
    from ai_check import load_reference
    patterns = ai_parts.card_patterns(load_reference())
    t = {"drawn": ["Queen of Cups", "XVI - The Tower"], "counted": ["Queen of Cups", "XVI - The Tower"],
         "timing": {"start": "2027-07-02", "end": "2027-07-12"}}
    s = ai_lean.score_answer(
        "The Queen of Cups meets the Tower and the Three of Swords.\n\n## Timeline\n- turn: 2027-07-05 to 2027-07-09\n",
        t, patterns)
    assert s["on_rule"] and s["count_coverage"] == 1.0
    assert s["invented"] == ["3 of Swords - Sorrow"]
    assert not s["cut_claim"]

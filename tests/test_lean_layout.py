"""The lean prompt layout (report.LAYOUTS, analyze_reading(layout="lean")): positions in one line
each, the count and pairs next, each card's correspondences once. It must carry exactly the
same cards, correspondences, counts, pairs and scores as the full layout, and the full layout
must stay the prompt the snapshots hold. The Book T timing rule names one card's decan window."""
import re
import sys
from datetime import datetime, timezone

import pytest

from ootk.report import LAYOUTS, build_analytical_prompt
from ootk.spreads import BOOK_T_KEY

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from test_prompt_snapshots import build_book_t_prompt, build_prompt  # noqa: E402

DRAWN = datetime(2026, 11, 15, 20, 0, tzinfo=timezone.utc)


def prompt(spread_key, **settings):
    settings.setdefault("drawn_at", DRAWN)
    if spread_key == BOOK_T_KEY:
        return build_book_t_prompt(**settings)
    return build_prompt(spread_key, **settings)


def placed(text):
    """{position number: card} from either layout."""
    full = re.findall(r"^### Position (\d+): .*\n- \*\*Card Drawn\*\*: (.+)$", text, re.M)
    lean = re.findall(r"^- Pos (\d+), .*: (.+)$", text, re.M)
    return {int(n): card for n, card in (full or lean)}


def details(text):
    """{card: its correspondence lines} from either layout."""
    out = {}
    for m in re.finditer(r"^### (?:Position \d+: .*\n- \*\*Card Drawn\*\*: (.+)|(.+?) \(Pos [\d, ]+\))\n"
                         r"((?:- .*\n)*)", text, re.M):
        out.setdefault(m[1] or m[2], m[3])
    return out


def section(text, title):
    m = re.search(rf"^## \d+\. {title}\n(.*?)(?=^---$)", text, re.M | re.S)
    return re.sub(r"\bsections? \d(-\d)?", "section n", m[1]) if m else None


@pytest.mark.parametrize("spread_key", ("1", "3", "7", "10", "14"))
def test_lean_is_the_full_layout_when_no_card_repeats(spread_key):
    assert prompt(spread_key, layout="lean") == prompt(spread_key)


@pytest.mark.parametrize("spread_key", ("12", BOOK_T_KEY))
def test_lean_carries_the_same_reading(spread_key):
    full, lean = prompt(spread_key), prompt(spread_key, layout="lean")
    assert placed(lean) == placed(full) and len(placed(full)) == full.count("### Position ")
    assert details(lean) == details(full)
    for title in ("PAIRWISE ELEMENTAL DIGNITY INTERACTIONS", "ELEMENTAL VECTOR DISTRIBUTION",
                  "SPATIAL & GEOMETRIC VECTOR ANALYSIS"):
        assert section(lean, title) == section(full, title)
    for table in ("**Liber 777 Rows:**", "**Golden Dawn Titles**", "**Angels of the Decans**"):
        assert (table in lean) == (table in full)
        if table in full:
            assert lean.split(table)[1].split("\n\n")[0] == full.split(table)[1].split("\n\n")[0]
    assert lean.rstrip().rsplit("\n", 1)[-1] == full.rstrip().rsplit("\n", 1)[-1]   # end marker
    assert len(lean) < len(full)


@pytest.mark.parametrize("spread_key", ("12", BOOK_T_KEY))
def test_lean_section_references_point_at_the_right_sections(spread_key):
    lean = prompt(spread_key, layout="lean")
    titles = {int(n): t for n, t in re.findall(r"^## (\d+)\. (.+)$", lean, re.M)}
    assert list(titles) == list(range(1, len(titles) + 1))
    layout = re.search(r"^\*\*How This Prompt Is Laid Out:\*\* (.+)$", lean, re.M)[1]
    assert [int(n) for n in re.findall(r"(?:^|; )(\d) ", layout)] == list(titles)
    details_at = next(n for n, t in titles.items() if t.startswith("CARD CORRESPONDENCES"))
    assert f"Each card's correspondences are in section {details_at}," in lean
    for n in re.findall(r"\bsection (\d)\b", lean):
        assert int(n) in titles


def test_full_layout_is_the_default():
    assert LAYOUTS == ("full", "lean")
    assert prompt("12") == prompt("12", layout="full")
    with pytest.raises(ValueError, match="Unknown layout"):
        build_analytical_prompt("x", "", "", "1", [], {}, [], [], {}, {}, layout="short")


def test_book_t_operations_are_grouped_under_their_place():
    lean = prompt(BOOK_T_KEY, layout="lean")
    assert "**Operation 2: The 3rd house**\n- Pos 21, the Significator: Queen of Cups\n" in lean
    assert "- Pos 22, 1 to the right of the Significator: 4 of Cups - Luxury\n" in lean
    assert "### Queen of Cups (Pos 1, 21, 28, 35, 72)\n" in lean
    order = [t for t in re.findall(r"^## \d+\. (.+)$", lean, re.M)]
    assert order.index("PAIRWISE ELEMENTAL DIGNITY INTERACTIONS") < order.index("CARD CORRESPONDENCES, ONCE PER CARD")


def test_wheel_positions_keep_their_full_names():
    lean = prompt("12", layout="lean")
    assert "- Pos 16, 1. First House (Ascendant / Physical Self): 8 of Swords - Interference\n" in lean
    assert "- Pos 40, Decan 1: Saturn in Leo (5 of Wands): " in lean


def test_book_t_timing_names_the_last_small_card_on_the_closing_count():
    rule = "Here that is Pos 77 (3 of Cups - Abundance), the last small card on its Count: the Sun is in its decan 2 Jul - 12 Jul 2027 (UTC)."
    assert rule in prompt(BOOK_T_KEY, layout="lean")
    assert rule in prompt(BOOK_T_KEY, timing_rule=True)
    assert "Book T times the matter" not in prompt(BOOK_T_KEY)               # off unless asked
    assert "Book T times the matter" not in prompt(BOOK_T_KEY, layout="lean", drawn_at=None)
    assert "Book T times the matter" not in prompt(BOOK_T_KEY, layout="lean",
                                                   without=frozenset({"timing", "geomancy", "solids", "cube",
                                                                      "all_aspects", "statistics", "gods",
                                                                      "hexagrams"}))


def test_book_t_timing_falls_back_to_the_last_small_card_listed():
    lean = prompt(BOOK_T_KEY, layout="lean", seed="100001")
    assert "its Count has no small card, so the last small card listed in it" in lean


def test_lean_dates_only_for_cards_on_the_counts():
    lean, full = prompt(BOOK_T_KEY, layout="lean"), prompt(BOOK_T_KEY)
    dates = lambda text: re.search(r"^\*\*Decan Dates\*\* .*$", text, re.M)[0]
    assert "each small card on the Counts" in dates(lean)
    assert "2 of Swords:" in dates(full) and "2 of Swords:" not in dates(lean)    # in a pair only
    assert "3 of Cups: 2 Jul - 12 Jul 2027" in dates(lean)                        # the timing card
    assert dates(lean).count(":") < dates(full).count(":")

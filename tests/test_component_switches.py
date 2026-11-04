"""Leaving Thoth components out of the prompt (report.COMPONENTS, `ootk --without`): each switch
takes out its own part and nothing else, the cards drawn never change, and with every switch
on the prompt is exactly the one the snapshots hold."""
import re
import sys
from datetime import datetime, timezone

import pytest

from ootk import cli
from ootk.report import COMPONENTS, components_off_markdown, reading_time_markdown, without_components
from ootk.spreads import BOOK_T_KEY, ZODIAC_SIGNS

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from test_prompt_snapshots import build_book_t_prompt, build_prompt  # noqa: E402

# Hexagram-free Tree of Life (7), a full wheel with the Own-Place Check (10), the four-operation
# pipeline (12) and Book T (13) between them use every part the switches touch.
SPREADS = ("7", "10", "12", BOOK_T_KEY)
PLANETS = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")


def prompt(spread_key, *off):
    without = frozenset(off)
    return build_book_t_prompt(without) if spread_key == BOOK_T_KEY else build_prompt(spread_key, without=without)


def lines(text, label):
    return [line for line in text.splitlines() if line.startswith(f"- **{label}**")]


def cards_drawn(text):
    return lines(text, "Card Drawn")


def test_parse_component_list():
    assert without_components(None) == frozenset()
    assert without_components(" Astrology, geometry ") == {"astrology", "geometry"}
    assert without_components("hebrew tree") == {"hebrew", "tree"}
    with pytest.raises(ValueError, match="Use any of"):
        without_components("astrology,tarot")


@pytest.mark.parametrize("spread_key", SPREADS)
def test_all_on_is_the_usual_prompt(spread_key):
    assert prompt(spread_key) == (build_book_t_prompt() if spread_key == BOOK_T_KEY else build_prompt(spread_key))
    assert "Components Left Out" not in prompt(spread_key)


@pytest.mark.parametrize("spread_key", SPREADS)
@pytest.mark.parametrize("key", list(COMPONENTS) + ["all"])
def test_switch_keeps_cards_sections_and_end_marker(spread_key, key):
    off = tuple(COMPONENTS) if key == "all" else (key,)
    full, cut = prompt(spread_key), prompt(spread_key, *off)
    assert cards_drawn(cut) == cards_drawn(full)
    assert [h for h in cut.splitlines() if h.startswith("## ")] == [h for h in full.splitlines() if h.startswith("## ")]
    assert cut.rstrip().endswith(full.rstrip().splitlines()[-1])
    assert components_off_markdown(frozenset(off)) in cut
    assert cut != full


@pytest.mark.parametrize("spread_key", SPREADS)
def test_elements_off(spread_key):
    text = prompt(spread_key, "elements")
    assert "Score:" not in text and "█" not in text and "| cards:" not in text
    assert not lines(text, "Element (used in scores)")
    assert "Withheld by element" not in text


@pytest.mark.parametrize("spread_key", SPREADS)
def test_astrology_off(spread_key):
    text = prompt(spread_key, "astrology")
    signs = "|".join(ZODIAC_SIGNS)
    for line in lines(text, "Attribution") + lines(text, "Geomantic Figure") + lines(text, "Element (used in scores)"):
        assert not re.search(rf"\b({signs}|{'|'.join(PLANETS)})\b|°", line), line
    assert "Letter via Sign" not in text and "Own-Place Check" not in text


def test_astrology_off_drops_sun_and_moon():
    when = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
    assert "Sun and Moon" in reading_time_markdown(when)
    assert reading_time_markdown(when, sky=False) == reading_time_markdown(when).splitlines(keepends=True)[0]


@pytest.mark.parametrize("spread_key", SPREADS)
def test_hebrew_off(spread_key):
    text = prompt(spread_key, "hebrew")
    assert not re.search("[א-ת]", text)
    assert "Comparative Hebrew Mapping" not in text and "Letter via" not in text
    assert "Mother Axes" not in text


@pytest.mark.parametrize("spread_key", SPREADS)
def test_tree_off(spread_key):
    text = prompt(spread_key, "tree")
    assert "Path/Sephira" not in text and "King Scale Color" not in text
    assert "Liber 777 Rows" not in text and "Intelligence" not in text
    assert "Framework Basis" not in text and "Sephira (both systems)" not in text
    if spread_key != BOOK_T_KEY:      # the Majors keep their letter
        assert lines(text, "Hebrew Letter")


@pytest.mark.parametrize("spread_key", SPREADS)
def test_courts_off(spread_key):
    text = prompt(spread_key, "courts")
    for line in lines(text, "Attribution"):
        assert not re.search(r"(Fire|Water|Air|Earth) of (Fire|Water|Air|Earth)", line), line


@pytest.mark.parametrize("spread_key", SPREADS)
def test_numerology_geomancy_geometry_off(spread_key):
    assert "Book T Counts" not in prompt(spread_key, "numerology")
    assert "Geomantic Figure" not in prompt(spread_key, "geomancy")
    text = prompt(spread_key, "geometry")
    for gone in ("Platonic Solid", "Platonic Topology", "Spatial Dimension", "Modifier", "Faces"):
        assert f"**{gone}" not in text and f"`{gone}" not in text
    assert "Cube of Space letters" not in text


def test_book_t_keeps_count_and_pairs_without_scores():
    text = prompt(BOOK_T_KEY, "elements")
    assert "**Count**" in text and "**Pairs:**" in text and "Score:" not in text


def test_cli_rejects_unknown_component(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["ootk", "--spread", "3", "--without", "runes"])
    with pytest.raises(cli.CliError, match="runes"):
        cli.run_spread_session()


@pytest.mark.parametrize("spread_key", SPREADS)
def test_gematria_totals_and_switch(spread_key):
    assert "Letter Values (standard gematria" in prompt(spread_key)
    for off in ("gematria", "hebrew"):
        assert "Letter Values (standard gematria" not in prompt(spread_key, off)


def test_gematria_values():
    from ootk import gematria
    assert gematria.letter_value("ס (Samekh)") == 60
    assert gematria.letter_value("Tav (ת)") == 400
    assert gematria.letter_value("Aleph") is None
    assert sum(gematria.STANDARD_VALUES.values()) == 1495
    assert gematria.card_value({"arcana_type": "Minor", "hebrew_letter": "כֶּתֶר (Kether)"}) is None
    assert gematria.card_value({"arcana_type": "Court", "hebrew_letter": "ה (Hé)"}) == 5
    cards = [{"position_number": n, "position_name": name, "card_data": data} for n, name, data in (
        (1, "[Op 1] One", {"arcana_type": "Major", "hebrew_letter": "א (Aleph)"}),
        (2, "[Op 1] Two", {"arcana_type": "Minor", "hebrew_letter": "כֶּתֶר (Kether)"}),
        (3, "[Op 2] One", {"arcana_type": "Major", "hebrew_letter": "ת (Tau)"}),
        (4, "[Op 2] Two", {"arcana_type": "Court", "hebrew_letter": "ש (Shin)"}))]
    assert [(op, total) for op, _, total in gematria.operation_totals(cards)] == [(1, 1), (2, 700)]

"""Leaving Thoth components out of the prompt (report.COMPONENTS, `ootk --without`): each switch
takes out its own part and nothing else, the cards drawn never change, and with every switch
on the prompt is exactly the one the snapshots hold."""
import re
import sys
from datetime import datetime, timezone

import pytest

from ootk import cli
from ootk.report import (COMPONENTS, DEFAULT_OFF, choose_components, cli_switches, component_keys,
                         components_off_markdown, reading_time_markdown)
from ootk.spreads import BOOK_T_KEY, ZODIAC_SIGNS

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from test_prompt_snapshots import build_book_t_prompt, build_prompt  # noqa: E402

# Hexagram-free Tree of Life (7), a full wheel with the Own-Place Check (10), the four-operation
# pipeline (12) and Book T (13) between them use every part the switches touch.
SPREADS = ("7", "10", "12", BOOK_T_KEY)
PLANETS = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")


def prompt(spread_key, *off):
    """The prompt with every layer on (extra layers included) except `off`."""
    without = frozenset(off)
    return build_book_t_prompt(without) if spread_key == BOOK_T_KEY else build_prompt(spread_key, without=without)


def lines(text, label):
    return [line for line in text.splitlines() if line.startswith(f"- **{label}**")]


def cards_drawn(text):
    return lines(text, "Card Drawn")


def headings(text):
    return [h.split(". ", 1)[1] for h in text.splitlines() if h.startswith("## ")]


def test_parse_component_list():
    assert component_keys(None) == frozenset()
    assert component_keys("all") == set(COMPONENTS)
    assert component_keys(" Astrology, geometry ") == {"astrology", "geometry"}
    assert component_keys("hebrew tree") == {"hebrew", "tree"}
    with pytest.raises(ValueError, match="Use any of"):
        component_keys("astrology,tarot")
    # Older links: removed parts are ignored, a renamed one maps to its new key.
    assert component_keys("gematria, hebrew_compare, tree") == {"tree"}
    assert component_keys("cube_counts") == {"cube"}


def test_defaults_round_trip_through_links_and_the_command_line():
    assert cli_switches(DEFAULT_OFF) == ("", "")
    assert choose_components() == DEFAULT_OFF                  # no choice made: the defaults
    assert choose_components("solids", "astrology") == (DEFAULT_OFF - {"solids"}) | {"astrology"}
    assert choose_components("all") == frozenset()
    off = (DEFAULT_OFF - {"cube"}) | {"tree"}
    assert cli_switches(off) == ("cube", "tree")
    assert choose_components(*cli_switches(off)) == off


@pytest.mark.parametrize("spread_key", SPREADS)
def test_all_on_is_the_usual_prompt(spread_key):
    assert "Components Left Out" not in prompt(spread_key)
    usual = build_book_t_prompt() if spread_key == BOOK_T_KEY else build_prompt(spread_key)
    assert "Components Left Out" not in usual                 # the extra layers are not named
    assert len(usual) < len(prompt(spread_key))


@pytest.mark.parametrize("spread_key", SPREADS)
@pytest.mark.parametrize("key", list(COMPONENTS) + ["all"])
def test_switch_keeps_cards_sections_and_end_marker(spread_key, key):
    off = tuple(COMPONENTS) if key == "all" else (key,)
    full, cut = prompt(spread_key), prompt(spread_key, *off)
    assert cards_drawn(cut) == cards_drawn(full)
    assert set(headings(cut)) <= set(headings(full))     # sections 3 and 4 go when left empty
    assert headings(cut)[-1] == headings(full)[-1]
    assert cut.rstrip().endswith(full.rstrip().splitlines()[-1])
    assert components_off_markdown(frozenset(off)) in cut
    # An extra layer is not named in the header, so a reading without it is unchanged.
    assert cut != full or key in DEFAULT_OFF


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
    assert "Modifier" not in text and "_Opposition (180" not in text
    text = prompt(spread_key, "cube")
    assert "**Spatial Dimension" not in text and "Mother axes" not in text
    assert "Cube of Space" not in text
    text = prompt(spread_key, "solids")
    for gone in ("Platonic Solid", "Platonic Topology", "Faces"):
        assert f"**{gone}" not in text and f"`{gone}" not in text


def test_book_t_keeps_count_and_pairs_without_scores():
    text = prompt(BOOK_T_KEY, "elements")
    assert "**Count**" in text and "**Pairs:**" in text and "Score:" not in text


def test_cli_rejects_unknown_component(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["ootk", "--spread", "3", "--without", "runes"])
    with pytest.raises(cli.CliError, match="runes"):
        cli.run_spread_session()


@pytest.mark.parametrize("spread_key", SPREADS)
def test_removed_layers_never_reach_the_prompt(spread_key):
    """Gematria sums, the French/Egyptian comparison column, birth cards and the dual-solid
    pairings were let go: not even every layer switched on brings them back."""
    text = prompt(spread_key)
    for gone in ("Letter Values", "gematria", "French/Egyptian: `", "Birth Cards", "duals",
                 "Dual:", "polyhedral inversion"):
        assert gone not in text, gone


def test_plain_summary_on_top_and_no_empty_geometry_section():
    """The prompt opens with a plain summary and a guide to its sections; Opening of the Key has
    no layout, so with every layer on it still has no geometry section; the extra totals are
    one line each."""
    full = prompt(BOOK_T_KEY)
    top = full.split("**Operation/Spread:**", 1)[0]
    assert "**In Plain Words:** 79 cards were drawn, in 5 operations" in top
    assert "The Significator, Queen of Cups, stands for the querent." in top
    layout = next(line for line in top.splitlines() if line.startswith("**How This Prompt Is Laid Out:**"))
    assert layout.count(";") == len(headings(full)) - 1          # one entry per section kept
    assert "SPATIAL & GEOMETRIC VECTOR ANALYSIS" not in headings(full)
    assert "No spatial layout" not in full
    assert "Solid properties" not in full and "Topological Dual Pairings" not in full
    assert "SPATIAL & GEOMETRIC VECTOR ANALYSIS" in headings(prompt("10"))   # a wheel keeps it

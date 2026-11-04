"""Birth and year cards (Greer and Arrien tarot numerology), and their prompt line."""
import json
import os
import re
from datetime import date

import pytest

from ootk.birth_cards import (MAJOR_NAMES, ROMAN, birth_cards_markdown, birth_cards_param, card_title,
                              constellation, latest_birthday_year, parse_birth_cards, personality_number,
                              reduce_to_card, year_number)
from ootk.report import analyze_reading

HERE = os.path.dirname(__file__)
ROOT = os.path.dirname(HERE)


def test_greer_worked_examples():
    # 14 July 1983: 7 + 14 + 1983 = 2004, 2 + 0 + 0 + 4 = 6, The Lovers.
    assert personality_number(date(1983, 7, 14)) == 6
    # 25 December 1990: 12 + 25 + 1990 = 2027 -> 11, Lust.
    assert personality_number(date(1990, 12, 25)) == 11
    # 3 March 1979: 3 + 3 + 1979 = 1985 -> 23 -> 5, the Hierophant (over 22 reduces again).
    assert personality_number(date(1979, 3, 3)) == 5
    assert reduce_to_card(22) == 22 and reduce_to_card(1999) == 10 and reduce_to_card(2029) == 13


def test_constellations():
    assert constellation(19) == [19, 10, 1]
    assert constellation(22) == [22, 4]          # The Fool, then the Emperor
    assert constellation(6) == [6]
    assert constellation(13) == [13, 4]


def test_year_card_runs_from_the_latest_birthday():
    birth = date(1983, 7, 14)
    assert latest_birthday_year(birth, date(2026, 7, 13)) == 2025
    assert latest_birthday_year(birth, date(2026, 7, 14)) == 2026
    assert latest_birthday_year(date(2000, 2, 29), date(2026, 2, 28)) == 2025
    assert latest_birthday_year(date(2000, 2, 29), date(2026, 3, 1)) == 2026
    assert year_number(birth, 2026) == 13       # 7 + 14 + 2026 = 2047 -> 13, Death
    assert birth_cards_param(birth, date(2026, 11, 4)) == "6-13-2026"


@pytest.mark.parametrize("bad", ["0-5-2026", "23-5-2026", "6-13", "6-13-26", "a-b-c", "6-13-2026x", "1983-07-14"])
def test_bad_params_are_refused(bad):
    with pytest.raises(ValueError):
        parse_birth_cards(bad)


def test_blank_param_means_none():
    assert parse_birth_cards("") is None and parse_birth_cards(None) is None
    assert birth_cards_markdown("", []) == ""


def test_titles_match_the_deck():
    with open(os.path.join(HERE, "fixtures", "reference_cards.json"), encoding="utf-8") as f:
        rows = json.load(f)["rows"]
    majors = {t for t, c in rows.items() if c["arcana_type"] == "Major"}
    assert {card_title(n) for n in range(1, 23)} == majors
    assert card_title(22) == "0 - The Fool" and card_title(8) == "VIII - Adjustment"


def test_browser_copy_of_the_names_matches():
    with open(os.path.join(ROOT, "static", "js", "index.js"), encoding="utf-8") as f:
        js = f.read()
    names = re.search(r"const ATU = \[(.*?)\];", js, re.S).group(1)
    assert re.findall(r'"([^"]+)"', names) == MAJOR_NAMES
    assert len(ROMAN) == len(MAJOR_NAMES) == 22


def _item(n, title):
    return {"position_number": n, "position_name": f"P{n}",
            "card_data": {"title": title, "arcana_type": "Major", "suit": None, "attribution": "Sun",
                          "king_scale_color": "Orange"}}


def test_prompt_line_names_the_cards_and_any_drawn():
    line = birth_cards_markdown("19-7-2026", [_item(1, "XIX - The Sun"), _item(2, "XVII - The Star")])
    assert "personality XIX - The Sun (reduces to X - Fortune, then I - The Magus)" in line
    assert "year card for the year from the birthday in 2026: VII - The Chariot" in line
    assert "Drawn in this reading: XIX - The Sun (Position 1)." in line
    assert "None of them was drawn." in birth_cards_markdown("6-13-2026", [_item(1, "XIX - The Sun")])
    assert "0 - The Fool (reduces to IV - The Emperor)" in birth_cards_markdown("22-1-2026", [])


def _prompt(**kw):
    with open(os.path.join(HERE, "fixtures", "reference_cards.json"), encoding="utf-8") as f:
        sun = json.load(f)["rows"]["XIX - The Sun"]
    item = {"position_number": 1, "position_name": "P1", "card_data": sun}
    return analyze_reading("Single Card", "1", "q", "None", "1", [item], **kw)["analytical_prompt"]


def test_header_line_and_numerology_switch():
    assert "**Birth Cards**" in _prompt(birth_cards="19-7-2026")
    assert "**Birth Cards**" not in _prompt(birth_cards="19-7-2026", without=frozenset({"numerology"}))
    assert "**Birth Cards**" not in _prompt()

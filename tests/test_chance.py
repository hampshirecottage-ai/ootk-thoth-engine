"""The "How unusual is this?" box: chance.json and the comparisons built from it."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ootk import chance, web
from ootk.spreads import BOOK_T_KEY, SPREADS

REFERENCE = json.loads((Path(__file__).parent / "fixtures" / "reference_cards.json").read_text())


@pytest.fixture
def tables(monkeypatch):
    cache = {"deck": REFERENCE["deck"]}
    cache.update({s: REFERENCE["rows"] for s in ("thoth", "golden_dawn", "french_egyptian")})
    monkeypatch.setattr(web, "_reference_cache", cache)


def test_table_covers_every_spread():
    table = chance.chance_table()
    assert set(table) == {*SPREADS, BOOK_T_KEY}
    for entry in table.values():
        assert entry["_draws"] == chance.CHANCE_DRAWS
        assert all(sum(entry[k].values()) in (0, chance.CHANCE_DRAWS) for k in chance.MEASURES)


def test_table_is_up_to_date(tables):
    # The table is seeded, so a rule change that moves these numbers shows here: rerun
    # scripts/make_chance_table.py.
    assert chance.simulate("4") == chance.chance_table()["4"]


def _hist(values):
    out = {}
    for v in values:
        out[str(v)] = out.get(str(v), 0) + 1
    return out


def test_only_the_far_tail_is_unusual():
    draws = 100
    table = {"leader": _hist([3] * 50 + [4] * 46 + [5] * 4), "_draws": draws}
    rows = chance.rows_for({"leader": 5}, table, 0, 0, None, draws)
    assert rows[0]["unusual"] and rows[0]["verdict"] == "unusually high"
    assert rows[0]["odds"] == "about 1 in 25 random shuffles go this far"
    assert rows[0]["usual"] == "up to 4"
    usual = chance.rows_for({"leader": 4}, table, 0, 0, None, draws)[0]
    assert not usual["unusual"] and usual["verdict"] == "usual"


def test_a_number_every_shuffle_gives_is_left_out():
    table = {"kinds": _hist([0] * 99 + [1]), "_draws": 100}
    assert chance.rows_for({"kinds": 0}, table, 0, 0, None, 100) == []


def test_one_contrary_pair_on_a_short_spread_is_usual():
    rows = chance.rows_for({}, {"_draws": 1}, 1, -2, None, 1)
    assert rows[0]["key"] == "dignity" and not rows[0]["unusual"]


def _book_t_reading():
    deck = web.reference_deck()
    titles, label = web.seeded_draw(deck, "408850", BOOK_T_KEY, "Queen of Cups", "1,10/6,10,6")
    settings = {"spread_key": BOOK_T_KEY, "topic": "", "significator": "Queen of Cups",
                "framework": "auto", "mapping_system": "thoth", "draw_mode": "seed",
                "seed": "408850", "selected_cards": "", "drawn_at": "", "expect": "1,10/6,10,6",
                "with": "", "without": ""}
    return web.run_reading(settings, titles, label, deck)


def test_switching_a_part_off_drops_its_numbers(tables):
    r = _book_t_reading()
    args = (BOOK_T_KEY, r["spread_results"], r["dignity_matrix"], r["framework_basis"], r["own_place"])
    keys = {row["key"] for row in chance.chance_view(*args)["rows"]}
    assert {"dignity", "leader", "ill", "majors", "lens"} <= keys
    off = {row["key"] for row in chance.chance_view(*args, off={"elements", "tree"})["rows"]}
    assert off == keys - {"dignity", "leader", "weakest", "ill", "lens"}


def test_prompt_says_what_stands_out_and_how_often_chance_does(tables):
    r = _book_t_reading()
    line = next(l for l in r["analytical_prompt"].splitlines() if l.startswith("**Against Chance:**"))
    assert "trumps, 27, unusually high (about 1 in 26 random shuffles go this far)" in line
    assert "at least one unusual number 31% of the time" in line


def test_nothing_unusual_says_read_as_ordinary():
    view = {"rows": [{"label": "Trumps", "unusual": False}], "unusual": [], "any_rate": 0.1}
    assert chance.chance_sentence(view) == ("Compared with random shuffles of this spread, none of the "
                                            "1 numbers checked (trumps) is unusual, so read them as "
                                            "ordinary for this spread.")


def test_report_shows_the_box(tables):
    page = TestClient(web.app).get("/reading?seed=408850&spread=13&significator=Queen+of+Cups"
                                   "&expect=1,10/6,10,6&drawn=20261111T1800Z")
    assert page.status_code == 200
    assert 'id="howUnusual"' in page.text and "1 of 7 numbers stands out from chance" in page.text
    assert "31% of random shuffles show at least one unusual one" in page.text


def test_one_card_has_no_box(tables):
    page = TestClient(web.app).get("/reading?seed=5&spread=1&drawn=20261111T1800Z")
    assert page.status_code == 200 and 'id="howUnusual"' not in page.text

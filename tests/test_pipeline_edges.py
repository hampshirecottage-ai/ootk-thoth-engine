"""Edge cases of the reading pipeline (engine and CLI), no database or web app needed."""
import sys
from contextlib import nullcontext

import pytest

from ootk import analysis, cli, shuffle, spreads


def card(i, title=None, arcana="Minor", solid="Tetrahedron"):
    return {"card_id": i, "title": title or f"Card {i}", "arcana_type": arcana, "suit": "Wands",
            "attribution": "Fire", "platonic_solid": solid, "key_scale": 2,
            "path_or_sephira": "Chokmah", "hebrew_letter": "Chokmah", "element": "Fire",
            "king_scale_color": "Blue", "spatial_type": None, "spatial_dimension": None}


# ---------- dual pairings stay inside an operation ----------

def test_dual_pairings_never_cross_an_operation_boundary():
    positions = spreads.spread_positions("12")
    results = [{"position_number": i + 1, "position_name": p, "card_data": card(i)}
               for i, p in enumerate(positions)]
    _, _, duals = analysis.analyze_platonic_topology(results, "12")
    pairs = {d.split(":")[0] for d in duals}
    for last in (15, 27, 39):                    # the last card of operations 1, 2 and 3
        assert f"Positions {last} & {last + 1}" not in pairs
    assert len(duals) == 8 + 12 + 12 + 36        # the dignities' pairs: heap pairs, closed wheels
    # A single spread is one segment, as before.
    _, _, duals = analysis.analyze_platonic_topology(results[:3], "3")
    assert len(duals) == 2


# ---------- drawing from a short deck ----------

def test_draw_refuses_a_deck_too_small_for_the_spread():
    with pytest.raises(ValueError, match="needs 3"):
        shuffle.draw_spread([], "1", spreads.spread_positions("3"))
    deck = [card(i) for i in range(5)]
    with pytest.raises(ValueError, match="needs 12"):           # used to deal cards twice
        shuffle.draw_spread(deck, "1", spreads.spread_positions("9"))
    with pytest.raises(ValueError):                              # only the significator left
        shuffle.draw_spread(deck[:1], "1", spreads.spread_positions("8"), deck[0])
    titles, _ = shuffle.draw_spread(deck, "1", spreads.spread_positions("5"))
    assert len(set(titles)) == 4


# ---------- significator names ----------

DECK = [card(0, "XI - Lust", "Major"), card(1, "2 of Wands - Dominion"),
        card(2, "Queen of Cups", "Court")]


@pytest.mark.parametrize("name,title", [
    ("XI - Lust", "XI - Lust"), ("lust", "XI - Lust"), ("Queen of Cups", "Queen of Cups"),
    ("2 of Wands", "2 of Wands - Dominion"), ("dominion", "2 of Wands - Dominion"),
    (" 2 OF WANDS ", "2 of Wands - Dominion"),
])
def test_significator_found_by_any_of_its_names(name, title):
    assert shuffle.resolve_significator(DECK, name)["title"] == title


@pytest.mark.parametrize("name", ["XI", "", "Queen", "2 of Cups"])
def test_significator_not_found(name):
    assert shuffle.resolve_significator(DECK, name) is None


# ---------- CLI ----------

CLI_DECK = [card(i) for i in range(78)]


@pytest.fixture
def run_cli(monkeypatch, capsys):
    saved = {}
    monkeypatch.setattr(cli, "get_db_connection", lambda: nullcontext(object()))
    monkeypatch.setattr(cli, "fetch_all_cards", lambda conn: CLI_DECK)
    monkeypatch.setattr(cli, "load_cards_data", lambda conn, titles, system: [
        next(c for c in CLI_DECK if c["title"] == t) for t in titles])
    monkeypatch.setattr(cli, "load_withheld", lambda *a: None)

    def save(conn, name, topic, notes, sig, results, dignity):
        saved["titles"] = [r["card_data"]["title"] for r in results]
        return 1
    monkeypatch.setattr(cli, "save_spread_session", save)

    def run(argv, answers=()):
        answers = iter(answers)

        def fake_input(prompt=""):
            try:
                return next(answers)
            except StopIteration:
                raise EOFError from None
        monkeypatch.setattr("builtins.input", fake_input)
        monkeypatch.setattr(sys, "argv", ["ootk", *argv])
        code = 0
        try:
            cli.main()
        except SystemExit as e:
            code = e.code
        out = capsys.readouterr()
        return code, out.out, out.err, saved
    return run


def test_cli_manual_entry_refuses_a_card_already_drawn(run_cli):
    code, out, _, saved = run_cli(["--spread", "3", "--topic", "t"], ["", "1", "1", "2", "2", "3"])
    assert code == 0
    assert saved["titles"] == ["Card 0", "Card 1", "Card 2"]
    assert out.count("already at position") == 2


def test_cli_unknown_spread_is_an_error_not_a_menu(run_cli):
    code, out, err, saved = run_cli(["--spread", "99", "--seed", "1", "--topic", "t"])
    assert code == 1 and "Unknown spread '99'" in err and not saved


def test_cli_closed_input_ends_cleanly(run_cli):
    code, _, err, saved = run_cli(["--spread", "8", "--seed", "1", "--topic", "t"])
    assert code == 1 and "Input ended" in err and "--significator" in err and not saved


def test_cli_seed_is_stripped_like_the_web_form(run_cli):
    _, _, _, saved = run_cli(["--spread", "3", "--seed", " 42 ", "--topic", "t"])
    expected, _ = shuffle.draw_spread(CLI_DECK, "42", spreads.spread_positions("3"))
    assert saved["titles"] == expected


def test_cli_short_deck_is_an_error(run_cli, monkeypatch):
    monkeypatch.setattr(cli, "fetch_all_cards", lambda conn: CLI_DECK[:5])
    code, _, err, saved = run_cli(["--spread", "9", "--seed", "1", "--topic", "t"])
    assert code == 1 and "needs 12" in err and not saved

"""The whole AI prompt for a fixed draw of several spreads, compared with a saved copy.

Any change to the prompt's wording or layout shows up here as a readable diff of
tests/prompt_snapshots/. The card rows come from tests/fixtures/reference_cards.json (a copy
of the database, checked against it in test_db_integration), so no database is needed.
After an intended change, rewrite the copies with:
    OOTK_UPDATE_SNAPSHOTS=1 python -m pytest tests/test_prompt_snapshots.py
"""
import copy
import json
import os

import pytest

from ootk import book_t
from ootk.analysis import withheld_summary
from ootk.report import analyze_reading
from ootk.shuffle import draw_spread, has_significator_position, resolve_significator, significator_places
from ootk.spreads import BOOK_T_KEY, BOOK_T_OP_NAMES, BOOK_T_SPREAD, SPREADS, spread_positions

HERE = os.path.dirname(__file__)
SEED = "408850"
TOPIC = "Should I change jobs this year?"
SIGNIFICATOR = "Queen of Cups"
# One of each kind of layout: single card, line, hexagram (with a centre), Tree of Life,
# Op 1 heap, a full wheel (Own-Place Check) and the four-operation master pipeline.
SPREAD_KEYS = ("1", "3", "6", "7", "8", "10", "12")

with open(os.path.join(HERE, "fixtures", "reference_cards.json"), encoding="utf-8") as f:
    REFERENCE = json.load(f)


def build_prompt(spread_key, mapping_system="thoth"):
    """The same steps as cli.run_spread_session, from the saved card rows."""
    deck = REFERENCE["deck"]
    positions = spread_positions(spread_key)
    sig_card = resolve_significator(deck, SIGNIFICATOR)
    titles, pinned = draw_spread(deck, SEED, positions, sig_card)
    spread_results = [
        {"position_number": i, "position_name": name, "card_data": copy.deepcopy(REFERENCE["rows"][title])}
        for i, (name, title) in enumerate(zip(positions, titles), start=1)
    ]
    withheld = withheld_summary([REFERENCE["rows"][c["title"]] for c in deck], titles)
    significator = sig_card["title"] if pinned else "None (spread has no significator position)"
    reading = analyze_reading(SPREADS[spread_key]["name"], spread_key, TOPIC, significator, SEED,
                              spread_results, withheld=withheld, mapping_system=mapping_system,
                              significator_places=significator_places(deck, SEED, positions, sig_card))
    return reading["analytical_prompt"]


# Book T (spread 13): expected in the Yod pack (work), the 10th house or else the 6th,
# Capricorn, and Tiphareth. With this seed the first three operations miss, which is the
# common case and exercises the "Book T would abandon here" wording.
BOOK_T_EXPECT = "1,10/6,10,6"


def build_book_t_prompt():
    """The same steps as cli.run_book_t_session, from the saved card rows."""
    deck = REFERENCE["deck"]
    sig_card = resolve_significator(deck, SIGNIFICATOR)
    ops = book_t.opening_of_the_key(deck, SEED, sig_card, book_t.parse_expect(BOOK_T_EXPECT))
    placed = book_t.positions(ops)
    titles = [c["title"] for _, c in placed]
    spread_results = [
        {"position_number": i, "position_name": name, "card_data": copy.deepcopy(REFERENCE["rows"][c["title"]])}
        for i, (name, c) in enumerate(placed, start=1)
    ]
    withheld = withheld_summary([REFERENCE["rows"][c["title"]] for c in deck], titles)
    reading = analyze_reading(BOOK_T_SPREAD["name"], BOOK_T_KEY, TOPIC, sig_card["title"], SEED,
                              spread_results, withheld=withheld, book_t_ops=ops)
    return reading["analytical_prompt"]


def test_fixture_covers_the_whole_deck():
    assert len(REFERENCE["deck"]) == 78
    assert {c["title"] for c in REFERENCE["deck"]} == set(REFERENCE["rows"])
    assert has_significator_position(spread_positions("8"))


@pytest.mark.parametrize("spread_key", SPREAD_KEYS + (BOOK_T_KEY,))
def test_prompt_matches_saved_copy(spread_key):
    prompt = build_book_t_prompt() if spread_key == BOOK_T_KEY else build_prompt(spread_key)
    path = os.path.join(HERE, "prompt_snapshots", f"spread_{spread_key}.md")
    if os.getenv("OOTK_UPDATE_SNAPSHOTS") == "1":
        with open(path, "w", encoding="utf-8") as f:
            f.write(prompt)
    with open(path, encoding="utf-8") as f:
        saved = f.read()
    assert prompt == saved, (f"The prompt for spread {spread_key} changed. If that was intended, "
                             f"rewrite the copy with OOTK_UPDATE_SNAPSHOTS=1 and check the diff.")


def test_french_prompt_explains_its_path_numbers():
    """Under French/Egyptian the Star carries Peh and Path 27; without a note an AI that knows
    the Golden Dawn Tree reads that as a mix-up (Peh is the Tower's letter there)."""
    french = build_prompt("12", "french_egyptian")
    assert "**Mapping Note:**" in french
    assert "The Star (XVII) is Peh on Path 27" in french
    assert "**Mapping Note:**" not in build_prompt("12", "golden_dawn")


def test_thoth_prompt_explains_the_swapped_cards_edges():
    """Under Thoth the Star carries Heh but sits on Aquarius's Upper-South edge; without a note
    an AI that knows Paul Case's cube reads that as a mix-up (Heh is the North-East edge)."""
    thoth = build_prompt("12")
    assert "**Mapping Note:** Crowley swapped the letters Tzaddi and Heh, not the signs" in thoth
    assert "Cube of Space edge follow the sign" in thoth


def test_planetary_majors_say_which_sign_gives_their_element():
    """Venus rules Taurus (Earth) and Libra (Air); without a note an AI that reads Venus by Libra
    takes the Empress's Earth scores as a mistake."""
    from ootk.analysis import PLANETARY_ELEMENT_NOTES, PLANETARY_MAJORS, major_element_note
    assert set(PLANETARY_ELEMENT_NOTES) == PLANETARY_MAJORS
    empress = {"arcana_type": "Major", "title": "III - The Empress"}
    assert major_element_note(empress) == "Earth (Venus via Taurus; Libra would make it Air)"
    assert major_element_note({"arcana_type": "Minor", "title": "3 of Swords - Sorrow"}) is None


def test_every_major_states_its_element():
    """An AI saw no element line on the Emperor, Fool, Hermit, Hanged Man and Lovers and had to
    work their elements out from the pair scores, so every Major now says its element."""
    from ootk.analysis import MAJOR_ELEMENT_NOTES, MAJOR_ELEMENTS, ZODIAC_ELEMENTS, SIGN_ELEMENT_NOTES, major_element_note
    assert set(MAJOR_ELEMENT_NOTES) == set(MAJOR_ELEMENTS)
    for name, sign in SIGN_ELEMENT_NOTES.items():
        assert ZODIAC_ELEMENTS[sign.lower()] == MAJOR_ELEMENTS[name]
    for name in MAJOR_ELEMENTS:
        assert major_element_note({"arcana_type": "Major", "title": f"X - {name}"}).startswith(MAJOR_ELEMENTS[name] + " (")
    assert major_element_note({"arcana_type": "Major", "title": "IV - The Emperor"}) == "Fire (via Aries)"
    assert major_element_note({"arcana_type": "Major", "title": "0 - The Fool"}) == "Air (the element Air itself)"
    prompt = build_prompt("12")
    assert prompt.count("- **Element (used in scores)**:") == sum(
        1 for line in prompt.splitlines()
        if line.startswith("- **Card Drawn**:") and line.split(" - ", 1)[-1] in MAJOR_ELEMENTS)


def test_courts_say_they_have_no_french_letter():
    # The French/Egyptian system gives courts no path letter on purpose: the prompt says so
    # once, and the court's mapping line reads "none" rather than a missing-data "N/A".
    prompt = build_prompt("12")
    assert "The French/Egyptian system gives courts no path letter" in prompt
    assert "French/Egyptian: `none`" in prompt
    assert "French/Egyptian: `N/A`" not in prompt


def test_book_t_prompt_counts_and_pairs_each_operation():
    """Every operation read gets its status line, a Count and its Pairs, and the prompt stays
    well under the ~78k characters where Gemini stops reading (see the shorter-prompt work)."""
    prompt = build_book_t_prompt()
    for name in BOOK_T_OP_NAMES.values():
        assert f"**{name}**" in prompt, name
    assert prompt.count("**Count** (towards the left") == 5
    assert prompt.count("**Pairs:**") == 5
    assert "Book T says to abandon the divination here" in prompt
    assert "Counting numbers (Book T)" in prompt
    assert len(prompt) < 70000

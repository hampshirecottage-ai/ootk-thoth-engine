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

from ootk.analysis import withheld_summary
from ootk.report import analyze_reading
from ootk.shuffle import draw_spread, has_significator_position, resolve_significator, significator_places
from ootk.spreads import SPREADS, spread_positions

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


def test_fixture_covers_the_whole_deck():
    assert len(REFERENCE["deck"]) == 78
    assert {c["title"] for c in REFERENCE["deck"]} == set(REFERENCE["rows"])
    assert has_significator_position(spread_positions("8"))


@pytest.mark.parametrize("spread_key", SPREAD_KEYS)
def test_prompt_matches_saved_copy(spread_key):
    prompt = build_prompt(spread_key)
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
    from ootk.analysis import MAJOR_ELEMENTS, PLANETARY_ELEMENT_NOTES, PLANETARY_MAJORS, planetary_element_note
    assert set(PLANETARY_ELEMENT_NOTES) == PLANETARY_MAJORS
    empress = {"arcana_type": "Major", "title": "III - The Empress"}
    assert planetary_element_note(empress) == "Earth (Venus via Taurus; Libra would make it Air)"
    assert planetary_element_note({"arcana_type": "Major", "title": "XI - Lust"}) is None
    assert planetary_element_note({"arcana_type": "Minor", "title": "3 of Swords - Sorrow"}) is None
    for name in PLANETARY_MAJORS:
        assert planetary_element_note({"arcana_type": "Major", "title": f"X - {name}"}).startswith(MAJOR_ELEMENTS[name])
    prompt = build_prompt("12")
    assert prompt.count("- **Element (used in scores)**:") == sum(
        1 for line in prompt.splitlines()
        if line.startswith("- **Card Drawn**:") and line.split(" - ", 1)[-1] in PLANETARY_MAJORS)

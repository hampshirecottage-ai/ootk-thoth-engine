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
from ootk.shuffle import draw_spread, has_significator_position, resolve_significator
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


def build_prompt(spread_key):
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
                              spread_results, withheld=withheld)
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

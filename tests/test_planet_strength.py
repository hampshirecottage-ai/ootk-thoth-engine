"""Planet Strength line: classical essential dignity of a pip's planet in its sign."""
import json
import os

from ootk.report import _cards_md
from ootk.rules import planet_dignities, planet_dignity_note

HERE = os.path.dirname(__file__)


def test_known_cards():
    assert planet_dignity_note("Sun in Aries") == "exalted (strong)"           # 3 of Wands
    assert planet_dignity_note("Mars in Aries") == "rules this sign (strong)"              # 2 of Wands
    assert planet_dignity_note("Venus in Aries") == "in detriment (weakened)"  # 4 of Wands
    assert planet_dignity_note("Jupiter in Capricorn") == "in fall (weakest)"
    assert planet_dignity_note("Mercury in Virgo") == "rules this sign and is exalted (strong)"
    assert planet_dignities("Mercury", "Pisces") == ["detriment", "fall"]


def test_no_line_without_dignity_or_planet():
    assert planet_dignity_note("Saturn in Aquarius") == "rules this sign (strong)"
    assert planet_dignity_note("Moon in Aquarius") is None   # 7 of Swords: neither
    for text in ("Aries", "Root of the Powers of Fire", "Fire of Water - 20° Gemini to 20° Cancer", None, ""):
        assert planet_dignity_note(text) is None


def test_table_is_consistent():
    # Each planet's detriments are the signs opposite its rulerships, and falls opposite exaltations.
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
             "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    planets = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
    for i, sign in enumerate(signs):
        opposite = signs[(i + 6) % 12]
        for planet in planets:
            here, there = planet_dignities(planet, sign), planet_dignities(planet, opposite)
            assert ("ruler" in here) == ("detriment" in there)
            assert ("exalted" in here) == ("fall" in there)


def test_sixteen_of_the_36_decan_cards_carry_the_line():
    with open(os.path.join(HERE, "fixtures", "reference_cards.json"), encoding="utf-8") as f:
        rows = json.load(f)["rows"]
    pips = {t: c["attribution"] for t, c in rows.items()
            if c.get("arcana_type") == "Minor" and " in " in (c.get("attribution") or "")}
    assert len(pips) == 36
    marked = {t for t, a in pips.items() if planet_dignity_note(a)}
    assert len(marked) == 16
    assert "3 of Wands - Virtue" in marked and "7 of Swords - Futility" not in marked


def _item(title, attribution):
    return {"position_number": 1, "position_name": "Test",
            "card_data": {"title": title, "arcana_type": "Minor", "suit": "Wands",
                          "attribution": attribution, "king_scale_color": "Red"}}


def test_prompt_line_and_astrology_switch():
    item = _item("3 of Wands - Virtue", "Sun in Aries")
    md = _cards_md([item], {}, frozenset({"geometry", "tree", "hebrew"}))
    assert "- **Planet Strength**: exalted (strong)" in md
    assert "Planet Strength is the classical" in md
    md = _cards_md([item], {}, frozenset({"geometry", "tree", "hebrew", "astrology"}))
    assert "Planet Strength" not in md
    md = _cards_md([_item("7 of Swords - Futility", "Moon in Aquarius")], {},
                   frozenset({"geometry", "tree", "hebrew"}))
    assert "Planet Strength" not in md

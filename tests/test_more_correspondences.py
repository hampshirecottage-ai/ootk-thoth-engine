"""Golden Dawn titles, decan angels, decan dates and day ruler, and leaving them out to fit."""
import copy
import json
import os
from datetime import datetime, timezone

from ootk import report
from ootk.decans import (ANGELS, _equinox, day_ruler, decan_angels, decan_dates, pip_decan,
                         solar_year)
from ootk.report import FIT_ORDER, PROMPT_BUDGET, analyze_reading
from ootk.titles import COURT_TITLES, TRUMP_TITLES, full_title, short_title

HERE = os.path.dirname(__file__)
with open(os.path.join(HERE, "fixtures", "reference_cards.json"), encoding="utf-8") as f:
    ROWS = json.load(f)["rows"]


# ---------- titles ----------

def test_every_card_but_the_aces_has_a_title():
    missing = [t for t in ROWS if full_title(t) is None]
    assert sorted(missing) == ["Ace of Cups", "Ace of Disks", "Ace of Swords", "Ace of Wands"]
    assert len(TRUMP_TITLES) == 22 and len(COURT_TITLES) == 16


def test_known_titles():
    assert full_title("4 of Swords - Truce") == "Lord of Rest from Strife"
    assert short_title("4 of Swords - Truce") == "Rest from Strife"
    assert short_title("2 of Cups - Love") is None                 # only repeats the card's name
    assert short_title("XVII - The Star") == "The Daughter of the Firmament"
    assert short_title("VIII - Adjustment") == "The Daughter of the Lords of Truth"   # Justice's
    assert short_title("XI - Lust") == "The Daughter of the Flaming Sword"            # Strength's
    assert short_title("Knight of Wands") == "Lord of the Flame and the Lightning"


# ---------- angels and dates ----------

def test_angels_start_at_leo_and_cover_all_72():
    assert len(ANGELS) == len(set(ANGELS)) == 72
    assert decan_angels("5 of Wands - Strife") == ("Vehuiah", "Yeliel")      # 0° Leo
    assert decan_angels("2 of Wands - Dominion") == ("Vehuel", "Daniel")     # 0° Aries
    assert decan_angels("4 of Cups - Luxury") == ("Haiaiel", "Mumiah")       # last before Leo
    pips = [t for t in ROWS if pip_decan(t) is not None]
    assert len(pips) == 36
    assert sorted(n for t in pips for n in decan_angels(t)) == sorted(ANGELS)
    assert decan_angels("Knight of Wands") is None and decan_angels("XIX - The Sun") is None


def test_titles_follow_one_stated_source():
    assert full_title("XI - Lust") == "The Daughter of the Flaming Sword"          # 777, one clause
    assert full_title("V - The Hierophant") == "The Magus of the Eternal"          # 777, not "... Gods"
    assert full_title("XIII - Death").endswith("the Lord of the Gates of Death")
    assert short_title("IV - The Emperor") == "The Son of the Morning"
    assert full_title("Prince of Swords") == "Prince of the Chariot of the Winds"  # Book T list form


def test_decan_dates():
    assert _equinox(2026).date().isoformat() == "2026-03-20"
    assert decan_dates("2 of Wands - Dominion", 2026) == "20 Mar - 30 Mar 2026"
    assert decan_dates("5 of Wands - Strife", 2026).startswith("22 Jul")
    assert decan_dates("2 of Disks - Change", 2026).startswith("21 Dec")
    assert decan_dates("10 of Cups - Satiety", 2026).endswith("20 Mar 2027")
    assert decan_dates("3 of Disks - Works", 2026) == "31 Dec 2026 - 10 Jan 2027"   # spans the new year
    assert solar_year(datetime(2026, 3, 1, tzinfo=timezone.utc)) == 2025
    assert solar_year(datetime(2026, 11, 4, tzinfo=timezone.utc)) == 2026


def test_decan_dates_are_never_before_the_draw():
    from ootk.decans import decan_dates_after, decan_window
    drawn = datetime(2026, 11, 11, 18, tzinfo=timezone.utc)
    assert decan_dates_after("7 of Cups - Debauch", drawn) == "12 Nov - 22 Nov 2026"     # starts the next day
    assert decan_dates_after("6 of Cups - Pleasure", drawn) == decan_dates("6 of Cups - Pleasure", 2026)  # the Sun is in it now
    assert decan_dates_after("2 of Wands - Dominion", drawn) == decan_dates("2 of Wands - Dominion", 2027)  # March 2026 is past
    assert decan_dates_after("3 of Disks - Works", drawn) == "31 Dec 2026 - 10 Jan 2027"
    assert decan_dates_after("Ace of Cups", drawn) is None
    for title in ("2 of Wands - Dominion", "5 of Wands - Strife", "10 of Cups - Satiety", "9 of Disks - Gain"):
        start, end = decan_window(title, drawn)
        assert end >= drawn and (end - start).days < 12


def test_day_ruler():
    assert day_ruler(datetime(2026, 11, 4, 12, tzinfo=timezone.utc)) == ("Wednesday", "Mercury")
    assert day_ruler(datetime(2026, 11, 8, 12, tzinfo=timezone.utc)) == ("Sunday", "Sun")


def test_day_ruler_line_says_utc_when_no_time_zone_was_given():
    from zoneinfo import ZoneInfo
    from ootk.report import day_ruler_markdown
    drawn = datetime(2026, 11, 5, 3, tzinfo=timezone.utc)   # Wednesday evening in Vancouver
    assert "Thursday" in day_ruler_markdown(drawn) and "by UTC" in day_ruler_markdown(drawn)
    assert "own clock" not in day_ruler_markdown(drawn)
    local = day_ruler_markdown(drawn, ZoneInfo("America/Vancouver"))
    assert "Wednesday" in local and "own clock" in local and "UTC" not in local


# ---------- the prompt ----------

def _items(*titles):
    return [{"position_number": i, "position_name": f"P{i}", "card_data": copy.deepcopy(ROWS[t])}
            for i, t in enumerate(titles, 1)]

DRAWN = datetime(2026, 11, 4, 5, 0, tzinfo=timezone.utc)

def _prompt(*titles, **kw):
    """A reading with every layer on (these parts are extra layers, off by default) unless
    `without` says otherwise."""
    kw.setdefault("without", frozenset())
    return analyze_reading("Triad", "3", "q", "None", "1", _items(*titles), drawn_at=DRAWN, **kw)


def test_extra_layers_are_off_by_default_and_titles_angels_and_dates_on():
    """Keep: titles, angels, decan dates. Move to the report: gods, hexagrams, geomancy, the
    Cube of Space and solids. Gone: gematria."""
    from ootk.report import DEFAULT_OFF
    text = _prompt("4 of Swords - Truce", "XVII - The Star", "Prince of Swords",
                   without=DEFAULT_OFF)["analytical_prompt"]
    for mark in ("**Golden Dawn Titles**", "**Angels of the Decans**", "**Decan Dates**", "**Day Ruler:**"):
        assert mark in text, mark
    for mark in ("**Gods (Liber 777)**", "**Court Hexagrams**", "**Letter Values", "Platonic Solid",
                 "Geomantic Figure", "Spatial Dimension", "Cube of Space", "Left out on purpose"):
        assert mark not in text, mark


def test_new_parts_in_the_prompt_and_their_switches():
    r = _prompt("4 of Swords - Truce", "XVII - The Star", "4 of Swords - Truce")
    text = r["analytical_prompt"]
    assert "**Golden Dawn Titles**" in text and "4 of Swords - Truce: Rest from Strife" in text
    assert text.count("Rest from Strife") == 1                      # once per card
    assert "**Angels of the Decans**" in text and "4 of Swords: Laviah (17) and Caliel (18)" in text
    assert "**Decan Dates**" in text and "**Day Ruler:** Wednesday, ruled by Mercury" in text
    assert r["left_out_to_fit"] == []
    for key, mark in (("titles", "**Golden Dawn Titles**"), ("angels", "**Angels of the Decans**"),
                      ("timing", "**Decan Dates**"), ("timing", "**Day Ruler:**")):
        assert mark not in _prompt("4 of Swords - Truce", "XVII - The Star", without=frozenset({key}))["analytical_prompt"]


def test_no_time_means_no_dates_or_day_ruler():
    text = analyze_reading("Single", "1", "q", "None", "1", _items("4 of Swords - Truce"))["analytical_prompt"]
    assert "**Decan Dates**" not in text and "**Day Ruler:**" not in text


def test_long_prompts_leave_the_new_parts_out_in_order(monkeypatch):
    pips = [t for t in ROWS if pip_decan(t) is not None][:12]
    full = len(_prompt(*pips)["analytical_prompt"])
    monkeypatch.setattr(report, "PROMPT_BUDGET", full - 1)
    r = _prompt(*pips)
    assert r["left_out_to_fit"] == ["angels"]
    assert len(r["analytical_prompt"]) <= full - 1
    assert "**Left Out to Fit:** Angels of the decans." in r["analytical_prompt"]
    assert "**Components Left Out:**" not in r["analytical_prompt"]
    monkeypatch.setattr(report, "PROMPT_BUDGET", 10)
    r = _prompt("4 of Swords - Truce", "XVII - The Star", "Queen of Cups")
    assert r["left_out_to_fit"] == list(FIT_ORDER)
    # a part with nothing to say for these cards (no Trump, no court) is not named
    assert _prompt("4 of Swords - Truce")["left_out_to_fit"] == ["angels", "timing", "titles"]
    # a part switched off by hand is named as switched off, not as left out to fit
    r = _prompt("4 of Swords - Truce", without=frozenset({"titles"}))
    assert r["left_out_to_fit"] == ["angels", "timing"]
    assert "**Components Left Out:** Golden Dawn titles." in r["analytical_prompt"]
    assert PROMPT_BUDGET < 78600


# ---------- gods and court hexagrams ----------

from ootk.gods import GODS, RANKS, SUITS, TRIGRAMS, court_hexagram, trump_gods


def test_gods_cover_every_trump_path_and_follow_the_colour_row():
    assert sorted(GODS) == list(range(11, 33))
    majors = [d for d in ROWS.values() if d["arcana_type"] == "Major"]
    assert len(majors) == 22 and all(trump_gods(d) for d in majors)
    assert trump_gods(ROWS["XVII - The Star"]) == GODS[28]          # Aquarius row, as its colours
    assert trump_gods(ROWS["IV - The Emperor"]) == GODS[15]         # Aries row
    assert all("," not in g.replace(", ", "") for pair in GODS.values() for g in pair)  # spaced
    assert all(g.count("[[") == g.count("]]") for pair in GODS.values() for g in pair)


def test_court_hexagrams_follow_rank_over_suit():
    numbers = {}
    for rank in RANKS:
        for suit in SUITS:
            numbers[f"{rank} of {suit}"] = court_hexagram(f"{rank} of {suit}")[0]
    assert len(set(numbers.values())) == 16
    # the owner's values from the Book of Thoth, checked 2026-11-04
    assert numbers == {
        "Knight of Wands": 51, "Knight of Cups": 54, "Knight of Swords": 32, "Knight of Disks": 62,
        "Queen of Wands": 17, "Queen of Cups": 58, "Queen of Swords": 28, "Queen of Disks": 31,
        "Prince of Wands": 42, "Prince of Cups": 61, "Prince of Swords": 57, "Prince of Disks": 53,
        "Princess of Wands": 27, "Princess of Cups": 41, "Princess of Swords": 18,
        "Princess of Disks": 52}
    assert TRIGRAMS == {"Fire": "Chên", "Water": "Tui", "Air": "Sun", "Earth": "Kên"}
    assert court_hexagram("4 of Swords - Truce") is None and court_hexagram("XVII - The Star") is None


def test_gods_and_hexagrams_in_the_prompt_and_their_switches():
    cards = ("XVII - The Star", "Queen of Cups", "4 of Swords - Truce", "XVII - The Star")
    text = _prompt(*cards)["analytical_prompt"]
    assert "**Gods (Liber 777)**" in text and "XVII - The Star (row 28): Ahepi, Aroueris" in text
    assert text.count("Ahepi, Aroueris") == 1
    assert "Queen of Cups (row" not in text                         # courts take no gods
    assert "**Court Hexagrams**" in text and "Queen of Cups: 58 Tui, The Joyous" in text
    for key, mark in (("gods", "**Gods (Liber 777)**"), ("hexagrams", "**Court Hexagrams**")):
        assert mark not in _prompt(*cards, without=frozenset({key}))["analytical_prompt"]


def test_owner_corrections_to_gods_and_hexagram_names():
    assert GODS[22][1] == "Themis, Minos, Aeacus and Rhadamanthus"
    assert GODS[29][1] == "Poseidon [[Hermes Psychopompos]]"
    assert GODS[28][1] == "[Athena] Ganymede" and GODS[30][0] == "Ra and many others"
    assert court_hexagram("Knight of Wands") == (51, "Chên, The Arousing (Crowley: Kan)")
    assert court_hexagram("Princess of Disks") == (52, "Kên, Keeping Still (Crowley: Kan)")
    assert court_hexagram("Queen of Cups") == (58, "Tui, The Joyous")

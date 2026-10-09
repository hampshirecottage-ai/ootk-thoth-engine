"""ootk.sky: the Sun and Moon's longitudes, the Moon's phase and the cards that hold a degree.
Reference positions are PyEphem's apparent geocentric longitudes (of date)."""
from datetime import date, datetime, timezone

import pytest

from ootk import sky


def utc(text):
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)


def off(a, b):
    return abs((a - b + 180) % 360 - 180)


@pytest.mark.parametrize("when,sun,moon", [
    ("2000-01-01 12:00", 280.379, 223.328),
    ("2026-03-20 14:46", 0.004, 20.515),      # the March equinox
    ("2026-10-09 12:00", 196.218, 182.115),
    ("2044-07-15 00:00", 113.176, 345.945),
])
def test_longitudes_match_an_ephemeris(when, sun, moon):
    assert off(sky.sun_longitude(utc(when)), sun) < 0.02
    assert off(sky.moon_longitude(utc(when)), moon) < 0.1


def test_moon_phase():
    assert sky.moon_phase(0, 0) == ("New moon", 0)
    assert sky.moon_phase(10, 100) == ("First quarter", 50)
    assert sky.moon_phase(0, 60)[0] == "Waxing crescent" and sky.moon_phase(0, 120)[0] == "Waxing gibbous"
    assert sky.moon_phase(0, 180) == ("Full moon", 100)
    assert sky.moon_phase(90, 0)[0] == "Last quarter"
    assert sky.moon_phase(196.2, 182.1) == ("Waning crescent", 2)   # 9 Oct 2026, new moon on the 10th


def row(title, kind, attribution, suit=None, rank=None):
    return {"title": title, "arcana_type": kind, "attribution": attribution, "suit": suit,
            "number_or_rank": rank, "key_scale": None, "path_or_sephira": "", "hebrew_letter": "N/A"}


ROWS = [
    row("VIII - Adjustment", "Major", "Libra"),
    row("3 of Swords - Sorrow", "Minor", "Saturn in Libra", "Swords", "3"),
    row("2 of Swords - Peace", "Minor", "Moon in Libra", "Swords", "2"),
    row("Queen of Swords", "Court", "Water of Air - 20° Virgo to 20° Libra", "Swords", "Queen"),
    row("Princess of Swords", "Court", "Earth of Air - Capricorn, Aquarius, Pisces quadrant", "Swords", "Princess"),
    row("Queen of Wands", "Court", "Water of Fire - 20° Pisces to 20° Aries", "Wands", "Queen"),
]


def test_place_names_the_decan_card_sign_trump_and_court():
    p = sky.place(196.2, ROWS)
    assert (p["sign"], p["degree"], p["decan"]) == ("Libra", 16, 2)
    assert (p["pip"], p["trump"], p["court"]) == ("3 of Swords", "Adjustment", "Queen of Swords")
    p = sky.place(202.0, ROWS)                       # past 20° Libra: the Queen's span has ended
    assert p["decan"] == 3 and p["court"] is None and p["pip"] is None


def test_a_court_span_that_crosses_0_aries():
    assert sky.place(355.0, ROWS)["court"] == "Queen of Wands"
    assert sky.place(5.0, ROWS)["court"] == "Queen of Wands"


def test_todays_sky_uses_noon_utc():
    s = sky.todays_sky(date(2026, 10, 9), ROWS)
    assert s["sun"]["pip"] == "3 of Swords" and s["moon"]["pip"] == "2 of Swords"
    assert (s["phase"], s["lit"]) == ("Waning crescent", 2)

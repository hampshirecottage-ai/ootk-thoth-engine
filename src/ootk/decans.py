"""Two more things Book T hangs on the 36 decans, the small cards 2 to 10: the angels of the
Shem ha-Mephorash and the dates the Sun spends in each decan. Also the ruler of the day.

Angels. The 72 angels of the Name (Shem ha-Mephorash), from Exodus 14:19-21, each rule five
degrees (a quinance), so each decan and its small card has two. Book T counts them, like the
decans of the Fourth Operation, from 0° Leo: Vehuiah and Yeliel are the 5 of Wands (Saturn in
Leo). Spellings follow the usual modern English forms, not Regardie's (his Vahaviah and Yelayel);
no. 17 is written Laviah to keep it apart from no. 11, Lauviah.

Dates. Book T times a matter by the decan of the small card: about ten days while the Sun is
in it. The dates are worked out for the reading's year from the Sun's position (sky.py), so
they shift by a day between years as the calendar does.

Day ruler. Each weekday has the planet that names it (Sunday Sun, Monday Moon, Tuesday Mars,
Wednesday Mercury, Thursday Jupiter, Friday Venus, Saturday Saturn), as in the Golden Dawn's
planetary days. The planetary hour is not given: it needs the querent's sunrise and so their
place, which the site never asks for.
"""
from datetime import datetime, timedelta, timezone

from ootk.atlas import decan_pip
from ootk.sky import sun_longitude

ANGELS = (   # from 0° Leo, two per decan
    "Vehuiah", "Yeliel", "Sitael", "Elemiah", "Mahasiah", "Lelahel",
    "Achaiah", "Cahetel", "Haziel", "Aladiah", "Lauviah", "Hahaiah",
    "Yezalel", "Mebahel", "Hariel", "Hakamiah", "Laviah", "Caliel",
    "Leuviah", "Pahaliah", "Nelchael", "Yeiayel", "Melahel", "Haheuiah",
    "Nithhaiah", "Haaiah", "Yerathel", "Seheiah", "Reiyel", "Omael",
    "Lecabel", "Vasariah", "Yehuiah", "Lehahiah", "Chavakiah", "Menadel",
    "Aniel", "Haamiah", "Rehael", "Yeiazel", "Hahahel", "Mikael",
    "Veuliah", "Yelahiah", "Sealiah", "Ariel", "Asaliah", "Mihael",
    "Vehuel", "Daniel", "Hahasiah", "Imamiah", "Nanael", "Nithael",
    "Mebahiah", "Poyel", "Nemamiah", "Yeialel", "Harahel", "Mitzrael",
    "Umabel", "Iahhel", "Anauel", "Mehiel", "Damabiah", "Manakel",
    "Ayael", "Habuhiah", "Rochel", "Yabamiah", "Haiaiel", "Mumiah",
)
LEO = 12                     # decan index of 0° Leo, counted from 0° Aries

DAY_RULERS = ("Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun")   # Monday first
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

_DECAN_OF = {decan_pip(i): i for i in range(36)}     # (suit, number) -> decan from 0° Aries

def pip_decan(card_title):
    """Decan index (0 = Aries 0-10°) of a small card 2-10 ("5 of Wands - Strife"), or None."""
    head = card_title.partition(" - ")[0]
    number, sep, suit = head.partition(" of ")
    if not sep or not number.isdigit():
        return None
    return _DECAN_OF.get((suit, int(number)))

def decan_angels(card_title):
    """("Vehuiah", "Yeliel") for the 5 of Wands, or None for a card that is not a decan pip."""
    i = pip_decan(card_title)
    if i is None:
        return None
    a = ((i - LEO) % 36) * 2
    return ANGELS[a], ANGELS[a + 1]

def _equinox(year):
    """The March equinox of `year` (UTC, to within a minute): the Sun at 0° Aries."""
    lo = datetime(year, 3, 15, tzinfo=timezone.utc)
    hi = datetime(year, 3, 25, tzinfo=timezone.utc)
    while hi - lo > timedelta(minutes=1):
        mid = lo + (hi - lo) / 2
        lo, hi = (mid, hi) if sun_longitude(mid) > 180 else (lo, mid)
    return hi

def _sun_reaches(degree, year):
    """The moment the Sun reaches `degree` (0-360) in the solar year from `year`'s equinox."""
    lo = _equinox(year)
    if degree <= 0:
        return lo
    hi = _equinox(year + 1)
    if degree >= 360:
        return hi
    start = lo
    while hi - lo > timedelta(minutes=1):
        mid = lo + (hi - lo) / 2
        # degrees the Sun has moved since the equinox, rising from 0 to 360 over the year
        moved = (sun_longitude(mid) - sun_longitude(start)) % 360
        lo, hi = (mid, hi) if moved < degree else (lo, mid)
    return hi

def decan_dates(card_title, year):
    """"22 Jul - 1 Aug 2026" or "31 Dec 2026 - 9 Jan 2027": the first and last day (UTC) the Sun is in the card's decan, in the
    solar year from the March equinox of `year`; None for a card that is not a decan pip."""
    i = pip_decan(card_title)
    if i is None:
        return None
    start = _sun_reaches(i * 10, year)
    end = _sun_reaches((i + 1) * 10, year) - timedelta(minutes=1)
    day = lambda d: f"{d.day} {_MONTHS[d.month - 1]}"
    first = day(start) if start.year == end.year else f"{day(start)} {start.year}"
    return f"{first} - {day(end)} {end.year}"

def solar_year(when):
    """The year whose March equinox last came before `when` (an aware datetime)."""
    return when.year if when >= _equinox(when.year) else when.year - 1

def day_ruler(when):
    """("Wednesday", "Mercury") for an aware datetime, in its own zone."""
    return when.strftime("%A"), DAY_RULERS[when.weekday()]

def _once(spread_results):
    seen = set()
    for item in spread_results:
        title = item["card_data"]["title"]
        if title not in seen:
            seen.add(title)
            yield title

def angels_markdown(spread_results):
    """The Angels of the Decans paragraph for section 1, or "" when no decan pip is drawn."""
    parts = [f"{t.partition(' - ')[0]}: {' and '.join(f'{n} ({ANGELS.index(n) + 1})' for n in decan_angels(t))}"
             for t in _once(spread_results) if decan_angels(t)]
    if not parts:
        return ""
    return ("**Angels of the Decans** (the 72 angels of the Shem ha-Mephorash, two for each small "
            "card's decan, numbered 1-72 from 0° Leo as Book T counts them): " + "; ".join(parts) + ".\n\n")

def dates_markdown(spread_results, year):
    """The Decan Dates paragraph for section 1, or "" when no decan pip is drawn."""
    parts = [f"{t.partition(' - ')[0]}: {decan_dates(t, year)}"
             for t in _once(spread_results) if pip_decan(t) is not None]
    if not parts:
        return ""
    return (f"**Decan Dates** (Book T's timing: the days the Sun is in each small card's decan, "
            f"for the year from the March equinox of {year}, in UTC, from the Sun's computed position): " + "; ".join(parts) + ".\n\n")

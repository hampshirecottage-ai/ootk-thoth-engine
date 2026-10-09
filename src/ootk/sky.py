"""Today's sky: where the Sun and Moon stand on a given day, and the cards that hold those
degrees in Book T (the decan's small card, the sign's Trump, the court whose thirty degrees
cover it).

The positions use the short series from Meeus, Astronomical Algorithms (ch. 25 and 47):
the Sun to about 0.02° and the Moon to about 0.1° (checked against PyEphem over 1990-2044),
so a decan can only be misnamed within minutes of the Sun, or a few hours of the Moon,
crossing into the next one. Longitudes are tropical, from 0° Aries at the spring
equinox, the frame the decan wheel in atlas.py already uses. Nothing here interprets a card.
"""
import math
from datetime import datetime, time, timezone

from ootk.atlas import SIGNS, card_atlas, decan_pip, sign_carriers

PHASES = ("New moon", "Waxing crescent", "First quarter", "Waxing gibbous",
          "Full moon", "Waning gibbous", "Last quarter", "Waning crescent")
# New, first quarter, full and last quarter are named within this many degrees of the exact
# moment (the Moon gains about 12° a day on the Sun, so roughly half a day either side).
QUARTER_WINDOW = 6


def _centuries(when):
    """Julian centuries since J2000.0 (2000-01-01 12:00 UTC; the few seconds to TT are ignored)."""
    return (when.timestamp() / 86400 + 2440587.5 - 2451545.0) / 36525


def _sin(deg):
    return math.sin(math.radians(deg))


def sun_longitude(when):
    """The Sun's apparent ecliptic longitude in degrees (Meeus ch. 25, low accuracy)."""
    t = _centuries(when)
    l0 = 280.46646 + 36000.76983 * t + 0.0003032 * t * t
    m = 357.52911 + 35999.05029 * t - 0.0001537 * t * t
    c = ((1.914602 - 0.004817 * t - 0.000014 * t * t) * _sin(m)
         + (0.019993 - 0.000101 * t) * _sin(2 * m) + 0.000289 * _sin(3 * m))
    omega = 125.04 - 1934.136 * t
    return (l0 + c - 0.00569 - 0.00478 * _sin(omega)) % 360


def moon_longitude(when):
    """The Moon's ecliptic longitude in degrees: the largest terms of Meeus ch. 47."""
    t = _centuries(when)
    lp = 218.3164477 + 481267.88123421 * t       # mean longitude
    d = 297.8501921 + 445267.1114034 * t         # mean elongation
    m = 357.5291092 + 35999.0502909 * t          # Sun's mean anomaly
    mp = 134.9633964 + 477198.8675055 * t        # Moon's mean anomaly
    f = 93.2720950 + 483202.0175233 * t          # argument of latitude
    terms = ((6.288774, 0, 0, 1, 0), (1.274027, 2, 0, -1, 0), (0.658314, 2, 0, 0, 0),
             (0.213618, 0, 0, 2, 0), (-0.185116, 0, 1, 0, 0), (-0.114332, 0, 0, 0, 2),
             (0.058793, 2, 0, -2, 0), (0.057066, 2, -1, -1, 0), (0.053322, 2, 0, 1, 0),
             (0.045758, 2, -1, 0, 0), (-0.040923, 0, 1, -1, 0), (-0.034720, 1, 0, 0, 0),
             (-0.030383, 0, 1, 1, 0), (0.015327, 2, 0, 0, -2), (0.010980, 0, 0, 1, -2),
             (0.010675, 4, 0, -1, 0), (0.010034, 0, 0, 3, 0), (0.008548, 4, 0, -2, 0))
    lon = lp + sum(k * _sin(a * d + b * m + c * mp + e * f) for k, a, b, c, e in terms)
    return lon % 360


def moon_phase(sun, moon):
    """(phase name, percent lit) from the two longitudes."""
    elongation = (moon - sun) % 360
    lit = round((1 - math.cos(math.radians(elongation))) / 2 * 100)
    quarter = round(elongation / 90) % 4
    if abs((elongation - quarter * 90 + 180) % 360 - 180) < QUARTER_WINDOW:
        return PHASES[quarter * 2], lit
    return PHASES[int(elongation // 90) * 2 + 1], lit


def _short(title):
    head, _, tail = str(title).partition(" - ")
    return head if " of " in head else (tail or head)


def _covers(arc, lon):
    a, b = arc
    return a <= lon < b or a <= lon + 360 < b


def place(lon, rows):
    """Where a longitude falls and the short names of the cards that hold it. `rows` are
    fetched card rows (any order); a card the rows lack is left out (None)."""
    sign_i, deg = divmod(lon, 30)
    sign = SIGNS[int(sign_i)]
    decan = int(lon // 10)
    suit, n = decan_pip(decan)
    shorts = {_short(r["title"]) for r in rows}
    trump = sign_carriers(rows).get(sign, {}).get("card")
    court = next((r["title"] for r in rows if r.get("arcana_type") == "Court"
                  and any(b - a == 30 and _covers((a, b), lon)
                          for a, b in card_atlas(r, {})["zodiac"]["arcs"])), None)
    return {
        "longitude": lon, "sign": sign, "degree": int(deg), "decan": decan % 3 + 1,
        "pip": f"{n} of {suit}" if f"{n} of {suit}" in shorts else None,
        "trump": trump if trump in shorts else None, "court": court,
    }


def todays_sky(day, rows):
    """The Sun and Moon at noon UTC on `day` (a date), with their cards and the Moon's phase."""
    when = datetime.combine(day, time(12), tzinfo=timezone.utc)
    sun, moon = sun_longitude(when), moon_longitude(when)
    phase, lit = moon_phase(sun, moon)
    return {"sun": place(sun, rows), "moon": place(moon, rows), "phase": phase, "lit": lit}


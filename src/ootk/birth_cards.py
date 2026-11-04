"""Birth cards and year cards: the Major Arcana a birth date reduces to.

This is the modern tarot numerology of Mary K. Greer (Tarot for Your Self, 1984; Who Are You
in the Tarot?, 2002) and Angeles Arrien (The Tarot Handbook, 1987, written for the Thoth
deck). It is not Golden Dawn, but it is widely used with the Thoth deck.

Add the month, day and year of birth as numbers (14 July 1983: 7 + 14 + 1983 = 2004), then
add the digits of the total (2 + 0 + 0 + 4 = 6), and keep adding digits while the result is
over 22. That number is the personality card. While it is 10 or more, its digits added give
the next card, down to a single digit: 19 gives The Sun, then 10 Fortune, then 1 The Magus.
22 stands for The Fool, and 22 reduces to 4, The Emperor. The year card is the same sum with
the year of the querent's latest birthday in place of the birth year.

The numbers follow the Thoth deck's own Atu numbers (VIII Adjustment, XI Lust), as Arrien
uses them. The web page works the numbers out in the browser; the birth date is never sent
or stored, only the two card numbers and the year of the year card.
"""
import re
from datetime import date

ROMAN = ["0", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII",
         "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX", "XXI"]
FOOL_NUMBER = 22          # the Fool's place in the count; its card is Atu 0
# The deck's Major titles, as thoth_cards has them (tests check they match).
MAJOR_NAMES = ["The Fool", "The Magus", "The Priestess", "The Empress", "The Emperor",
               "The Hierophant", "The Lovers", "The Chariot", "Adjustment", "The Hermit",
               "Fortune", "Lust", "The Hanged Man", "Death", "Art", "The Devil", "The Tower",
               "The Star", "The Moon", "The Sun", "The Aeon", "The Universe"]

def _digit_sum(n):
    return sum(int(d) for d in str(n))

def reduce_to_card(total):
    """The first number from 1 to 22 that adding digits reaches from `total` (a positive
    whole number; a total of 22 or less is already a card number)."""
    if total < 1:
        raise ValueError("a birth card total must be a positive whole number")
    n = total if total <= FOOL_NUMBER else _digit_sum(total)
    while n > FOOL_NUMBER:
        n = _digit_sum(n)
    return n

def constellation(number):
    """[19, 10, 1] for 19: the card and each digit sum after it down to a single digit."""
    chain = [number]
    while chain[-1] > 9:
        chain.append(_digit_sum(chain[-1]))
    return chain

def personality_number(birth):
    """Personality card number (1-22) for a datetime.date of birth."""
    return reduce_to_card(birth.month + birth.day + birth.year)

def year_number(birth, year):
    """Year card number (1-22) for the year starting at the birthday in `year`."""
    return reduce_to_card(birth.month + birth.day + year)

def latest_birthday_year(birth, today):
    """The year of the querent's latest birthday on or before `today` (29 February counts
    from 1 March in other years)."""
    month, day = (3, 1) if (birth.month, birth.day) == (2, 29) else (birth.month, birth.day)
    return today.year if (today.month, today.day) >= (month, day) else today.year - 1

def birth_cards_param(birth, today=None):
    """The "19-7-2026" value a reading's settings carry: personality number, year card number,
    year of the year card. The birth date itself cannot be read back from it."""
    today = today or date.today()
    year = latest_birthday_year(birth, today)
    return f"{personality_number(birth)}-{year_number(birth, year)}-{year}"

_PARAM = re.compile(r"^(\d{1,2})-(\d{1,2})-(\d{4})$")

def parse_birth_cards(text):
    """(personality, year card, year) from "19-7-2026", None for blank. ValueError otherwise."""
    text = (text or "").strip()
    if not text:
        return None
    m = _PARAM.match(text)
    if not m or not all(1 <= int(m.group(i)) <= FOOL_NUMBER for i in (1, 2)):
        raise ValueError("Birth cards must look like 19-7-2026: two card numbers from 1 to 22 "
                         "and a year.")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))

def card_title(number):
    """The deck's title for card number 1-22 ("XIX - The Sun"), 22 being The Fool."""
    atu = 0 if number == FOOL_NUMBER else number
    return f"{ROMAN[atu]} - {MAJOR_NAMES[atu]}"

def birth_cards_markdown(text, spread_results):
    """The prompt header line for a reading's birth cards, or "" when it has none.
    """
    parsed = parse_birth_cards(text)
    if not parsed:
        return ""
    personality, year_card, year = parsed
    named = lambda chain: ", then ".join(card_title(n) for n in chain)
    soul = constellation(personality)
    line = f"personality {named(soul[:1])}"
    if len(soul) > 1:
        line += f" (reduces to {named(soul[1:])})"
    line += f"; year card for the year from the birthday in {year}: {named(constellation(year_card)[:1])}"
    wanted = {card_title(n) for n in soul + [year_card]}
    found = [f"{item['card_data']['title']} (Position {item['position_number']})"
             for item in spread_results if item["card_data"]["title"] in wanted]
    drawn = f"Drawn in this reading: {', '.join(found)}." if found else "None of them was drawn."
    return (f"**Birth Cards** (Greer and Arrien tarot numerology from the querent's birth date; "
            f"context only, not used in any score): {line}. {drawn}\n")

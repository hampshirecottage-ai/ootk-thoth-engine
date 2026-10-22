"""Ways to choose a significator, following Book T with Thoth court titles.

Book T picks a court card from the querent's description: the rank from age and gender,
the suit from colouring or temperament. Golden Dawn King, Queen, Prince, Princess are the
Thoth Knight, Queen, Prince, Princess.

The birth-date method uses the zodiacal span each Knight, Queen and Prince rules (from 21°
of one sign to 20° of the next, see thoth_cards.attributions). Princesses rule quadrants of
the heavens, not date spans, so this method never gives a Princess. The web page works the
card out in the browser and sends only the card title; the birth date is never stored.

The start page also asks the Book T questions in plainer words (TEMPERAMENTS, LIFE_STAGES),
with Book T's own wording beside each answer. TOPICS is the later custom of taking the suit
from the matter asked about; its four matters are Book T's own for the four IHVH piles of
the First Operation (Wands work, Cups love, Swords trouble, Disks money).
"""
from datetime import date, timedelta

RANKS = {
    "Knight": "Older man",
    "Queen": "Older woman",
    "Prince": "Younger man",
    "Princess": "Younger woman",
}

SUITS = {
    "Wands": "Very fair or red hair; fiery",
    "Cups": "Fair to light brown hair; watery",
    "Swords": "Dark brown hair; airy",
    "Disks": "Very dark hair; earthy",
}

# The start page's guided questions: the suit by temperament (or by the matter asked about),
# the rank by stage of life. Keys are the same as SUITS and RANKS.
TEMPERAMENTS = {
    "Wands": "Act first: eager, bold, quick to start things",
    "Cups": "Feel first: warm, imaginative, led by the heart",
    "Swords": "Think first: sharp, curious, quick to question",
    "Disks": "Build steadily: patient, practical, down to earth",
}

TOPICS = {
    "Wands": "Work, plans, energy or ambition",
    "Cups": "Love, friendship or feelings",
    "Swords": "A conflict, a worry or a hard decision",
    "Disks": "Money, home, health or the body",
}

LIFE_STAGES = {
    "Knight": "Established, and taking the lead",
    "Queen": "Established, and holding things together",
    "Prince": "Young, and driving things forward",
    "Princess": "Just starting out",
}

RANK_ELEMENTS = {"Knight": "Fire", "Queen": "Water", "Prince": "Air", "Princess": "Earth"}
SUIT_ELEMENTS = {"Wands": "Fire", "Cups": "Water", "Swords": "Air", "Disks": "Earth"}

# The quarter of the heavens round the North Pole each Princess rules.
PRINCESS_QUADRANTS = {
    "Wands": "Cancer, Leo and Virgo",
    "Cups": "Libra, Scorpio and Sagittarius",
    "Swords": "Capricorn, Aquarius and Pisces",
    "Disks": "Aries, Taurus and Gemini",
}

# (first day as (month, day), card), in calendar order. Each span runs until the day before
# the next one starts. Sun ingress dates shift by a day between years, so a birthday on the
# boundary can belong to either card.
BIRTH_SPANS = [
    ((1, 10), "Prince of Swords"),   # 21° Capricorn - 20° Aquarius
    ((2, 9), "Knight of Cups"),      # 21° Aquarius - 20° Pisces
    ((3, 11), "Queen of Wands"),     # 21° Pisces - 20° Aries
    ((4, 11), "Prince of Disks"),    # 21° Aries - 20° Taurus
    ((5, 11), "Knight of Swords"),   # 21° Taurus - 20° Gemini
    ((6, 11), "Queen of Cups"),      # 21° Gemini - 20° Cancer
    ((7, 12), "Prince of Wands"),    # 21° Cancer - 20° Leo
    ((8, 12), "Knight of Disks"),    # 21° Leo - 20° Virgo
    ((9, 12), "Queen of Swords"),    # 21° Virgo - 20° Libra
    ((10, 13), "Prince of Cups"),    # 21° Libra - 20° Scorpio
    ((11, 13), "Knight of Wands"),   # 21° Scorpio - 20° Sagittarius
    ((12, 13), "Queen of Disks"),    # 21° Sagittarius - 20° Capricorn
]


# BIRTH_SPANS[i] runs from 21° of SPAN_SIGNS[i] to 20° of the sign after it.
SPAN_SIGNS = ["Capricorn", "Aquarius", "Pisces", "Aries", "Taurus", "Gemini", "Cancer", "Leo",
              "Virgo", "Libra", "Scorpio", "Sagittarius"]


def book_t_card(rank, suit):
    """Court card for a rank (Knight, Queen, Prince, Princess) and suit."""
    if rank not in RANKS or suit not in SUITS:
        raise ValueError(f"Unknown rank or suit: {rank!r}, {suit!r}")
    return f"{rank} of {suit}"


def card_for_birthday(month, day):
    """Knight, Queen or Prince whose zodiacal span holds this birthday."""
    card = BIRTH_SPANS[-1][1]          # early January belongs to the Queen of Disks
    for start, title in BIRTH_SPANS:
        if (month, day) >= start:
            card = title
    return card


MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]


def _day_text(d):
    return f"{d.day} {MONTHS[d.month - 1]}"


def court_preview(rank, suit):
    """What the start page shows under a chosen court card: its element and the part of the
    zodiac it rules, with the birthdays that fall there."""
    title = book_t_card(rank, suit)
    if rank == "Princess":
        place = f"Rules the {PRINCESS_QUADRANTS[suit]} quarter of the heavens (no birth dates)"
    else:
        i = next(n for n, (_, card) in enumerate(BIRTH_SPANS) if card == title)
        start = date(2001, *BIRTH_SPANS[i][0])
        end = date(2001, *BIRTH_SPANS[(i + 1) % 12][0]) - timedelta(days=1)
        place = (f"21° {SPAN_SIGNS[i]} to 20° {SPAN_SIGNS[(i + 1) % 12]}, "
                 f"birthdays about {_day_text(start)} to {_day_text(end)}")
    return {"element": f"{RANK_ELEMENTS[rank]} of {SUIT_ELEMENTS[suit]}", "place": place}


def court_previews():
    """court_preview for all sixteen court cards, by title."""
    return {book_t_card(r, s): court_preview(r, s) for r in RANKS for s in SUITS}

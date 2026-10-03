"""Ways to choose a significator, following Book T with Thoth court titles.

Book T picks a court card from the querent's description: the rank from age and gender,
the suit from colouring or temperament. Golden Dawn King, Queen, Prince, Princess are the
Thoth Knight, Queen, Prince, Princess.

The birth-date method uses the zodiacal span each Knight, Queen and Prince rules (from 21°
of one sign to 20° of the next, see thoth_cards.attributions). Princesses rule quadrants of
the heavens, not date spans, so this method never gives a Princess. The web page works the
card out in the browser and sends only the card title; the birth date is never stored.
"""

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

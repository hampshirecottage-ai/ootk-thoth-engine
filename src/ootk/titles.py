"""Golden Dawn titles: the Order's own long names for the cards.

Small cards and court cards follow Book T (Regardie's The Golden Dawn; Crowley's Book of Thoth
gives the same). Each small card is "Lord of ..." (the 4 of Swords is the Lord of Rest from
Strife). The Trumps follow Liber 777's wording, which Crowley used; Regardie's Book T differs in
places (the Hierophant "Magus of the Eternal Gods", the Lovers "Children of the Voice Divine",
the Hermit "The Magus of the Voice of Light, The Prophet of the Gods", Death "Gates" for
"Gate"), and some witnesses have "Son of the Morning" for the Emperor where 777 and the
Equinox have "Sun". Text variants within Book T itself (Knight of Disks "Wide" or "Wild",
Prince of Swords "Chariot" or "Chariots") take the form of its introductory list. The Aces'
title, "the Root of the Powers of Fire" and so on, is already their Attribution line, so they
have none here. Court ranks are the Thoth names: the mounted father is the Knight (Book T's
King), the chariot-borne son the Prince. The keys are Thoth Atu numbers: Adjustment (VIII)
and Lust (XI) take the titles of Justice and Strength, whose Golden Dawn places differ.

The prompt gives each card's first title only, and drops "Lord of" from the small cards, to
keep the longest Opening of the Key under the length some AIs stop reading at.
"""

PIP_TITLES = {
    "Wands": {2: "Dominion", 3: "Established Strength", 4: "Perfected Work", 5: "Strife",
              6: "Victory", 7: "Valour", 8: "Swiftness", 9: "Great Strength", 10: "Oppression"},
    "Cups": {2: "Love", 3: "Abundance", 4: "Blended Pleasure", 5: "Loss in Pleasure",
             6: "Pleasure", 7: "Illusionary Success", 8: "Abandoned Success",
             9: "Material Happiness", 10: "Perfected Success"},
    "Swords": {2: "Peace Restored", 3: "Sorrow", 4: "Rest from Strife", 5: "Defeat",
               6: "Earned Success", 7: "Unstable Effort", 8: "Shortened Force",
               9: "Despair and Cruelty", 10: "Ruin"},
    "Disks": {2: "Harmonious Change", 3: "Material Works", 4: "Earthly Power",
              5: "Material Trouble", 6: "Material Success", 7: "Success Unfulfilled",
              8: "Prudence", 9: "Material Gain", 10: "Wealth"},
}

TRUMP_TITLES = {
    "0": "The Spirit of Aethyr",
    "I": "The Magus of Power",
    "II": "The Priestess of the Silver Star",
    "III": "The Daughter of the Mighty Ones",
    "IV": "Sun of the Morning; Chief among the Mighty",
    "V": "The Magus of the Eternal",
    "VI": "The Children of the Voice; the Oracle of the Mighty Gods",
    "VII": "The Child of the Powers of the Waters; the Lord of the Triumph of Light",
    "VIII": "The Daughter of the Lords of Truth; the Ruler of the Balance",
    "IX": "The Prophet of the Eternal; the Magus of the Voice of Power",
    "X": "The Lord of the Forces of Life",
    "XI": "The Daughter of the Flaming Sword",   # Book T adds "Leader of the Lion"
    "XII": "The Spirit of the Mighty Waters",
    "XIII": "The Child of the Great Transformers; the Lord of the Gate of Death",
    "XIV": "The Daughter of the Reconcilers; the Bringer-forth of Life",
    "XV": "The Lord of the Gates of Matter; the Child of the Forces of Time",
    "XVI": "The Lord of the Hosts of the Mighty",
    "XVII": "The Daughter of the Firmament; the Dweller between the Waters",
    "XVIII": "The Ruler of Flux and Reflux; the Child of the Sons of the Mighty",
    "XIX": "The Lord of the Fire of the World",
    "XX": "The Spirit of the Primal Fire",
    "XXI": "The Great One of the Night of Time",
}

COURT_TITLES = {
    "Knight of Wands": "Lord of the Flame and the Lightning; King of the Spirits of Fire",
    "Queen of Wands": "Queen of the Thrones of Flame",
    "Prince of Wands": "Prince of the Chariot of Fire",
    "Princess of Wands": "Princess of the Shining Flame; Rose of the Palace of Fire",
    "Knight of Cups": "Lord of the Waves and the Waters; King of the Hosts of the Sea",
    "Queen of Cups": "Queen of the Thrones of the Waters",
    "Prince of Cups": "Prince of the Chariot of the Waters",
    "Princess of Cups": "Princess of the Waters; Lotus of the Palace of the Floods",
    "Knight of Swords": "Lord of the Winds and the Breezes; King of the Spirits of Air",
    "Queen of Swords": "Queen of the Thrones of Air",
    "Prince of Swords": "Prince of the Chariot of the Winds",
    "Princess of Swords": "Princess of the Rushing Winds; Lotus of the Palace of Air",
    "Knight of Disks": "Lord of the Wide and Fertile Land; King of the Spirits of Earth",
    "Queen of Disks": "Queen of the Thrones of Earth",
    "Prince of Disks": "Prince of the Chariot of Earth",
    "Princess of Disks": "Princess of the Echoing Hills; Rose of the Palace of Earth",
}

def full_title(card_title):
    """Book T's full title for a deck title ("4 of Swords - Truce" -> "Lord of Rest from
    Strife"), or None for an Ace or an unknown title."""
    head, _, _ = card_title.partition(" - ")
    if head in TRUMP_TITLES:
        return TRUMP_TITLES[head]
    if card_title in COURT_TITLES:
        return COURT_TITLES[card_title]
    number, sep, suit = head.partition(" of ")
    if sep and number.isdigit() and int(number) in PIP_TITLES.get(suit, {}):
        return f"Lord of {PIP_TITLES[suit][int(number)]}"
    return None

def short_title(card_title):
    """The prompt's form: the first title only, and "Rest from Strife" for a small card; None
    when there is none, or when it only repeats the card's own Thoth name (2 of Cups - Love)."""
    title = full_title(card_title)
    if not title:
        return None
    first = title.split("; ")[0]
    head, _, name = card_title.partition(" - ")
    if first.startswith("Lord of ") and " of " in head and head[0].isdigit():
        first = first[len("Lord of "):]
        if first.lower() == name.lower():
            return None
    return first

def titles_markdown(spread_results):
    """The Golden Dawn Titles paragraph for the end of section 1: each card drawn once, in the
    order first drawn, or "" when no card drawn has one to add."""
    seen, parts = set(), []
    for item in spread_results:
        title = item["card_data"]["title"]
        if title in seen:
            continue
        seen.add(title)
        short = short_title(title)
        if short:
            parts.append(f"{title}: {short}")
    if not parts:
        return ""
    return ("**Golden Dawn Titles** (Book T for small and court cards, Liber 777 for Trumps; first "
            "title only; a small card's is \"Lord of ...\", and ones that only repeat the card's name "
            "are left out): " + "; ".join(parts) + ".\n\n")

"""Two more correspondences: the gods of Liber 777 for the Trumps, and Crowley's I Ching
hexagrams for the court cards.

Gods. Liber 777 lists gods for each path of the Tree. The prompt gives two columns for each
Trump's path (rows 11-32): XIX, the Egyptian gods, which Crowley drew into the Thoth Trumps,
and XXXIV, the Greek gods. The Roman and the practical Egyptian columns are left out to keep
the prompt short. [ ] and [[ ]] are 777's own marks for its later additions. Under the Thoth
swap the Emperor and the Star take the gods of their sign's row (Emperor 15 Aries, Star 28
Aquarius), as their colours do (colour_key_scale), not of their letter's row. The values come
from the database's 777 table with its typing slips cleaned (spaces after commas, "Thoth and
Cynocephalus", the closing "]]" after Hathor in row 23), and were checked against 777 by the
site's owner on 2026-11-04.

Hexagrams. Crowley (The Book of Thoth) gives each court card a hexagram made of two trigrams:
the rank's element on top, the suit's below. The elements' trigrams are Fire Chên (thunder),
Water Tui (lake), Air Sun (wind), Earth Kên (mountain); the ranks are Knight Fire, Queen Water,
Prince Air, Princess Earth. Ten of the sixteen were checked against the book by the owner (CHECKED);
the other six are worked out from that rule and still need checking.
"""

GODS = {   # 777 row: (Egyptian, column XIX; Greek, column XXXIV)
    11: ("Nu [[Hoor-pa-kraat as ATU 0]]", "Zeus"),
    12: ("Thoth and Cynocephalus", "Hermes"),
    13: ("Chomse", "Artemis, Hekate"),
    14: ("Hathor", "Aphrodite"),
    15: ("Men Thu", "Athena"),
    16: ("Asar, Ameshet, Apis", "Here"),
    17: ("Twin Deities, Rekht, Merti [[Heru-Ra-Ha]]", "Castor and Pollux, Apollo the Diviner, Eros"),
    18: ("Khephra", "Apollo the Charioteer"),
    19: ("Ra-Hoor-Khuit, Pasht, Sekhet, Mau", "Demeter"),
    20: ("Isis (as Virgin)", "Attis"),
    21: ("Amoun-Ra", "Zeus"),
    22: ("Ma", "Themis, Minos, Aecus and Rhadamanthus"),
    23: ("Tum, Ptah, Auramoth (as Water), Asar (as Hanged Man), Hekar, Isis [[Hathor]]", "Poseidon"),
    24: ("Merti goddesses, Typhon, Apep, Khephra", "Ares [[Apollo the Pythean, Thanatos]]"),
    25: ("Nephthys", "Apollo, Artemis (hunters)"),
    26: ("Khem (Set)", "Pan, Priapus"),
    27: ("Horus", "Ares [[Athena]]"),
    28: ("Ahepi, Aroueris", "[[Athena]] Ganymede"),
    29: ("Khephra (as Scarab in Tarot Trump)", "Poseidon [[Hermes Psychopompus]]"),
    30: ("Ra", "Helios, Apollo"),
    31: ("Thoum-Aesh-Neith, Mau, Kabeshunt, Horus, Tarpesheth", "Hades"),
    32: ("Sebek, Mako", "[Athena]"),
}

TRIGRAMS = {"Fire": "Chên", "Water": "Tui", "Air": "Sun", "Earth": "Kên"}
RANKS = {"Knight": "Fire", "Queen": "Water", "Prince": "Air", "Princess": "Earth"}
SUITS = {"Wands": "Fire", "Cups": "Water", "Swords": "Air", "Disks": "Earth"}

# (upper trigram, lower trigram) -> King Wen number and name
_HEXAGRAMS = {
    ("Chên", "Chên"): (51, "Chên, The Arousing"),
    ("Tui", "Chên"): (17, "Sui, Following"),
    ("Sun", "Chên"): (42, "Yi, Increase"),
    ("Kên", "Chên"): (27, "I, Nourishment"),
    ("Chên", "Tui"): (54, "Kuei Mei, The Marrying Maiden"),
    ("Tui", "Tui"): (58, "Tui, The Joyous"),
    ("Sun", "Tui"): (61, "Chung Fu, Inner Truth"),
    ("Kên", "Tui"): (41, "Sun, Decrease"),
    ("Chên", "Sun"): (32, "Hêng, Duration"),
    ("Tui", "Sun"): (28, "Ta Kuo, Preponderance of the Great"),
    ("Sun", "Sun"): (57, "Sun, The Gentle"),
    ("Kên", "Sun"): (18, "Ku, Work on What Has Been Spoiled"),
    ("Chên", "Kên"): (62, "Hsiao Kuo, Preponderance of the Small"),
    ("Tui", "Kên"): (31, "Hsien, Influence"),
    ("Sun", "Kên"): (53, "Chien, Development"),
    ("Kên", "Kên"): (52, "Kên, Keeping Still"),
}
# The owner's 2026-11-04 check gave these ten from the Book of Thoth; the rest follow the rule.
CHECKED = {"Knight of Wands", "Queen of Wands", "Prince of Wands", "Princess of Wands",
           "Prince of Cups", "Prince of Swords", "Princess of Swords", "Queen of Disks",
           "Prince of Disks", "Princess of Disks"}

def court_hexagram(card_title):
    """(51, "Chên, The Arousing") for "Knight of Wands", or None for a card that is not a court."""
    rank, sep, suit = card_title.partition(" - ")[0].partition(" of ")
    if not sep or rank not in RANKS or suit not in SUITS:
        return None
    return _HEXAGRAMS[TRIGRAMS[RANKS[rank]], TRIGRAMS[SUITS[suit]]]

def trump_gods(card_data):
    """(Egyptian, Greek) for a Trump's row from its colour_key_scale, or None."""
    return GODS.get(card_data.get("colour_key_scale"))

def _once(spread_results):
    seen = set()
    for item in spread_results:
        data = item["card_data"]
        if data["title"] not in seen:
            seen.add(data["title"])
            yield data

def gods_markdown(spread_results):
    """The Gods paragraph for the end of section 1, or "" when no Trump is drawn."""
    parts = []
    for data in _once(spread_results):
        gods = trump_gods(data)
        if gods and data.get("arcana_type") == "Major":
            parts.append(f"{data['title']} (row {data['colour_key_scale']}): {gods[0]} / {gods[1]}")
    if not parts:
        return ""
    return ("**Gods (Liber 777)** (Egyptian, column XIX / Greek, column XXXIV, from the row the "
            "card's colours follow; [ ] and [[ ]] are 777's later additions): "
            + "; ".join(parts) + ".\n\n")

def hexagrams_markdown(spread_results):
    """The Court Hexagrams paragraph for the end of section 1, or "" when no court is drawn."""
    parts = []
    for data in _once(spread_results):
        hexagram = court_hexagram(data["title"])
        if hexagram:
            parts.append(f"{data['title'].partition(' - ')[0]}: {hexagram[0]} {hexagram[1]}")
    if not parts:
        return ""
    return ("**Court Hexagrams** (Crowley, Book of Thoth: the rank's trigram over the suit's; "
            "Fire thunder, Water lake, Air wind, Earth mountain): " + "; ".join(parts) + ".\n\n")

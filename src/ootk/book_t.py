"""Book T's own way of reading the Opening of the Key: piles, counting and pairing.

Checked against Book T as printed in The Equinox I(8) (1912) and reprinted in The Book of
Thoth ("The Behaviour of the Tarot"), 2026-11-01. In each operation the significator is
looked for in one place chosen beforehand; the cards round it are counted ("in the
direction in which he faces"; "the counting should include the card from which you count")
and then paired outwards from it.

    Op 1  cut into four packs, I H V H from right to left; read the significator's pack if
          it is the one the question is about, otherwise abandon the divination.
    Op 2  deal into twelve stacks for the houses; read the expected house, else one cognate
          house; "on a second failure, abandon the divination".
    Op 3  the same with twelve stacks for the signs.
    Op 4  set the significator down; "the thirty-six cards following form a ring round him".
    Op 5  deal ten packs for the Sephiroth; an expected Sephira is chosen, but "failure does
          not here necessarily imply that the divination has gone astray", so the pack that
          holds the significator is read either way.

Where the text is silent this module makes a choice, and SITE_RULES lists each one so the
prompt can say which rules are the site's and not Book T's.

Everything here is a pure function of a shuffled deck (the same per-operation shuffles as
shuffle.draw_spread), so a seed always gives the same reading. A deck is a list of card
rows with at least `card_id` and `title`, top card first.
"""
from ootk.analysis import ELEMENT_MAJOR_NOTES, PLANETARY_MAJORS, major_name

# The four packs of Operation 1. Book T names the subjects; the suits are this site's
# correspondence (the pack's letter's element), not words from the text.
IHVH_PACKS = (
    {"letter": "Yod", "suit": "Wands", "subject": "work, business"},
    {"letter": "Heh", "suit": "Cups", "subject": "love, marriage, pleasure"},
    {"letter": "Vau", "suit": "Swords", "subject": "trouble, loss, scandal, quarrelling"},
    {"letter": "Heh final", "suit": "Disks", "subject": "money, goods, purely material matters"},
)

STACKS = {2: 12, 3: 12, 5: 10}       # operations dealt into stacks, and how many
OP4_RING = 36                        # cards following the significator in Operation 4

# Choices this module makes where Book T is silent, worded for the prompt.
SITE_RULES = {
    "cut": "the deck is cut into four equal packs (Book T does not say where to cut)",
    "deal": "stacks are dealt one card to each stack in turn (Book T says only 'deal into stacks')",
    "ring": "Operation 4's ring wraps round to the top of the deck when fewer than 36 cards follow",
    "stop": "counting stops on reaching a card already counted",
    "leftover": "a card left over when pairing is read on its own",
    "facing": ("each court card faces the way it looks on the Thoth card, read from the deck; "
               "one facing straight out, or a significator that is not a court card, is counted "
               "from right to left"),
}

# Which way each court figure looks on the Thoth card, 'left' or 'right' as you look at it,
# or 'front'. Book T gives no list; the owner read these from the deck (2026-11-01). Any card
# not listed (a Trump or pip used as significator) counts as 'front'.
COURT_FACING = {
    "Knight of Wands": "right", "Queen of Wands": "front", "Prince of Wands": "right",
    "Princess of Wands": "front",
    "Knight of Cups": "left", "Queen of Cups": "left", "Prince of Cups": "left",
    "Princess of Cups": "right",
    "Knight of Swords": "right", "Queen of Swords": "right", "Prince of Swords": "right",
    "Princess of Swords": "right",
    "Knight of Disks": "right", "Queen of Disks": "right", "Prince of Disks": "left",
    "Princess of Disks": "front",
}


def count_value(card):
    """How many cards Book T counts on from `card`, the card itself included."""
    title = str(card.get("title") or "")
    arcana = card.get("arcana_type")
    if arcana == "Major":
        name = major_name(card)
        if name in ELEMENT_MAJOR_NOTES:            # the Fool, the Hanged Man, the Aeon
            return 3
        return 9 if name in PLANETARY_MAJORS else 12
    if arcana == "Court" or title.split(" ", 1)[0] in ("Knight", "Queen", "Prince", "Princess"):
        return 7 if title.startswith("Princess") else 4
    head = title.split(" ", 1)[0]
    if head == "Ace":
        return 11
    return int(head)


def direction(sig_card, facing=None):
    """+1 to count rightwards along the laid-out pile, -1 leftwards (see SITE_RULES['facing'])."""
    table = COURT_FACING if facing is None else facing
    return 1 if table.get(str(sig_card.get("title") or ""), "front") == "right" else -1


def count_chain(pile, start, step_dir):
    """Book T's count round `pile` (laid out as a ring) from index `start`.

    Returns the list of pile indices in the order counted, starting with `start`, and the
    index the count stopped on (a card already counted), or None when the count stopped
    because a card counts only itself round the whole ring."""
    n = len(pile)
    chain, seen, pos = [start], {start}, start
    while True:
        move = (count_value(pile[pos]) - 1) % n
        if move == 0:
            return chain, None
        pos = (pos + step_dir * move) % n
        if pos in seen:
            return chain, pos
        chain.append(pos)
        seen.add(pos)


def pair_round(pile, start):
    """The cards on either side of `start`, then those outside them, and so on.

    Returns ([(left index, right index), ...], leftover index or None). 'Left' and 'right'
    are as the pile is laid out (lower and higher index), round the ring."""
    n = len(pile)
    others = [(start + k) % n for k in range(1, n)]          # rightwards round the ring
    pairs = []
    i, j = len(others) - 1, 0
    while j < i:
        pairs.append((others[i], others[j]))
        i, j = i - 1, j + 1
    return pairs, (others[i] if i == j else None)


def _read_pile(op, place, pile, sig_card, facing, **extra):
    start = next(i for i, c in enumerate(pile) if c["card_id"] == sig_card["card_id"])
    step = direction(sig_card, facing)
    chain, stopped_on = count_chain(pile, start, step)
    pairs, leftover = pair_round(pile, start)
    return {"op": op, "place": place, "status": "read", "pile": pile, "start": start,
            "direction": "right" if step > 0 else "left", "chain": chain,
            "stopped_on": stopped_on, "pairs": pairs, "leftover": leftover, **extra}


def four_packs(deck):
    """Operation 1's packs as Book T lays them: the deck is cut and the top half put to the
    left, then each half cut and its top put to the left; the four stacks are I H V H from
    right to left. Returns the packs in I H V H order, each top card first."""
    q = len(deck) // 4
    left_to_right = [deck[:q], deck[q:2 * q], deck[2 * q:3 * q], deck[3 * q:]]
    return list(reversed(left_to_right))


def deal_stacks(deck, count):
    """`count` stacks dealt one card to each in turn; each stack top card first."""
    return [deck[i::count] for i in range(count)]


def _holds(pile, sig_card):
    return any(c["card_id"] == sig_card["card_id"] for c in pile)


def operation_one(deck, sig_card, expected_pack, facing=None, strict=True):
    """Operation 1. `expected_pack` is 0-3 (Yod, Heh, Vau, Heh final): the subject the
    querent came about. Wrong pack -> status 'abandoned', as Book T says; with strict=False
    the significator's pack is read anyway, with status 'missed'."""
    packs = four_packs(deck)
    found = next(i for i, p in enumerate(packs) if _holds(p, sig_card))
    place = dict(IHVH_PACKS[found], index=found)
    if found != expected_pack and not strict:
        return _read_pile(1, place, packs[found], sig_card, facing, status="missed",
                          expected=dict(IHVH_PACKS[expected_pack], index=expected_pack))
    if found != expected_pack:
        return {"op": 1, "place": place, "status": "abandoned",
                "expected": dict(IHVH_PACKS[expected_pack], index=expected_pack)}
    return _read_pile(1, place, packs[found], sig_card, facing)


def operation_stacks(op, deck, sig_card, expected, cognate=None, facing=None, strict=True):
    """Operations 2, 3 and 5: `expected` and `cognate` are 0-based stack numbers (house,
    sign or Sephira). Ops 2 and 3 read the expected stack, else the cognate one, else are
    abandoned (with strict=False: the stack holding the significator, status 'missed').
    Op 5 always reads the stack holding the significator and says whether it
    was the expected one."""
    stacks = deal_stacks(deck, STACKS[op])
    found = next(i for i, s in enumerate(stacks) if _holds(s, sig_card))
    if op == 5:
        return _read_pile(5, found, stacks[found], sig_card, facing,
                          expected=expected, as_expected=found == expected)
    for tried, which in ((expected, "expected"), (cognate, "cognate")):
        if tried is not None and _holds(stacks[tried], sig_card):
            return _read_pile(op, tried, stacks[tried], sig_card, facing,
                              expected=expected, cognate=cognate, found_in=which)
    if not strict:
        return _read_pile(op, found, stacks[found], sig_card, facing, status="missed",
                          expected=expected, cognate=cognate, found_in=None)
    return {"op": op, "place": found, "status": "abandoned", "expected": expected, "cognate": cognate}


def operation_four(deck, sig_card, facing=None):
    """Operation 4: the significator with the 36 cards that follow it, as a ring."""
    at = next(i for i, c in enumerate(deck) if c["card_id"] == sig_card["card_id"])
    ring = [deck[(at + k) % len(deck)] for k in range(OP4_RING + 1)]
    return _read_pile(4, None, ring, sig_card, facing,
                      wrapped=at + OP4_RING >= len(deck))


def opening_of_the_key(cards, seed, sig_card, expected, facing=None, strict=False):
    """All five operations, each from its own shuffle of the whole deck (the same shuffles
    as shuffle.draw_spread's master pipeline). By default (the owner's choice, 2026-11-01) no
    operation stops the reading: a missed place reads the pile that holds the significator
    and is marked 'missed', so the prompt can say Book T would stop there. strict=True stops
    after an abandoned operation, as Book T does.

    `expected` = {"pack": 0-3, "house": (expected, cognate or None), "sign": (expected,
    cognate or None), "sephira": 0-9}, all 0-based. Returns the operations read, in order."""
    from ootk.shuffle import operation_seed, shuffle_deck     # shuffle imports nothing from here

    if not any(c["card_id"] == sig_card["card_id"] for c in cards):
        raise ValueError(f"The significator {sig_card.get('title')!r} is not in the deck.")
    ops = []
    for op in range(1, 6):
        deck = shuffle_deck(cards, operation_seed(seed, op))
        if op == 1:
            result = operation_one(deck, sig_card, expected["pack"], facing, strict)
        elif op == 4:
            result = operation_four(deck, sig_card, facing)
        elif op == 5:
            result = operation_stacks(5, deck, sig_card, expected["sephira"], facing=facing)
        else:
            exp, cog = expected["house" if op == 2 else "sign"]
            result = operation_stacks(op, deck, sig_card, exp, cog, facing, strict)
        ops.append(result)
        if result["status"] == "abandoned":
            break
    return ops


# ---------- Turning the operations into reading positions ----------

HOUSE_NAMES = ("1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th", "11th", "12th")
SIGN_NAMES = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
              "Sagittarius", "Capricorn", "Aquarius", "Pisces")
SEPHIRA_NAMES = ("Kether", "Chokmah", "Binah", "Chesed", "Geburah", "Tiphareth", "Netzach",
                 "Hod", "Yesod", "Malkuth")


def place_name(op, index):
    """The plain name of stack `index` in operation `op` ('the 7th house', 'Cancer', ...)."""
    if op == 1:
        pack = IHVH_PACKS[index]
        return f"the {pack['letter']} pack ({pack['subject']})"
    if op == 2:
        return f"the {HOUSE_NAMES[index]} house"
    if op == 3:
        return SIGN_NAMES[index]
    if op == 5:
        return f"{index + 1}. {SEPHIRA_NAMES[index]}"
    return "the Significator and the 36 cards after it"


def _place_index(o):
    return o["place"]["index"] if isinstance(o["place"], dict) else o["place"]


def positions(ops):
    """Reading positions for the operations read: [(position name, card)], each operation
    starting with the Significator and going rightwards round its pile (see
    spreads.BOOK_T_KEY), with each operation's chain, pairs and leftover renumbered to match
    (keys 'chain_at', 'stop_at', 'leftover_at', 0-based within the operation)."""
    out = []
    for o in ops:
        if o["status"] == "abandoned":
            continue
        pile, start, n = o["pile"], o["start"], len(o["pile"])
        place = place_name(o["op"], _place_index(o)) if o["op"] != 4 else "the ring of 36"
        place = place[0].upper() + place[1:]
        for k in range(n):
            where = "the Significator" if k == 0 else f"{k} to the right of the Significator"
            out.append((f"[Op {o['op']}] {place}: {where}", pile[(start + k) % n]))
        o["chain_at"] = [(i - start) % n for i in o["chain"]]
        o["stop_at"] = None if o["stopped_on"] is None else (o["stopped_on"] - start) % n
        o["leftover_at"] = None if o["leftover"] is None else (o["leftover"] - start) % n
    return out


def status_line(o):
    """One sentence on where the Significator was looked for and found."""
    op = o["op"]
    if op == 1:
        found = place_name(1, o["place"]["index"])
        if o["status"] == "read":
            return f"The Significator is in {found}, the pack this question is about."
        return (f"The question is about {place_name(1, o['expected']['index'])}, but the Significator "
                f"is in {found}. Book T says to abandon the divination here; this site reads on "
                f"with {found}, so treat this operation with caution.")
    if op == 4:
        return ("Book T sets the Significator down and lets the 36 cards that follow it in the "
                "deck form a ring round it." + (" Fewer than 36 followed it, so the ring carries "
                "on from the top of the deck." if o.get("wrapped") else ""))
    expected = place_name(op, o["expected"])
    found = place_name(op, o["place"])
    if op == 5:
        if o["as_expected"]:
            return f"The Significator is in {found}, the Sephira expected for this question."
        return (f"The Significator was expected in {expected} but is in {found}. Book T says a "
                f"miss here need not mean the divination has gone astray, so {found} is read.")
    if o["status"] == "read" and o["found_in"] == "expected":
        return f"The Significator is in {found}, the place expected for this question."
    if o["status"] == "read":
        return (f"The Significator was not in {expected}, the place expected, but is in "
                f"{found}, the related place tried next, as Book T allows.")
    tried = expected + (f" or {place_name(op, o['cognate'])}" if o.get("cognate") is not None else "")
    return (f"The Significator was not in {tried}. Book T says to abandon the divination here; "
            f"this site reads on with {found}, where it is, so treat this operation with caution.")


EXPECT_HELP = ("pack,house,sign,sephira, counted from 1: pack 1-4 (Yod fire/work, Heh love, Vau "
               "trouble/loss, Heh final money), house 1-12, sign 1-12 (1 = Aries), Sephira 1-10 "
               "(1 = Kether); a house or sign may add a related one to try next after a slash, "
               "e.g. '1,10/6,10,6'")


def parse_expect(text):
    """The expected places typed as EXPECT_HELP describes, as opening_of_the_key's
    `expected` (0-based). Raises ValueError with a plain message if anything is off."""
    parts = [p.strip() for p in (text or "").split(",")]
    if len(parts) != 4:
        raise ValueError(f"Expected places need four parts: {EXPECT_HELP}.")

    def number(s, top, what):
        if not s.isdigit() or not 1 <= int(s) <= top:
            raise ValueError(f"The {what} must be a number from 1 to {top}, not {s!r}.")
        return int(s) - 1

    def with_cognate(s, what):
        first, _, second = s.partition("/")
        exp = number(first.strip(), 12, what)
        cog = number(second.strip(), 12, f"related {what}") if second.strip() else None
        if cog == exp:
            raise ValueError(f"The related {what} must differ from the expected one.")
        return exp, cog

    return {"pack": number(parts[0], 4, "pack"), "house": with_cognate(parts[1], "house"),
            "sign": with_cognate(parts[2], "sign"), "sephira": number(parts[3], 10, "Sephira")}


# ---------- Expected places suggested from the question (the web form) ----------

# What a question is about, and where the Significator is then expected: Book T's own pack
# subjects for Operation 1; for the rest this site's suggestion (the house that rules the
# matter and a related one, that house's sign and the related house's sign, and the Sephira
# of the matching planet). The querent can change every one. `words` are matched against
# the question, lower-cased, at the start of a word.
SUBJECTS = (
    {"key": "work", "label": "Work, career or business", "pack": 0, "house": (9, 5), "sign": (9, 5),
     "sephira": 7, "words": ("work", "job", "career", "business", "boss", "employ", "promot",
                             "project", "office", "company", "client", "colleague", "retire")},
    {"key": "love", "label": "Love, marriage or pleasure", "pack": 1, "house": (6, 4), "sign": (6, 4),
     "sephira": 6, "words": ("love", "marr", "partner", "relationship", "dating", "date ", "romance",
                             "husband", "wife", "boyfriend", "girlfriend", "crush", "wedding")},
    {"key": "trouble", "label": "Trouble, loss or a quarrel", "pack": 2, "house": (11, 7),
     "sign": (11, 7), "sephira": 4, "words": ("quarrel", "argu", "fight", "conflict", "loss", "lost",
                                              "lose", "scandal", "enemy", "lawsuit", "court case",
                                              "trouble", "danger", "betray")},
    {"key": "money", "label": "Money, goods or property", "pack": 3, "house": (1, 7), "sign": (1, 7),
     "sephira": 3, "words": ("money", "financ", "debt", "loan", "invest", "salary", "pay", "buy",
                             "sell", "house", "property", "rent", "inherit", "savings", "afford")},
    {"key": "health", "label": "Health", "pack": 2, "house": (5, 11), "sign": (5, 11), "sephira": 5,
     "words": ("health", "ill", "sick", "heal", "doctor", "surgery", "diagnos", "recover", "body")},
    {"key": "home", "label": "Home or family", "pack": 3, "house": (3, 9), "sign": (3, 9), "sephira": 8,
     "words": ("home", "family", "mother", "father", "parent", "child", "son", "daughter", "move",
               "moving", "sister", "brother")},
    {"key": "study", "label": "Study, travel or beliefs", "pack": 0, "house": (8, 2), "sign": (8, 2),
     "sephira": 7, "words": ("study", "school", "university", "exam", "degree", "learn", "travel",
                             "abroad", "journey", "trip", "faith", "spiritual", "religio", "teach")},
)


def suggest_subject(topic):
    """The SUBJECTS key the question's words point to most, or None when none match."""
    import re
    text = " " + re.sub(r"\s+", " ", (topic or "").lower()) + " "
    best, hits = None, 0
    for s in SUBJECTS:
        n = sum(len(re.findall(r"(?<![a-z])" + re.escape(w), text)) for w in s["words"])
        if n > hits:
            best, hits = s["key"], n
    return best


def expect_text(pack, house, house2, sign, sign2, sephira):
    """The web form's six fields (each 1-based text, the related ones may be blank) as the
    `--expect` text parse_expect reads, so the form, share links and the CLI share one form."""
    def part(a, b):
        return f"{a}/{b}" if b else f"{a}"
    return f"{pack},{part(house, house2)},{part(sign, sign2)},{sephira}"


def expect_from_parsed(expected):
    """opening_of_the_key's `expected` back as `--expect` text (1-based)."""
    def part(pair):
        exp, cog = pair
        return f"{exp + 1}/{cog + 1}" if cog is not None else f"{exp + 1}"
    return (f"{expected['pack'] + 1},{part(expected['house'])},{part(expected['sign'])},"
            f"{expected['sephira'] + 1}")

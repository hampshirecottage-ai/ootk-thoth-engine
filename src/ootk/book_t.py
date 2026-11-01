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
    "facing": "a significator facing straight out, or not a court card, is counted from right to left",
}

# Which way each court figure looks on the card, 'left' or 'right' as you look at it, or
# 'front'. Book T gives no list; the owner fills this in from the deck. Missing = 'front'.
COURT_FACING = {}


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

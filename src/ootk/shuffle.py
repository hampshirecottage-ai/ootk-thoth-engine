"""The one shuffler used by every entry point (CLI and web GUI).

Same seed -> same deck, regardless of whether the seed is given as int or str.
"""
import hashlib
import json
import random
import re

_OP_TAG = re.compile(r"^\[Op (\d+)\]")


def seed_to_int(seed) -> int:
    """Normalises any seed (1568 or "1568") to a full-width integer via SHA-256."""
    if seed is None:
        raise ValueError("A seed is required for a reproducible shuffle.")
    return int(hashlib.sha256(str(seed).encode("utf-8")).hexdigest(), 16)


def shuffle_deck(deck: list, seed) -> list:
    """Returns a new, deterministically shuffled copy of `deck`."""
    rng = random.Random(seed_to_int(seed))
    shuffled = list(deck)
    rng.shuffle(shuffled)
    return shuffled


def resolve_significator(cards, name):
    """Finds the significator card by full title, by the name after the ' - ' ('Lust' for
    'XI - Lust', 'Dominion' for '2 of Wands - Dominion') or by a pip's name before it
    ('2 of Wands')."""
    wanted = (name or "").strip().lower()
    if not wanted:
        return None
    for c in cards:
        t = c["title"].lower()
        head, _, tail = t.partition(" - ")
        if wanted in (t, tail, head if c.get("arcana_type") == "Minor" else None):
            return c
    return None


def has_significator_position(positions):
    """True when the spread's first position is the significator's (OOTK Op 1)."""
    return bool(positions) and "significator" in positions[0].lower()


def operation_number(position_name):
    """1 for an untagged position, n for a master pipeline's '[Op n] ...' position."""
    m = _OP_TAG.match(position_name or "")
    return int(m.group(1)) if m else 1


def operation_seed(seed, op_num):
    """The seed operation `op_num` shuffles with. Operation 1 (and every single spread) uses
    the seed itself, so those draws are unchanged; later operations get their own shuffle."""
    return seed if op_num == 1 else f"{seed}|op{op_num}"


def draw_spread(cards, seed, positions, sig_card=None):
    """Draws one title per position from the deck shuffled by `seed`.

    Each operation of a master pipeline (positions tagged '[Op n]') shuffles the whole deck
    again, as the Opening of the Key does, so a card can fall in several operations and the
    significator can turn up in a house, sign or decan. Within one operation no card falls
    twice. `sig_card` is pinned to position 1 only when that position is a significator
    position; it is then removed from Operation 1's deck so it cannot be drawn twice there.
    A given seed draws the same cards in the CLI and the web GUI.
    Returns (titles, pinned). Raises ValueError when the deck holds fewer cards than an
    operation needs, rather than dealing some cards twice.
    """
    pinned = bool(sig_card) and has_significator_position(positions)
    ops = []                                   # [(op_num, [position indices])] in order
    for idx, name in enumerate(positions):
        op_num = operation_number(name)
        if ops and ops[-1][0] == op_num:
            ops[-1][1].append(idx)
        else:
            ops.append((op_num, [idx]))

    titles = [None] * len(positions)
    for op_num, indices in ops:
        deck = shuffle_deck(cards, operation_seed(seed, op_num))
        if pinned and indices[0] == 0:
            deck = [c for c in deck if c["card_id"] != sig_card["card_id"]]
            titles[0] = sig_card["title"]
            indices = indices[1:]
        if len(deck) < len(indices):
            raise ValueError(f"The deck has {len(cards)} cards but this spread needs {len(positions)}. "
                             f"Load every card from database/schema.sql.")
        for card, idx in zip(deck, indices):
            titles[idx] = card["title"]
    return titles, pinned


def duplicate_in_operation(positions, titles):
    """The first title that falls twice within one operation, or None. A master pipeline
    reshuffles for each operation, so a card may repeat across operations but not inside one."""
    seen = set()
    for name, title in zip(positions, titles):
        key = (operation_number(name), (title or "").lower())
        if key in seen:
            return title
        seen.add(key)
    return None


def main():
    suits = ["Wands", "Cups", "Swords", "Disks"]
    ranks = ["Ace", "2", "3", "4", "5", "6", "7", "8", "9", "10",
             "Knight", "Queen", "Prince", "Princess"]
    deck = [f"Major {i}" for i in range(22)] + [f"{r} of {s}" for s in suits for r in ranks]

    seed = 42
    print(f"--- Shuffle Simulation (Seed: {seed}) ---")
    print("Top 5 Cards Dealt:")
    print(json.dumps(shuffle_deck(deck, seed)[:5], indent=2))


if __name__ == "__main__":
    main()

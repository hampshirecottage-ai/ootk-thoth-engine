"""The one shuffler used by every entry point (CLI, web GUI, vector_engine).

Same seed -> same deck, regardless of whether the seed is given as int or str.
"""
import hashlib
import json
import random


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

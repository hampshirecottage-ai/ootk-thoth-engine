import json
import time

class LCGPRNG:
    """Linear Congruential Generator for reproducible, seed-based PRNG."""
    def __init__(self, seed: int = None):
        self.state = seed if seed is not None else int(time.time())
        # Standard numerical parameters (Numerical Recipes LCG)
        self.a = 1664525
        self.c = 1013904223
        self.m = 2**32

    def next_float(self) -> float:
        """Returns a pseudo-random float in [0.0, 1.0)."""
        self.state = (self.a * self.state + self.c) % self.m
        return self.state / self.m

    def randint(self, min_val: int, max_val: int) -> int:
        """Returns a pseudo-random integer between min_val and max_val inclusive."""
        return min_val + int(self.next_float() * (max_val - min_val + 1))


def fisher_yates_shuffle(deck: list, prng: LCGPRNG) -> list:
    """In-place Fisher-Yates (Knuth) shuffle driven by the PRNG."""
    shuffled = deck.copy()
    n = len(shuffled)
    for i in range(n - 1, 0, -1):
        # Pick a random index from 0 to i
        j = prng.randint(0, i)
        # Swap elements at i and j
        shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
    return shuffled


def main():
    # Build standard 78-card Thoth deck baseline
    suits = ["Wands", "Cups", "Swords", "Disks"]
    ranks = ["Ace", "2", "3", "4", "5", "6", "7", "8", "9", "10", "Knight", "Queen", "Prince", "Princess"]
    majors = [f"Major {i}" for i in range(22)]
    
    deck = majors + [f"{r} of {s}" for s in suits for r in ranks]
    
    # Initialize PRNG with deterministic seed
    seed = 42
    prng = LCGPRNG(seed=seed)
    
    shuffled_deck = fisher_yates_shuffle(deck, prng)
    
    print(f"--- PRNG Fisher-Yates Simulation (Seed: {seed}) ---")
    print("Top 5 Cards Dealt:")
    print(json.dumps(shuffled_deck[:5], indent=2))

if __name__ == "__main__":
    main()

import json
import os
from prng_shuffler import LCGPRNG, fisher_yates_shuffle

def load_config(config_filename="config.json"):
    # Resolves the directory path: scripts/.. -> root -> config/config.json
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, ".."))
    config_path = os.path.join(root_dir, "config", config_filename)

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file missing: {config_path}")
    
    with open(config_path, "r") as f:
        return json.load(f)

def build_thoth_deck():
    """Generates a structured 78-card Thoth deck baseline with suit mappings."""
    suits = ["Wands", "Cups", "Swords", "Disks"]
    ranks = ["Ace", "2", "3", "4", "5", "6", "7", "8", "9", "10", "Knight", "Queen", "Prince", "Princess"]
    
    deck = []
    # Minor Arcana
    for suit in suits:
        for rank in ranks:
            deck.append({"name": f"{rank} of {suit}", "suit": suit, "type": "Minor"})
            
    # Major Arcana (Assigned baseline elemental suit mappings for dignity calculations)
    majors = [
        ("The Fool", "Swords"),        # Air
        ("The Magus", "Swords"),       # Air
        ("The Priestess", "Cups"),     # Water
        ("The Empress", "Disks"),      # Earth
        ("The Emperor", "Wands"),      # Fire
        ("The Hierophant", "Disks"),   # Earth
        ("The Lovers", "Swords"),      # Air
        ("The Chariot", "Cups"),       # Water
        ("Adjustment", "Swords"),      # Air
        ("The Hermit", "Disks"),       # Earth
        ("Fortune", "Wands"),          # Fire
        ("Lust", "Wands"),             # Fire
        ("The Hanged Man", "Cups"),    # Water
        ("Death", "Cups"),             # Water
        ("Art", "Wands"),              # Fire
        ("The Devil", "Disks"),        # Earth
        ("The Tower", "Wands"),        # Fire
        ("The Star", "Swords"),        # Air
        ("The Moon", "Cups"),          # Water
        ("The Sun", "Wands"),          # Fire
        ("Aeon", "Wands"),             # Fire
        ("The Universe", "Disks")      # Earth
    ]
    for name, suit in majors:
        deck.append({"name": name, "suit": suit, "type": "Major"})
        
    return deck

def calculate_pair_dignity(card_a, card_b, config):
    """Calculates composite vector score for a card pair using elemental interaction rules."""
    suits = config["suits"]
    matrix = config["elemental_relationships"]
    
    suit_a, suit_b = card_a["suit"], card_b["suit"]
    elem_a, elem_b = suits[suit_a]["element"], suits[suit_b]["element"]
    
    weight_a = suits[suit_a]["weight"]
    weight_b = suits[suit_b]["weight"]
    interaction = matrix[elem_a][elem_b]
    
    vector_score = (weight_a + weight_b) * interaction
    return {
        "pair": [card_a["name"], card_b["name"]],
        "elements": [elem_a, elem_b],
        "interaction_multiplier": interaction,
        "composite_vector_score": round(vector_score, 4)
    }

def run_ootk_pipeline(seed: int):
    """Executes full pipeline: PRNG Seed -> Fisher-Yates Deal -> Vector Analysis."""
    config = load_config()
    print(f"=== {config['system_name']} v{config['version']} ===")
    print(f"Initializing PRNG with Seed: {seed}")
    
    # 1. Build and Shuffle Deck
    deck = build_thoth_deck()
    prng = LCGPRNG(seed=seed)
    shuffled_deck = fisher_yates_shuffle(deck, prng)
    
    # 2. Deal Top Pair for Vector Analysis
    card_1 = shuffled_deck[0]
    card_2 = shuffled_deck[1]
    
    print(f"\nDealt Pair: '{card_1['name']}' & '{card_2['name']}'")
    
    # 3. Calculate Elemental Dignities
    result = calculate_pair_dignity(card_1, card_2, config)
    return result

if __name__ == "__main__":
    # Test execution with seed 1568
    analysis_output = run_ootk_pipeline(seed=1568)
    print("\nVector Evaluation Output:")
    print(json.dumps(analysis_output, indent=2))

import os
import sys
import json
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database Connection Configuration loaded securely from Environment Variables
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "ootk_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432))
}

# Reordered Spreads Hierarchy (12 Total Operations / Layouts)
SPREADS = {
    # --- 1. CORE & PROGRESSIVE SPREADS ---
    "1": {
        "name": "Single Card / Daily Operations",
        "positions": [
            "Core Theme / Focus"
        ]
    },
    "2": {
        "name": "Dyad (Polarity & Dynamics)",
        "positions": [
            "Active Force (Thesis)", 
            "Receptive / Resistance Force (Antithesis)"
        ]
    },
    "3": {
        "name": "Triad (Timeline & Motion)",
        "positions": [
            "Past / Root Cause", 
            "Present / Active Dynamics", 
            "Future / Manifest Result"
        ]
    },
    "4": {
        "name": "Sub-Elemental Quadrant Cross (Elemental Sub-Division)",
        "positions": [
            "1. Yod of Yod (Fire of Fire - Pure Flash)",
            "2. Heh of Yod (Water of Fire - Emotional Will)",
            "3. Vav of Yod (Air of Fire - Directed Focus)",
            "4. Heh Final of Yod (Earth of Fire - Physicalized Action)"
        ]
    },
    "5": {
        "name": "Tetragrammaton Spread (4 Elemental Vectors)",
        "positions": [
            "Atziluth / Yod (Fire - Creative Spark)", 
            "Briah / Heh (Water - Mental/Emotional Container)", 
            "Yetzirah / Vav (Air - Formative Processing)", 
            "Assiah / Heh Final (Earth - Material Result)"
        ]
    },

    # --- 2. HERMETIC & MACROCOSMIC LAYOUTS ---
    "6": {
        "name": "Hexagram Spread (Planetary Operations & Macrocosm)",
        "positions": [
            "1. Saturn (Top Apex / Form, Constraints & Karma)",
            "2. Jupiter (Right Top / Expansion, Luck & Growth)",
            "3. Mars (Right Bottom / Drive, Severity & Force)",
            "4. Venus (Bottom Apex / Harmony, Affection & Value)",
            "5. Mercury (Left Bottom / Intellect, Logic & Communication)",
            "6. Sun (Left Top / Core Vitality, Identity & Spirit)",
            "7. Moon (Center Core / Subconscious, Instinct & Foundation)"
        ]
    },
    "7": {
        "name": "Tree of Life Layout (10 Sephiroth Mapping)",
        "positions": [
            "1. Kether (Crown / Primary Impulse)",
            "2. Chokmah (Wisdom / Dynamic Force)",
            "3. Binah (Understanding / Structural Form)",
            "4. Chesed (Mercy / Expansion)",
            "5. Geburah (Severity / Action & Severity)",
            "6. Tiphareth (Beauty / Harmony & Core Self)",
            "7. Netzach (Victory / Emotions & Instinct)",
            "8. Hod (Splendor / Intellect & Logic)",
            "9. Yesod (Foundation / Subconscious & Astral)",
            "10. Malkuth (Kingdom / Manifest World)"
        ]
    },

    # --- 3. OPENING OF THE KEY (OOTK) OPERATIONS ---
    "8": {
        "name": "OOTK - First Operation (15-Card Active Heap)",
        "positions": [
            "1. Significator / Core Nature of Question",
            "2. Development of Question (Left Pair A)",
            "3. Development of Question (Left Pair B)",
            "4. Further Outcome (Right Pair A)",
            "5. Further Outcome (Right Pair B)",
            "6. Unexpected / External Factors (Center Pair A)",
            "7. Unexpected / External Factors (Center Pair B)",
            "8. Psychological / Subconscious Basis (Base Left A)",
            "9. Psychological / Subconscious Basis (Base Left B)",
            "10. Environmental / Material Basis (Base Right A)",
            "11. Environmental / Material Basis (Base Right B)",
            "12. Final Synthesis / Karma (Top Apex A)",
            "13. Final Synthesis / Karma (Top Apex B)",
            "14. Key Counter-Balance / Receptivity",
            "15. Ultimate Climax / Resolution"
        ]
    },
    "9": {
        "name": "OOTK - Second Operation (12 Astrological Houses)",
        "positions": [
            "1. First House (Ascendant / Physical Self & Vitality)",
            "2. Second House (Finances, Possessions & Values)",
            "3. Third House (Siblings, Local Travel & Mental Habits)",
            "4. Fourth House (Imum Coeli / Home, Roots & Endings)",
            "5. Fifth House (Creativity, Children & Speculation)",
            "6. Sixth House (Health, Daily Work & Service)",
            "7. Seventh House (Descendant / Partnerships & Open Enemies)",
            "8. Eighth House (Shared Assets, Death & Transformation)",
            "9. Ninth House (Higher Learning, Philosophy & Foreign Travel)",
            "10. Tenth House (Midheaven / Career, Public Standing & Authority)",
            "11. Eleventh House (Hopes, Friends & Collective Alliances)",
            "12. Twelfth House (Subconscious, Hidden Enemies & Self-Undoings)"
        ]
    },
    "10": {
        "name": "OOTK - Third Operation (12 Zodiacal Signs)",
        "positions": [
            "1. Aries (0°-30° / Cardinal Fire - Impulse)",
            "2. Taurus (0°-30° / Fixed Earth - Consolidation)",
            "3. Gemini (0°-30° / Mutable Air - Synthesis)",
            "4. Cancer (0°-30° / Cardinal Water - Enclosure)",
            "5. Leo (0°-30° / Fixed Fire - Radiance)",
            "6. Virgo (0°-30° / Mutable Earth - Analysis)",
            "7. Libra (0°-30° / Cardinal Air - Equilibrium)",
            "8. Scorpio (0°-30° / Fixed Water - Transformation)",
            "9. Sagittarius (0°-30° / Mutable Fire - Vector)",
            "10. Capricorn (0°-30° / Cardinal Earth - Structure)",
            "11. Aquarius (0°-30° / Fixed Air - Collective)",
            "12. Pisces (0°-30° / Mutable Water - Dissolution)"
        ]
    },
    "11": {
        "name": "OOTK - Fourth Operation (36 Zodiacal Decans)",
        "positions": [
            "1. Cardinal Fire (Aries I)", "2. Cardinal Fire (Aries II)", "3. Cardinal Fire (Aries III)",
            "4. Fixed Earth (Taurus I)", "5. Fixed Earth (Taurus II)", "6. Fixed Earth (Taurus III)",
            "7. Mutable Air (Gemini I)", "8. Mutable Air (Gemini II)", "9. Mutable Air (Gemini III)",
            "10. Cardinal Water (Cancer I)", "11. Cardinal Water (Cancer II)", "12. Cardinal Water (Cancer III)",
            "13. Fixed Fire (Leo I)", "14. Fixed Fire (Leo II)", "15. Fixed Fire (Leo III)",
            "16. Mutable Earth (Virgo I)", "17. Mutable Earth (Virgo II)", "18. Mutable Earth (Virgo III)",
            "19. Cardinal Air (Libra I)", "20. Cardinal Air (Libra II)", "21. Cardinal Air (Libra III)",
            "22. Fixed Water (Scorpio I)", "23. Fixed Water (Scorpio II)", "24. Fixed Water (Scorpio III)",
            "25. Mutable Fire (Sagittarius I)", "26. Mutable Fire (Sagittarius II)", "27. Mutable Fire (Sagittarius III)",
            "28. Cardinal Earth (Capricorn I)", "29. Cardinal Earth (Capricorn II)", "30. Cardinal Earth (Capricorn III)",
            "31. Fixed Air (Aquarius I)", "32. Fixed Air (Aquarius II)", "33. Fixed Air (Aquarius III)",
            "34. Mutable Water (Pisces I)", "35. Mutable Water (Pisces II)", "36. Mutable Water (Pisces III)"
        ]
    },

    # --- 4. MASTER COMPREHENSIVE PIPELINE ---
    "12": {
        "name": "Complete Opening of the Key (OOTK) - 4-Operation Master Pipeline",
        "operations": ["8", "9", "10", "11"]  # Sequences Ops 1 through 4
    }
}

def get_db_connection():
    """Establishes and returns a connection to the PostgreSQL database."""
    try:
        conn = psycopg.connect(**DB_CONFIG, row_factory=dict_row)
        return conn
    except Exception as e:
        print(f"[ERROR] Database connection failed: {e}")
        sys.exit(1)

def fetch_all_cards(conn):
    """Retrieve indexed list of all 78 cards from DB using context management."""
    with conn.cursor() as cur:
        cur.execute("SELECT card_id, title, arcana_type, key_scale FROM thoth_cards ORDER BY card_id ASC;")
        return cur.fetchall()

def fetch_card_correspondences(conn, title):
    """Fetch card details and joined 777 correspondences using context management."""
    query = """
    SELECT 
        tc.title,
        tc.arcana_type,
        tc.suit,
        tc.number_or_rank,
        tc.description,
        c.key_scale,
        c.name AS path_or_sephira,
        c.hebrew_letter,
        c.element_or_planet_or_sign AS attribution,
        c.king_scale_color,
        c.attributions
    FROM thoth_cards tc
    JOIN correspondences c ON tc.key_scale = c.key_scale
    WHERE tc.title = %s;
    """
    with conn.cursor() as cur:
        cur.execute(query, (title,))
        return cur.fetchone()

def save_spread_session(conn, spread_name, query_prompt, notes, spread_results):
    """Persists parent session metadata and child card pulls securely inside an atomic transaction block."""
    insert_session_query = """
    INSERT INTO tarot_sessions (spread_name, query_prompt, notes)
    VALUES (%s, %s, %s)
    RETURNING session_id;
    """
    
    insert_pull_query = """
    INSERT INTO session_card_pulls (session_id, position_number, position_name, card_title, key_scale)
    VALUES (%s, %s, %s, %s, %s);
    """
    
    try:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(insert_session_query, (spread_name, query_prompt, notes))
                session_id = cur.fetchone()["session_id"]
                
                for item in spread_results:
                    cur.execute(insert_pull_query, (
                        session_id,
                        item["position_number"],
                        item["position_name"],
                        item["card_data"]["title"],
                        item["card_data"]["key_scale"]
                    ))
                    
        print(f"\n[SUCCESS] Session #{session_id} and {len(spread_results)} card pulls recorded to PostgreSQL.")
    except Exception as e:
        print(f"\n[ERROR] Failed to record session to database: {e}")

def guide_ootk_preparation():
    """Provides step-by-step terminal prompts for the traditional OOTK First Operation physical setup."""
    steps = [
        ("PHASE 1: SIGNIFICATOR SELECTION", [
            "1. Select the Significator card representing the querent or core focus.",
            "2. For an active, analytical, or intellectual intent, the Knight of Swords is traditionally placed.",
            "3. Return the Significator to the full 78-card deck."
        ]),
        ("PHASE 2: SHUFFLING & INVOCATION", [
            "1. Hold the full deck in your hands.",
            "2. State the intent or question clearly, focusing on the primary dynamic.",
            "3. Shuffle the 78 cards thoroughly until you feel the sequence is randomized."
        ]),
        ("PHASE 3: THE TETRAGRAMMATON CUT", [
            "1. Place the full deck face-down on your working space.",
            "2. Cut the deck approximately in half to your left.",
            "3. Cut both of those piles in half again to your left, creating FOUR heaps in a line.",
            "4. From RIGHT to LEFT, these heaps correspond to:",
            "   - Heap 1 (Far Right) : Yod   (Fire / Atziluth - Creative Impulse)",
            "   - Heap 2             : Heh   (Water / Briah - Emotional/Mental Basis)",
            "   - Heap 3             : Vav   (Air / Yetzirah - Formative Processing)",
            "   - Heap 4 (Far Left)  : Heh-f (Earth / Assiah - Material Manifestation)"
        ]),
        ("PHASE 4: LOCATING THE ACTIVE HEAP", [
            "1. Turn over each heap face up.",
            "2. Locate which of the four heaps contains your designated Significator.",
            "3. Note the elemental quadrant it landed in (Fire, Water, Air, or Earth).",
            "4. Take that specific heap for the 15-card layout extraction."
        ]),
        ("PHASE 5: DEALING THE 15 CARDS", [
            "1. Fan the active heap face-up and locate your Significator.",
            "2. Place the Significator into Position 1 (Center/Core Focus).",
            "3. METHOD A (Static Array): Deal the next 14 consecutive cards from the heap directly into Positions 2 through 15.",
            "4. METHOD B (Traditional OOTK Counting Protocol):",
            "   - Count forward from the Significator using card weights:",
            "     * Major Arcana = 11 cards",
            "     * Court Cards  = 4 cards",
            "     * Minor Cards  = Face value (2-10)",
            "   - Extract each landed card sequentially to form the 7 active pairs + final resolution card.",
            "5. Enter each card into the CLI in position order (1 through 15)."
        ])
    ]

    print("\n" + "="*65)
    print("      OPENING OF THE KEY (OOTK) - TRADITIONAL DRAW PROTOCOL")
    print("="*65)

    for phase_title, instructions in steps:
        print(f"\n---> {phase_title}")
        for line in instructions:
            print(f"  {line}")
        input("\n[Press ENTER when you have completed this step...]")

    print("\n" + "="*65)
    print("  PHYSICAL SETUP COMPLETE. PROCEEDING TO CARD ENTRY MATRIX.")
    print("="*65 + "\n")

def analyze_elemental_balance(spread_results):
    """Calculates the dominant Liber 777 elemental vector distribution across drawn cards."""
    element_counts = {"Fire": 0, "Water": 0, "Air": 0, "Earth": 0, "Spirit": 0}
    
    element_keywords = {
        "Fire": ["fire", "aries", "leo", "sagittarius", "wands", "yod", "shin", "south"],
        "Water": ["water", "cancer", "scorpio", "pisces", "cups", "heh", "mem", "west"],
        "Air": ["air", "gemini", "libra", "aquarius", "swords", "vav", "aleph", "east"],
        "Earth": ["earth", "taurus", "virgo", "capricorn", "disks", "pentacles", "final", "tau", "north"]
    }

    for item in spread_results:
        data = item.get("card_data", {}) or {}
        
        title = str(data.get("title") or "").lower()
        suit = str(data.get("suit") or "").lower()
        arcana = str(data.get("arcana_type") or "").lower()
        attribution = str(data.get("attribution") or "").lower()
        
        attr_json = data.get("attributions") or {}
        json_str = json.dumps(attr_json).lower() if isinstance(attr_json, dict) else str(attr_json).lower()

        combined_text = f"{title} {suit} {arcana} {attribution} {json_str}"

        matched = False
        for elem, keywords in element_keywords.items():
            if any(kw in combined_text for kw in keywords):
                element_counts[elem] += 1
                matched = True
                break

        if not matched:
            element_counts["Spirit"] += 1

    print("\n" + "="*60)
    print("         LIBER 777 ELEMENTAL VECTOR ANALYSIS")
    print("="*60)
    total = sum(element_counts.values()) or 1
    for elem, count in element_counts.items():
        percentage = (count / total) * 100
        bar = "█" * int(count * 2)
        print(f"{elem:7s} | {bar:20s} {count} ({percentage:.0f}%)")
    print("="*60)

def display_card_selection(cards):
    """Print numbered list of cards for easy selection."""
    print("\n--- AVAILABLE THOTH CARDS ---")
    for idx, card in enumerate(cards, start=1):
        print(f"{idx:2d}. {card['title']} (Scale {card['key_scale']})")

def run_spread_session():
    """Main CLI Execution Loop."""
    with get_db_connection() as conn:
        cards = fetch_all_cards(conn)
        card_lookup = {str(idx): card["title"] for idx, card in enumerate(cards, start=1)}
        card_titles_set = {card["title"].lower(): card["title"] for card in cards}

        # Step 1: Select Spread Layout
        print("==================================================")
        print("       THOTH TAROT & LIBER 777 ENGINE           ")
        print("==================================================")
        print("Select a spread layout:\n")
        print("--- CORE & PROGRESSIVE SPREADS ---")
        for key in ["1", "2", "3", "4", "5"]:
            print(f" [{key:2s}] {SPREADS[key]['name']} ({len(SPREADS[key]['positions'])} cards)")
            
        print("\n--- HERMETIC & MACROCOSMIC LAYOUTS ---")
        for key in ["6", "7"]:
            print(f" [{key:2s}] {SPREADS[key]['name']} ({len(SPREADS[key]['positions'])} cards)")

        print("\n--- OPENING OF THE KEY (OOTK) OPERATIONS ---")
        for key in ["8", "9", "10", "11"]:
            print(f" [{key:2s}] {SPREADS[key]['name']} ({len(SPREADS[key]['positions'])} cards)")

        print("\n--- MASTER PIPELINE ---")
        print(f" [12] {SPREADS['12']['name']} (75 cards total)")

        spread_choice = input("\nEnter spread number (1-12): ").strip()
        selected_spread = SPREADS.get(spread_choice, SPREADS["1"])
        print(f"\n---> Selected Spread: {selected_spread['name']}\n")

        # Capture optional metadata
        query_prompt = input("Enter Query / Intent Prompt (optional, press ENTER to skip): ").strip() or None
        session_notes = input("Enter Session Notes (optional, press ENTER to skip): ").strip() or None

        spread_results = []

        # MASTER PIPELINE SELECTION (Option 12)
        if spread_choice == "12":
            target_ops = selected_spread["operations"]
            global_pos_idx = 1

            for op_key in target_ops:
                op_spread = SPREADS[op_key]
                print("\n" + "="*60)
                print(f"  EXECUTING: {op_spread['name'].upper()}")
                print("="*60)

                if op_key == "8":  # First Operation setup guide
                    guide_ootk_preparation()

                for position_name in op_spread["positions"]:
                    formatted_pos = f"[{op_spread['name'][:6]}] {position_name}"
                    print(f"\n[Card {global_pos_idx} | {formatted_pos}]")
                    
                    selected_title = None
                    while not selected_title:
                        user_input = input("Enter card index or name: ").strip()
                        if user_input in card_lookup:
                            selected_title = card_lookup[user_input]
                        elif user_input.lower() in card_titles_set:
                            selected_title = card_titles_set[user_input.lower()]
                        else:
                            print("Invalid card selection. Type 'list' or try again.")
                            if user_input.lower() == 'list':
                                display_card_selection(cards)

                    card_data = fetch_card_correspondences(conn, selected_title)
                    spread_results.append({
                        "position_number": global_pos_idx,
                        "position_name": formatted_pos,
                        "card_data": card_data
                    })
                    global_pos_idx += 1

        # SINGLE SPREAD SELECTION (Options 1 - 11)
        else:
            if spread_choice == "8":  # First Operation setup guide
                guide_ootk_preparation()

            for pos_idx, position_name in enumerate(selected_spread["positions"], start=1):
                print(f"\n[Position {pos_idx}: {position_name}]")
                
                selected_title = None
                while not selected_title:
                    user_input = input("Enter card index number (or type full name): ").strip()
                    if user_input in card_lookup:
                        selected_title = card_lookup[user_input]
                    elif user_input.lower() in card_titles_set:
                        selected_title = card_titles_set[user_input.lower()]
                    else:
                        print("Invalid card selection. Type 'list' or try again.")
                        if user_input.lower() == 'list':
                            display_card_selection(cards)

                card_data = fetch_card_correspondences(conn, selected_title)
                spread_results.append({
                    "position_number": pos_idx,
                    "position_name": position_name,
                    "card_data": card_data
                })

        # Step 4: Render Analytical Synthesis Report
        print("\n\n" + "="*60)
        print(f"         SPREAD ANALYSIS REPORT: {selected_spread['name'].upper()}")
        print("="*60)

        for item in spread_results:
            data = item["card_data"]
            attr = data.get("attributions", {}) or {}

            print(f"\nPOSITION {item['position_number']}: {item['position_name']}")
            print("-" * 50)
            print(f"Card Drawn    : {data['title']}")
            print(f"Arcana / Suit : {data['arcana_type']} | {data['suit'] or 'N/A'}")
            print(f"Key Scale     : {data['key_scale']} ({data['path_or_sephira']})")
            print(f"Hebrew Letter : {data['hebrew_letter']}")
            print(f"Attribution   : {data['attribution']}")
            print(f"Color Scale   : {data['king_scale_color']}")

        # Step 5: Master Elemental Vector Synthesis
        analyze_elemental_balance(spread_results)

        # Step 6: Save Complete Operational Sequence to DB
        save_spread_session(conn, selected_spread["name"], query_prompt, session_notes, spread_results)

if __name__ == "__main__":
    run_spread_session()

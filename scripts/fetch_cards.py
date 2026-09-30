import os
import sys
from pathlib import Path
import psycopg
from psycopg.rows import dict_row

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from src.spread_engine import DB_CONFIG

def get_thoth_cards():
    """Fetches all 78 Thoth cards ordered by card_id using DB_CONFIG."""
    query = """
        SELECT card_id, title AS card_name, key_scale 
        FROM thoth_cards 
        ORDER BY card_id ASC;
    """
    
    try:
        with psycopg.connect(**DB_CONFIG, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                return cur.fetchall()
    except psycopg.Error as e:
        print(f"[ERROR] Failed to retrieve cards from database: {e}")
        return []

if __name__ == "__main__":
    cards = get_thoth_cards()
    
    print("--- AVAILABLE THOTH CARDS ---")
    if cards:
        for card in cards:
            print(f" {card['card_id']}. {card['card_name']} (Scale {card['key_scale']})")
    else:
        print("No card data retrieved. Check database contents and table schema.")

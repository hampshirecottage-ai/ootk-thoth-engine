import os
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

load_dotenv()

DB_NAME = os.getenv("DB_NAME", "my_tarot_db")
DB_USER = os.getenv("DB_USER", "dbuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

CONN_STR = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def get_thoth_cards():
    """Fetches all 78 Thoth cards ordered by card_id."""
    # Explicitly alias 'title' to 'card_name' for Python dict key access
    query = """
        SELECT card_id, title AS card_name, key_scale 
        FROM thoth_cards 
        ORDER BY card_id ASC;
    """
    
    try:
        with psycopg.connect(CONN_STR, row_factory=dict_row) as conn:
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

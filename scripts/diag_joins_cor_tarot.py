import sys
from pathlib import Path
import psycopg
from psycopg.rows import dict_row

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.spread_engine import DB_CONFIG

def check_correspondence_join():
    try:
        conn = psycopg.connect(**DB_CONFIG, row_factory=dict_row)
        with conn.cursor() as cur:
            # Fetch first 5 joined rows
            query = """
                SELECT 
                    c.card_id, 
                    c.title, 
                    c.key_scale,
                    corr.hebrew_letter,
                    corr.element_or_planet_or_sign,
                    corr.king_scale_color
                FROM thoth_cards c
                LEFT JOIN correspondences corr ON c.key_scale = corr.key_scale
                ORDER BY c.card_id ASC
                LIMIT 5;
            """
            cur.execute(query)
            rows = cur.fetchall()
            
            print(f"Query returned {len(rows)} rows.\n")
            for row in rows:
                print(f"Card {row['card_id']}: {row['title']} (Key Scale: {row['key_scale']})")
                print(f"  └─ Hebrew: {row['hebrew_letter']} | Attrib: {row['element_or_planet_or_sign']} | Color: {row['king_scale_color']}\n")

    except Exception as e:
        print(f"❌ Error during execution: {e}")

if __name__ == "__main__":
    check_correspondence_join()

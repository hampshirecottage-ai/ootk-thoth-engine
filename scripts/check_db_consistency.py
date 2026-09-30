import sys
from pathlib import Path
import psycopg
from psycopg.rows import dict_row

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.spread_engine import DB_CONFIG

def audit_database():
    print("=== OOTK DATABASE CONSISTENCY AUDIT ===\n")
    
    try:
        conn = psycopg.connect(**DB_CONFIG, row_factory=dict_row)
    except Exception as e:
        print(f"❌ Connection Error: Could not connect to database using DB_CONFIG.\nDetails: {e}")
        return

    with conn:
        with conn.cursor() as cur:
            # 1. Total Card Count Check
            cur.execute("SELECT COUNT(*) as total FROM thoth_cards;")
            count = cur.fetchone()["total"]
            if count == 78:
                print("✅ [78/78 Cards] Total card count is complete.")
            else:
                print(f"⚠️️ [Card Count Mismatch] Found {count} cards in `thoth_cards` (expected 78).")

            # 2. Check Null Values in Critical Fields
            cur.execute("""
                SELECT card_id, title 
                FROM thoth_cards 
                WHERE title IS NULL OR key_scale IS NULL;
            """)
            null_cards = cur.fetchall()
            if not null_cards:
                print("✅ [Null Check] No missing titles or key scales.")
            else:
                print(f"❌ [Null Check Failed] Null fields found in cards: {null_cards}")

            # 3. Check Major Arcana Count (Scale 0-21)
            cur.execute("""
                SELECT COUNT(*) as count 
                FROM thoth_cards 
                WHERE key_scale::text ~ '^[0-9]+$' AND CAST(key_scale AS INTEGER) BETWEEN 0 AND 21;
            """)
            majors = cur.fetchone()["count"]
            print(f"✅ [Trumps Check] Major Arcana count: {majors} (Expected: 22)")

            # 4. ID Sequence Continuity (1 through 78)
            cur.execute("SELECT MIN(card_id) as min_id, MAX(card_id) as max_id FROM thoth_cards;")
            id_range = cur.fetchone()
            if id_range["min_id"] == 1 and id_range["max_id"] == 78:
                print("✅ [ID Sequence] `card_id` ranges properly from 1 to 78.")
            else:
                print(f"⚠️ [ID Sequence Issue] Range is {id_range['min_id']} to {id_range['max_id']}.")

            # 5. Column Verification
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'thoth_cards';
            """)
            columns = [r["column_name"] for r in cur.fetchall()]
            
            print("\nSchema Column Verification for `thoth_cards`:")
            check_cols = ["card_id", "title", "key_scale", "element", "hebrew_letter", "path_number"]
            for col in check_cols:
                status = "✅ Present" if col in columns else "⚠️️ Optional/Missing"
                print(f"  - {col}: {status}")

    print("\nAudit completed.")

if __name__ == "__main__":
    audit_database()

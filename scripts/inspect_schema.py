import sys
from pathlib import Path
import psycopg
from psycopg.rows import dict_row

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.spread_engine import DB_CONFIG

def inspect_thoth_cards_schema():
    print("=== THOTH_CARDS TABLE SCHEMA INSPECTION ===\n")
    try:
        conn = psycopg.connect(**DB_CONFIG, row_factory=dict_row)
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return

    with conn:
        with conn.cursor() as cur:
            # 1. Fetch all columns and data types for thoth_cards
            cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'thoth_cards'
                ORDER BY ordinal_position;
            """)
            columns = cur.fetchall()

            print("Current Columns in `thoth_cards`:")
            for col in columns:
                print(f"  • {col['column_name']} ({col['data_type']}) - Nullable: {col['is_nullable']}")

            # 2. Check for related correspondence tables in public schema
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name != 'thoth_cards';
            """)
            other_tables = cur.fetchall()

            print("\nOther Tables in Database:")
            if other_tables:
                for t in other_tables:
                    print(f"  • {t['table_name']}")
            else:
                print("  (None found)")

            # 3. Sample row preview
            cur.execute("SELECT * FROM thoth_cards LIMIT 1;")
            sample = cur.fetchone()
            print("\nSample Row Data (Card 1):")
            if sample:
                for k, v in sample.items():
                    print(f"  {k}: {v}")

if __name__ == "__main__":
    inspect_thoth_cards_schema()

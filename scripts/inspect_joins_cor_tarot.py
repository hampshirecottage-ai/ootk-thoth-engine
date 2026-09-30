import sys
from pathlib import Path
import psycopg
from psycopg.rows import dict_row

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.spread_engine import DB_CONFIG

def check_correspondence_join():
    conn = psycopg.connect(**DB_CONFIG, row_factory=dict_row)
    with conn.cursor() as cur:
        # Corrected Join using key_scale
        query = """
            SELECT 
                c.card_id, 
                c.title, 
                c.key_scale,
                corr.hebrew_letter,
                corr.element_or_planet_or_sign,
                corr.king_scale_color,
                corr.spatial_type,
                corr.platonic_solid,
                corr.topological_role
            FROM thoth_cards c
            LEFT JOIN correspondences corr ON c.key_scale = corr.key_scale
            WHERE c.card_id = 1;
        """
        cur.execute(query)
        sample_joined = cur.fetchone()
        
        print("✅ Successfully Joined `thoth_cards` and `correspondences` on `key_scale`!\n")
        print("Joined Correspondence Data for Card 1 (The Fool):")
        if sample_joined:
            for k, v in sample_joined.items():
                print(f"  • {k}: {v}")

if __name__ == "__main__":
    check_correspondence_join()

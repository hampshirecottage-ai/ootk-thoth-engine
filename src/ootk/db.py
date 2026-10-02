"""Database access: connection settings, card lookups and saving sessions."""
import json
import os
import sys

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

from ootk import PROJECT_ROOT as BASE_DIR
from ootk.analysis import card_is_dignified

load_dotenv()

CONFIG_PATH = BASE_DIR / "config" / "config.json"

DB_ENV_VARS = {
    "dbname": "DB_NAME", "user": "DB_USER", "password": "DB_PASSWORD",
    "host": "DB_HOST", "port": "DB_PORT",
}

def load_db_config():
    """Loads database credentials from config/config.json with environment variable overrides."""
    config = {
        "dbname": os.getenv("DB_NAME", "my_tarot_db"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", ""),
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432"))
    }
    
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                json_data = json.load(f)
                db_json = json_data.get("database", {})
                for key in config:
                    # config.json only fills a value when the matching env var is unset
                    if key in db_json and not os.getenv(DB_ENV_VARS[key]):
                        config[key] = db_json[key]
        except Exception as e:
            print(f"[WARN] Failed to read {CONFIG_PATH}: {e}")
            
    return config

DB_CONFIG = load_db_config()

def get_db_connection():
    try:
        conn = psycopg.connect(**DB_CONFIG, row_factory=dict_row)
        return conn
    except Exception as e:
        print(f"[ERROR] Database connection failed: {e}")
        sys.exit(1)

def fetch_all_cards(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT card_id, title, arcana_type, key_scale FROM thoth_cards ORDER BY card_id ASC;")
        return cur.fetchall()

def fetch_card_correspondences(conn, title, system="golden_dawn"):
    """Looks up one card's correspondences.

    GD data (spatial, platonic, colours, GD letter) joins on the card's key_scale.
    French/Egyptian data joins separately (alias cf) because the French columns are indexed
    by French card number (0-21), not by the Golden Dawn path number, and only describe the
    Majors. Majors join on thoth_cards.french_number. Minors and Courts get no French row and
    keep their GD values: rows 1-10 hold French *Major* data, so joining a Minor on its
    key_scale would hand e.g. the 9 of Cups the Hermit's path.
    """
    query = """
    SELECT
        tc.card_id,
        tc.title,
        tc.arcana_type,
        tc.suit,
        tc.number_or_rank,
        tc.description,
        tc.key_scale,
        CASE WHEN %(sys)s = 'french_egyptian' AND cf.path_or_sephira_french IS NOT NULL
             THEN cf.path_or_sephira_french ELSE c.name END AS path_or_sephira,
        CASE WHEN %(sys)s = 'french_egyptian' AND cf.hebrew_letter_french IS NOT NULL
             THEN cf.hebrew_letter_french ELSE COALESCE(c.hebrew_letter, 'N/A') END AS hebrew_letter,
        c.hebrew_letter AS gd_hebrew_letter,
        cf.hebrew_letter_french AS french_hebrew_letter,
        CASE WHEN %(sys)s = 'french_egyptian' AND cf.attribution_french IS NOT NULL
             THEN cf.attribution_french ELSE c.element_or_planet_or_sign END AS attribution,
        c.element_or_planet_or_sign AS element,
        c.king_scale_color,
        c.attributions,
        c.spatial_type,
        c.spatial_dimension,
        c.platonic_solid,
        c.solid_faces,
        c.solid_vertices,
        c.dual_solid,
        c.topological_role
    FROM thoth_cards tc
    LEFT JOIN correspondences c  ON c.key_scale = tc.key_scale
    LEFT JOIN correspondences cf ON tc.arcana_type = 'Major' AND cf.key_scale = tc.french_number
    WHERE tc.title = %(title)s;
    """
    with conn.cursor() as cur:
        cur.execute(query, {"sys": system, "title": title})
        return cur.fetchone()

def load_card_data(conn, title, system):
    """fetch_card_correspondences with guards.

    A title with no thoth_cards row aborts cleanly instead of crashing later on card_data['title'].
    A card whose key_scale has no correspondences row is allowed through (its fields come back
    empty) but is flagged on stderr, so it never reaches the saved report unnoticed.
    Messages go to stderr so they don't land in a piped/saved report.
    """
    card_data = fetch_card_correspondences(conn, title, system=system)
    if card_data is None:
        print(f"[ERROR] No thoth_cards row found for '{title}'. Check the thoth_cards table.",
              file=sys.stderr)
        sys.exit(1)
    if card_data.get("path_or_sephira") is None and card_data.get("king_scale_color") is None:
        print(f"[WARN] '{title}' (key_scale {card_data.get('key_scale')}) has no correspondences row; "
              f"its path, attribution and geometry will be empty.", file=sys.stderr)
    return card_data

def save_spread_session(conn, spread_name, query_prompt, notes, significator, spread_results, dignity_matrix=None):
    insert_session_query = """
    INSERT INTO tarot_sessions (operation_type, significator, notes)
    VALUES (%s, %s, %s)
    RETURNING session_id;
    """
    insert_spread_query = """
    INSERT INTO spread_pulls (session_id, spread_name, pull_order)
    VALUES (%s, %s, %s)
    RETURNING spread_id;
    """
    insert_pull_query = """
    INSERT INTO session_card_pulls (session_id, spread_id, card_id, position_index, is_dignified, notes)
    VALUES (%s, %s, %s, %s, %s, %s);
    """
    
    full_notes = f"Prompt: {query_prompt} | Notes: {notes}" if query_prompt and notes else (query_prompt or notes)
    
    try:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(insert_session_query, ('OOTK', significator, full_notes))
                session_id = cur.fetchone()["session_id"]
                
                cur.execute(insert_spread_query, (session_id, spread_name, 1))
                spread_id = cur.fetchone()["spread_id"]
                
                for idx, item in enumerate(spread_results):
                    card_data = item["card_data"]
                    cur.execute(insert_pull_query, (
                        session_id,
                        spread_id,
                        card_data["card_id"],
                        item["position_number"],
                        card_is_dignified(idx, dignity_matrix),
                        item["position_name"]
                    ))
                    
        print(f"\n[SUCCESS] Session #{session_id} (Spread #{spread_id}) and {len(spread_results)} card pulls recorded to my_tarot_db.")
        return session_id
    except Exception as e:
        print(f"\n[ERROR] Failed to record session to database: {e}")
        return None

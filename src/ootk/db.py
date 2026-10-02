"""Database access: connection settings, card lookups and saving sessions."""
import json
import os
import sys

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

from ootk import PROJECT_ROOT as BASE_DIR
from ootk.analysis import apply_card_solid, card_is_dignified, WITHHELD_MAX, withheld_summary

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

def fetch_cards_correspondences(conn, titles, system="golden_dawn"):
    """Looks up the correspondences of many cards in one query; returns {title: row}.

    Titles with no thoth_cards row are simply absent from the result.

    GD data (spatial type, cube position, colours, GD letter) joins on the card's key_scale.
    French/Egyptian data joins separately (alias cf) because the French columns are indexed
    by French card number (0-21), not by the Golden Dawn path number, and only describe the
    Majors. Majors join on thoth_cards.french_number. Minors and Courts get no French row and
    keep their GD values: rows 1-10 hold French *Major* data, so joining a Minor on its
    key_scale would hand e.g. the 9 of Cups the Hermit's path.

    Under French/Egyptian a Major's letter geometry (spatial type, cube position, King Scale
    colour) comes from the path that carries its French letter (alias g, via cf.french_path),
    so the Sefer Yetzirah classification matches the letter shown.

    What belongs to the card rather than the letter comes from the card in both systems:
    under Golden Dawn the attribution is thoth_cards.attribution (the Major's sign, planet or
    element, the pip's decan, the court's span), and the Platonic solid follows the card's
    element (analysis.apply_card_solid). That keeps the Thoth swap whole: the Emperor sits on
    Tzaddi but stays Aries, Fire and a Tetrahedron.
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
             THEN cf.attribution_french
             ELSE COALESCE(tc.attribution, c.element_or_planet_or_sign) END AS attribution,
        c.element_or_planet_or_sign AS element,
        CASE WHEN g.key_scale IS NOT NULL THEN g.king_scale_color ELSE c.king_scale_color END AS king_scale_color,
        c.attributions,
        CASE WHEN g.key_scale IS NOT NULL THEN g.spatial_type ELSE c.spatial_type END AS spatial_type,
        CASE WHEN g.key_scale IS NOT NULL THEN g.spatial_dimension ELSE c.spatial_dimension END AS spatial_dimension,
        tc.attribution AS card_attribution
    FROM thoth_cards tc
    LEFT JOIN correspondences c  ON c.key_scale = tc.key_scale
    LEFT JOIN correspondences cf ON tc.arcana_type = 'Major' AND cf.key_scale = tc.french_number
    LEFT JOIN correspondences g  ON %(sys)s = 'french_egyptian' AND g.key_scale = cf.french_path
    WHERE tc.title = ANY(%(titles)s);
    """
    try:
        with conn.cursor() as cur:
            cur.execute(query, {"sys": system, "titles": list(titles)})
            rows = cur.fetchall()
    except psycopg.errors.UndefinedColumn as e:
        print(f"[ERROR] {e.diag.message_primary}. The database predates the correspondence fixes: "
              f"run psql -d <db> -f database/migrations/fix_correspondences.sql", file=sys.stderr)
        sys.exit(1)
    stale = [r["title"] for r in rows if r["arcana_type"] == "Major" and not r["card_attribution"]]
    if stale:
        print(f"[WARN] {len(stale)} Major(s) have no thoth_cards.attribution, so their Attribution "
              f"shows the letter's triplicity rulers: run psql -d <db> -f "
              f"database/migrations/fix_trump_attributions.sql", file=sys.stderr)
    return {row["title"]: apply_card_solid(row) for row in rows}

def fetch_card_correspondences(conn, title, system="golden_dawn"):
    """One card's correspondences (see fetch_cards_correspondences), or None."""
    return fetch_cards_correspondences(conn, [title], system=system).get(title)

def load_withheld(conn, deck, drawn_titles, system="golden_dawn"):
    """analysis.withheld_summary for a draw from `deck` (fetch_all_cards rows), or None."""
    if len(deck) - len(set(drawn_titles)) > WITHHELD_MAX:
        return None                       # skip the whole-deck query when nothing is listed
    rows = fetch_cards_correspondences(conn, [c["title"] for c in deck], system=system)
    return withheld_summary([rows[c["title"]] for c in deck if c["title"] in rows], drawn_titles)

def load_cards_data(conn, titles, system):
    """fetch_cards_correspondences with guards; returns rows in the order of `titles`.

    A title with no thoth_cards row aborts cleanly instead of crashing later on card_data['title'].
    A card whose key_scale has no correspondences row is allowed through (its fields come back
    empty) but is flagged on stderr, so it never reaches the saved report unnoticed.
    Messages go to stderr so they don't land in a piped/saved report.
    """
    rows = fetch_cards_correspondences(conn, titles, system=system)
    loaded = []
    for title in titles:
        card_data = rows.get(title)
        if card_data is None:
            print(f"[ERROR] No thoth_cards row found for '{title}'. Check the thoth_cards table.",
                  file=sys.stderr)
            sys.exit(1)
        if card_data.get("path_or_sephira") is None and card_data.get("king_scale_color") is None:
            print(f"[WARN] '{title}' (key_scale {card_data.get('key_scale')}) has no correspondences row; "
                  f"its path, attribution and geometry will be empty.", file=sys.stderr)
        loaded.append(card_data)
    return loaded

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
                
                cur.executemany(insert_pull_query, [
                    (
                        session_id,
                        spread_id,
                        item["card_data"]["card_id"],
                        item["position_number"],
                        card_is_dignified(idx, dignity_matrix),
                        item["position_name"]
                    )
                    for idx, item in enumerate(spread_results)
                ])
                    
        print(f"\n[SUCCESS] Session #{session_id} (Spread #{spread_id}) and {len(spread_results)} card pulls recorded to my_tarot_db.")
        return session_id
    except Exception as e:
        print(f"\n[ERROR] Failed to record session to database: {e}")
        return None

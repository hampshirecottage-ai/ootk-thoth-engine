#!/usr/bin/env python3
"""Database inspection helpers for the OOTK engine.

Replaces check_db_consistency.py, inspect_schema.py, inspect_joins_cor_tarot.py
and diag_joins_cor_tarot.py.

Usage (from the project root):
    python scripts/db_inspect.py audit                  # consistency checks, exit 1 on failure
    python scripts/db_inspect.py schema                 # thoth_cards columns, tables, sample row
    python scripts/db_inspect.py joins                  # first 5 cards joined to correspondences
    python scripts/db_inspect.py joins --card-id 1      # one card, every joined column
    python scripts/db_inspect.py joins --limit 20
"""
import argparse
import sys

import psycopg
from psycopg.rows import dict_row

from ootk.db import DB_CONFIG

EXPECTED_TABLES = {
    "thoth_cards": ["card_id", "title", "arcana_type", "suit", "number_or_rank", "key_scale", "description",
                    "french_number"],
    "correspondences": [
        "key_scale", "name", "hebrew_letter", "element_or_planet_or_sign", "king_scale_color",
        "hebrew_letter_french", "spatial_type", "platonic_solid", "topological_role",
    ],
    "spread_position_geometry": ["spread_key", "position_index", "position_name", "pos_x", "pos_y", "pos_z"],
    "tarot_sessions": ["session_id", "created_at", "operation_type", "significator"],
    "spread_pulls": ["spread_id", "session_id", "spread_name", "pull_order"],
    "session_card_pulls": ["pull_id", "session_id", "spread_id", "card_id", "position_index"],
}
EXPECTED_ARCANA = {"Major": 22, "Court": 16, "Minor": 40}


def connect():
    try:
        return psycopg.connect(**DB_CONFIG, row_factory=dict_row)
    except Exception as e:
        who = f"{DB_CONFIG.get('user')}@{DB_CONFIG.get('host')}/{DB_CONFIG.get('dbname')}"
        print(f"❌ Could not connect as {who}: {e}")
        print("   Check DB_USER / DB_NAME in .env (the user must be an existing Postgres role).")
        sys.exit(2)


def audit(_args):
    print("=== OOTK DATABASE CONSISTENCY AUDIT ===\n")
    failures = 0

    def ok(msg):
        print(f"✅ {msg}")

    def bad(msg):
        nonlocal failures
        failures += 1
        print(f"❌ {msg}")

    with connect() as conn, conn.cursor() as cur:
        # 1. Tables and columns exist
        cur.execute("SELECT table_name, column_name FROM information_schema.columns WHERE table_schema = 'public'")
        have = {}
        for r in cur.fetchall():
            have.setdefault(r["table_name"], set()).add(r["column_name"])
        for table, cols in EXPECTED_TABLES.items():
            if table not in have:
                bad(f"[Schema] table `{table}` is missing")
                continue
            missing = [c for c in cols if c not in have[table]]
            if missing:
                bad(f"[Schema] `{table}` is missing columns: {', '.join(missing)}")
            else:
                ok(f"[Schema] `{table}` has all expected columns")
        if "thoth_cards" not in have or "correspondences" not in have:
            print("\nCannot continue: core tables missing.")
            return 1

        # 2. Card count and id continuity
        cur.execute("SELECT COUNT(*) AS n, COUNT(DISTINCT card_id) AS ids, MIN(card_id) AS lo, MAX(card_id) AS hi FROM thoth_cards")
        r = cur.fetchone()
        if r["n"] == 78:
            ok("[Cards] 78/78 cards present")
        else:
            bad(f"[Cards] found {r['n']} cards (expected 78)")
        if (r["lo"], r["hi"], r["ids"]) == (1, 78, 78):
            ok("[IDs] card_id runs 1-78 with no gaps or duplicates")
        else:
            bad(f"[IDs] card_id range is {r['lo']}-{r['hi']} with {r['ids']} distinct ids")

        # 3. Arcana split (by arcana_type; key_scale 0-21 also matches minor cards)
        cur.execute("SELECT arcana_type, COUNT(*) AS n FROM thoth_cards GROUP BY arcana_type")
        got = {r["arcana_type"]: r["n"] for r in cur.fetchall()}
        if got == EXPECTED_ARCANA:
            ok("[Arcana] 22 Major / 16 Court / 40 Minor")
        else:
            bad(f"[Arcana] got {got}, expected {EXPECTED_ARCANA}")

        # 4. Nulls in critical fields
        cur.execute("SELECT card_id, title FROM thoth_cards WHERE title IS NULL OR key_scale IS NULL OR arcana_type IS NULL")
        nulls = cur.fetchall()
        if nulls:
            bad(f"[Nulls] cards with missing title/key_scale/arcana_type: {[n['card_id'] for n in nulls]}")
        else:
            ok("[Nulls] no missing titles, key scales or arcana types")

        # 5. Every card resolves to a correspondence row
        cur.execute("""
            SELECT c.card_id, c.title FROM thoth_cards c
            LEFT JOIN correspondences r ON c.key_scale = r.key_scale
            WHERE r.key_scale IS NULL ORDER BY c.card_id
        """)
        orphans = cur.fetchall()
        if orphans:
            bad(f"[Join] {len(orphans)} cards have no correspondence row: "
                f"{', '.join(o['title'] for o in orphans[:5])}{' ...' if len(orphans) > 5 else ''}")
        else:
            ok("[Join] every card matches a correspondence row on key_scale")

        # 6. Spread geometry present
        cur.execute("SELECT COUNT(*) AS n, COUNT(DISTINCT spread_key) AS spreads FROM spread_position_geometry")
        r = cur.fetchone()
        if r["n"]:
            ok(f"[Geometry] {r['n']} positions across {r['spreads']} spreads")
        else:
            bad("[Geometry] spread_position_geometry is empty")

    print(f"\nAudit completed: {failures} failure(s).")
    return 1 if failures else 0


def schema(_args):
    print("=== DATABASE SCHEMA INSPECTION ===\n")
    with connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT column_name, data_type, is_nullable FROM information_schema.columns
            WHERE table_name = 'thoth_cards' ORDER BY ordinal_position
        """)
        print("Columns in `thoth_cards`:")
        for c in cur.fetchall():
            print(f"  • {c['column_name']} ({c['data_type']}) - nullable: {c['is_nullable']}")

        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name <> 'thoth_cards' ORDER BY table_name
        """)
        print("\nOther tables:")
        tables = cur.fetchall()
        for t in tables:
            print(f"  • {t['table_name']}")
        if not tables:
            print("  (none found)")

        cur.execute("SELECT * FROM thoth_cards ORDER BY card_id LIMIT 1")
        sample = cur.fetchone()
        print("\nSample row (first card):")
        for k, v in (sample or {}).items():
            print(f"  {k}: {v}")
    return 0


def joins(args):
    with connect() as conn, conn.cursor() as cur:
        where, params = ("WHERE c.card_id = %s", (args.card_id,)) if args.card_id else ("", ())
        cur.execute(f"""
            SELECT c.card_id, c.title, c.key_scale,
                   r.hebrew_letter, r.element_or_planet_or_sign, r.king_scale_color,
                   r.spatial_type, r.platonic_solid, r.topological_role
            FROM thoth_cards c
            LEFT JOIN correspondences r ON c.key_scale = r.key_scale
            {where}
            ORDER BY c.card_id
            LIMIT %s
        """, params + (args.limit,))
        rows = cur.fetchall()
        if not rows:
            print("No matching cards.")
            return 1
        print(f"{len(rows)} card(s), joined on key_scale:\n")
        for row in rows:
            print(f"Card {row['card_id']}: {row['title']} (key_scale {row['key_scale']})")
            if args.card_id:
                for k, v in row.items():
                    print(f"  • {k}: {v}")
            else:
                print(f"  └─ Hebrew: {row['hebrew_letter']} | Attrib: {row['element_or_planet_or_sign']} "
                      f"| Color: {row['king_scale_color']}")
            print()
    return 0


def main():
    parser = argparse.ArgumentParser(description="OOTK database inspection helpers")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("audit", help="consistency checks (exit 1 on any failure)").set_defaults(func=audit)
    sub.add_parser("schema", help="show thoth_cards columns, other tables, a sample row").set_defaults(func=schema)
    p = sub.add_parser("joins", help="show cards joined to correspondences")
    p.add_argument("--card-id", type=int, help="show every joined column for one card")
    p.add_argument("--limit", type=int, default=5, help="rows to show (default 5)")
    p.set_defaults(func=joins)
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()

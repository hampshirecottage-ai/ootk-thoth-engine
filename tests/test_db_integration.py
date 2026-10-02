"""Runs the real SQL against a real database built from database/schema.sql.

Skipped unless OOTK_TEST_DB=1, so the default suite stays database-free. To run:
    createdb ootk_test && psql -d ootk_test -f database/schema.sql
    OOTK_TEST_DB=1 DB_NAME=ootk_test python -m pytest tests/test_db_integration.py -v
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

pytestmark = pytest.mark.skipif(os.getenv("OOTK_TEST_DB") != "1",
                                reason="set OOTK_TEST_DB=1 to run against a real database")


@pytest.fixture(scope="module")
def conn():
    from src import spread_engine as se
    with se.get_db_connection() as c:
        yield c


def fetch(conn, title, system):
    from src import spread_engine as se
    return se.fetch_card_correspondences(conn, title, system=system)


@pytest.mark.parametrize("system", ["golden_dawn", "french_egyptian"])
def test_every_card_resolves(conn, system):
    from src import spread_engine as se
    titles = [c["title"] for c in se.fetch_all_cards(conn)]
    assert len(titles) == 78
    assert all(fetch(conn, t, system) for t in titles)


def test_french_mapping_leaves_minors_on_their_sephira(conn):
    gd = fetch(conn, "9 of Cups - Happiness", "golden_dawn")
    fr = fetch(conn, "9 of Cups - Happiness", "french_egyptian")
    for key in ("path_or_sephira", "hebrew_letter", "attribution"):
        assert fr[key] == gd[key], key
    assert "Teth" not in str(fr["hebrew_letter"])          # not the Hermit's French letter


@pytest.mark.parametrize("title,letter", [
    ("0 - The Fool", "Shin"), ("I - The Magus", "Aleph"), ("XI - Lust", "Cheth"),
    ("VIII - Adjustment", "Kaph"), ("XXI - The Universe", "Tav"),
])
def test_french_mapping_for_majors(conn, title, letter):
    assert letter in fetch(conn, title, "french_egyptian")["hebrew_letter"]


def test_auto_framework_has_sephirothic_data_on_golden_dawn(conn):
    from src import spread_engine as se
    titles = [c["title"] for c in se.fetch_all_cards(conn)][:62]   # Majors + Minors
    results = [{"position_number": i + 1, "position_name": f"P{i+1}",
                "card_data": fetch(conn, t, "golden_dawn")} for i, t in enumerate(titles)]
    _name, basis = se.evaluate_macro_framework(results)
    assert "n=62" in basis

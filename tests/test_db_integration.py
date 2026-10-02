"""Runs the real SQL against a real database built from database/schema.sql.

Skipped unless OOTK_TEST_DB=1, so the default suite stays database-free. To run:
    createdb ootk_test && psql -d ootk_test -f database/schema.sql
    OOTK_TEST_DB=1 DB_NAME=ootk_test python -m pytest tests/test_db_integration.py -v
"""
import os
import re

import pytest

from ootk import analysis, db

pytestmark = pytest.mark.skipif(os.getenv("OOTK_TEST_DB") != "1",
                                reason="set OOTK_TEST_DB=1 to run against a real database")


@pytest.fixture(scope="module")
def conn():
    with db.get_db_connection() as c:
        yield c


def fetch(conn, title, system):
    return db.fetch_card_correspondences(conn, title, system=system)


@pytest.mark.parametrize("system", ["golden_dawn", "french_egyptian"])
def test_every_card_resolves(conn, system):
    titles = [c["title"] for c in db.fetch_all_cards(conn)]
    assert len(titles) == 78
    assert all(fetch(conn, t, system) for t in titles)


def test_french_mapping_leaves_minors_on_their_sephira(conn):
    gd = fetch(conn, "9 of Cups - Happiness", "golden_dawn")
    fr = fetch(conn, "9 of Cups - Happiness", "french_egyptian")
    for key in ("path_or_sephira", "hebrew_letter", "attribution"):
        assert fr[key] == gd[key], key
    assert "Teth" not in str(fr["hebrew_letter"])          # not the Hermit's French letter


@pytest.mark.parametrize("title,letter", [
    ("0 - The Fool", "Shin"), ("I - The Magus", "Aleph"), ("XI - Lust", "Kaph"),
    ("VIII - Adjustment", "Cheth"), ("XXI - The Universe", "Tav"),
])
def test_french_mapping_for_majors(conn, title, letter):
    assert letter in fetch(conn, title, "french_egyptian")["hebrew_letter"]


def test_auto_framework_has_sephirothic_data_on_golden_dawn(conn):
    titles = [c["title"] for c in db.fetch_all_cards(conn)][:62]   # Majors + Minors
    results = [{"position_number": i + 1, "position_name": f"P{i+1}",
                "card_data": fetch(conn, t, "golden_dawn")} for i, t in enumerate(titles)]
    _name, basis = analysis.evaluate_macro_framework(results)
    assert "n=62" in basis


SY_CLASS = {
    **{l: "Mother_Axis" for l in ("Aleph", "Mem", "Shin")},
    **{l: "Double_Direction" for l in ("Beth", "Gimel", "Daleth", "Kaph", "Peh", "Resh", "Tav")},
    **{l: "Simple_Edge" for l in ("Heh", "Vav", "Zain", "Cheth", "Teth", "Yod", "Lamed", "Nun",
                                    "Samekh", "Ayin", "Tzaddi", "Qoph")},
}
SEPHIRA_NAMES = {v: k for k, v in analysis.SEPHIROTH_RANKS.items()}


def majors(conn):
    return [c["title"] for c in db.fetch_all_cards(conn)][:22]


def test_french_geometry_follows_the_french_letter(conn):
    for title in majors(conn):
        card = fetch(conn, title, "french_egyptian")
        letter = card["hebrew_letter"].split(" ")[0]
        assert card["spatial_type"] == SY_CLASS[letter], (title, letter, card["spatial_type"])


def test_french_path_labels_match_the_tree(conn):
    for title in majors(conn):
        label = fetch(conn, title, "french_egyptian")["path_or_sephira"]   # 'Path 21 (Chesed-Netzach)'
        num, a, b = re.match(r"Path (\d+) \((\w+)-(\w+)\)", label).groups()
        ends = {SEPHIRA_NAMES[n] for n in analysis.GD_PATH_ENDPOINTS[int(num)]}
        assert {a.lower(), b.lower()} == ends, (title, label)


@pytest.mark.parametrize("system", ["golden_dawn", "french_egyptian"])
def test_no_placeholder_attributions(conn, system):
    for c in db.fetch_all_cards(conn):
        attr = fetch(conn, c["title"], system)["attribution"]
        assert attr and attr != "...", c["title"]


@pytest.mark.parametrize("title,attr", [
    ("6 of Disks - Success", "Moon in Taurus"), ("5 of Cups - Disappointment", "Mars in Scorpio"),
    ("3 of Cups - Abundance", "Mercury in Cancer"), ("Ace of Wands", "Root of the Powers of Fire"),
])
def test_pip_decans(conn, title, attr):
    for system in ("golden_dawn", "french_egyptian"):
        assert fetch(conn, title, system)["attribution"] == attr


@pytest.mark.parametrize("title,letter", [
    ("Knight of Wands", "Samekh"), ("Queen of Wands", "Tzaddi"), ("Prince of Wands", "Teth"),
    ("Knight of Cups", "Qoph"), ("Queen of Cups", "Cheth"), ("Prince of Cups", "Nun"),
    ("Princess of Cups", "Mem"), ("Prince of Swords", "Hé"), ("Princess of Swords", "Aleph"),
])
def test_court_signs(conn, title, letter):
    assert letter in fetch(conn, title, "golden_dawn")["hebrew_letter"]


def test_batched_lookup_matches_single_lookups(conn):
    titles = [c["title"] for c in db.fetch_all_cards(conn)]
    for system in ("golden_dawn", "french_egyptian"):
        batch = db.fetch_cards_correspondences(conn, titles, system=system)
        assert len(batch) == 78
        for t in titles[::7]:
            assert batch[t] == db.fetch_card_correspondences(conn, t, system=system)
    ordered = db.load_cards_data(conn, [titles[5], titles[0], titles[5]], "golden_dawn")
    assert [r["title"] for r in ordered] == [titles[5], titles[0], titles[5]]


# ---------- reading accuracy ----------

@pytest.mark.parametrize("title,attribution,element,solid", [
    ("IV - The Emperor", "Aries", "Fire", "Tetrahedron"),       # Thoth: on Tzaddi, still Aries
    ("XVII - The Star", "Aquarius", "Air", "Octahedron"),       # Thoth: on Heh, still Aquarius
    ("XI - Lust", "Leo", "Fire", "Tetrahedron"),
    ("XIII - Death", "Scorpio", "Water", "Icosahedron"),
])
def test_trump_attribution_element_and_solid_come_from_the_card(conn, title, attribution, element, solid):
    card = fetch(conn, title, "golden_dawn")
    assert card["attribution"] == attribution
    assert analysis.derive_primary_element(card) == element
    assert card["platonic_solid"] == solid


def test_emperor_keeps_its_letters_cube_edge(conn):
    emperor = fetch(conn, "IV - The Emperor", "golden_dawn")
    assert "Tzaddi" in emperor["hebrew_letter"] and emperor["spatial_dimension"] == "Upper-South Edge"


@pytest.mark.parametrize("system", ["golden_dawn", "french_egyptian"])
def test_every_solid_agrees_with_the_element_count(conn, system):
    for title in [c["title"] for c in db.fetch_all_cards(conn)]:
        card = fetch(conn, title, system)
        solid = card["platonic_solid"]
        if card["arcana_type"] == "Major" and analysis.major_name(card) in analysis.PLANETARY_MAJORS:
            assert solid == "Dodecahedron", title
        else:
            assert solid == analysis.ELEMENT_SOLIDS[analysis.derive_primary_element(card)], title


def test_every_major_has_a_card_attribution(conn):
    for title in majors(conn):
        card = fetch(conn, title, "golden_dawn")
        assert card["card_attribution"] and " - " not in card["attribution"], title


def test_universe_path_is_the_cross(conn):
    assert fetch(conn, "XXI - The Universe", "golden_dawn")["path_or_sephira"] == "Cross"


def test_decan_labels_match_the_pip_attributions(conn):
    from ootk.spreads import SPREADS
    for label in SPREADS["11"]["positions"]:
        decan, pip = re.fullmatch(r"Decan \d+: (.+) \((.+)\)", label).groups()
        card = next(c for c in db.fetch_all_cards(conn) if c["title"].startswith(pip + " - "))
        assert fetch(conn, card["title"], "golden_dawn")["attribution"] == decan, label


def test_withheld_lists_the_cards_left_out(conn):
    deck = db.fetch_all_cards(conn)
    drawn = [c["title"] for c in deck][3:]
    w = db.load_withheld(conn, deck, drawn)
    assert [r["title"] for r in w["cards"]] == [c["title"] for c in deck[:3]]
    assert w["deck_elements"] == {"Fire": 21, "Water": 19, "Air": 19, "Earth": 19, "Spirit": 0}

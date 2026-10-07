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


@pytest.mark.parametrize("system", ["thoth", "golden_dawn", "french_egyptian"])
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


@pytest.mark.parametrize("system", ["thoth", "golden_dawn", "french_egyptian"])
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
    assert letter in fetch(conn, title, "thoth")["hebrew_letter"]


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


# Paul Case's Cube of Space (Sepher Yetzirah 4:3 and 5:2), keyed by the card under Golden Dawn,
# where each trump sits on its own letter.
CUBE_OF_SPACE = {
    "0 - The Fool": "Vertical Axis (above to below)", "XII - The Hanged Man": "Horizontal Axis (east to west)",
    "XX - The Aeon": "Longitudinal Axis (north to south)",
    "I - The Magus": "Up (Zenith)", "II - The Priestess": "Down (Nadir)", "III - The Empress": "East",
    "X - Fortune": "West", "XVI - The Tower": "North", "XIX - The Sun": "South",
    "XXI - The Universe": "Center Core (Holy Temple)",
    "IV - The Emperor": "North-East Edge", "V - The Hierophant": "South-East Edge",
    "VI - The Lovers": "Upper-East Edge", "VII - The Chariot": "Lower-East Edge",
    "XI - Lust": "Upper-North Edge", "IX - The Hermit": "Lower-North Edge",
    "VIII - Adjustment": "North-West Edge", "XIII - Death": "South-West Edge",
    "XIV - Art": "Upper-West Edge", "XV - The Devil": "Lower-West Edge",
    "XVII - The Star": "Upper-South Edge", "XVIII - The Moon": "Lower-South Edge",
}


def test_every_trump_sits_on_its_cube_of_space_place(conn):
    assert len(CUBE_OF_SPACE) == 22
    for title, place in CUBE_OF_SPACE.items():
        assert fetch(conn, title, "golden_dawn")["spatial_dimension"] == place, title


def test_emperor_keeps_its_letters_cube_edge(conn):
    emperor = fetch(conn, "IV - The Emperor", "thoth")
    assert "Tzaddi" in emperor["hebrew_letter"] and emperor["spatial_dimension"] == "Upper-South Edge"


@pytest.mark.parametrize("title,thoth_letter,gd_letter,gd_edge,gd_key_scale", [
    ("IV - The Emperor", "Tzaddi", "Hé", "North-East Edge", 15),
    ("XVII - The Star", "Hé", "Tzaddi", "Upper-South Edge", 28),
    ("Queen of Wands", "Tzaddi", "Hé", "North-East Edge", 15),     # follows the Emperor
    ("Prince of Swords", "Hé", "Tzaddi", "Upper-South Edge", 28),  # follows the Star
])
def test_golden_dawn_undoes_the_thoth_swap(conn, title, thoth_letter, gd_letter, gd_edge, gd_key_scale):
    thoth, gd = fetch(conn, title, "thoth"), fetch(conn, title, "golden_dawn")
    assert thoth_letter in thoth["hebrew_letter"] and gd_letter in gd["hebrew_letter"]
    assert gd["spatial_dimension"] == gd_edge and gd["key_scale"] == gd_key_scale
    # The card keeps its own sign and solid; only the letter and its geometry move.
    assert gd["attribution"] == thoth["attribution"]
    assert gd["platonic_solid"] == thoth["platonic_solid"]
    for card in (thoth, gd):        # the comparison line names both letters in either system
        assert thoth_letter in card["thoth_hebrew_letter"] and gd_letter in card["gd_hebrew_letter"]


def test_only_the_swapped_cards_differ_between_thoth_and_golden_dawn(conn):
    titles = [c["title"] for c in db.fetch_all_cards(conn)]
    thoth = db.fetch_cards_correspondences(conn, titles, system="thoth")
    gd = db.fetch_cards_correspondences(conn, titles, system="golden_dawn")
    differ = {t for t in titles if thoth[t]["hebrew_letter"] != gd[t]["hebrew_letter"]}
    assert differ == {"IV - The Emperor", "XVII - The Star", "Queen of Wands", "Prince of Swords"}


@pytest.mark.parametrize("system", ["thoth", "golden_dawn", "french_egyptian"])
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


@pytest.mark.parametrize("system", ["thoth", "golden_dawn", "french_egyptian"])
def test_own_place_chance_uses_the_real_decks_own_places(conn, system):
    """The exact chance assumes 36 pips (one per decan) and, per sign, a Trump, three pips and a
    Knight, Queen or Prince. The database's cards must give exactly those places."""
    from collections import Counter
    titles = [c["title"] for c in db.fetch_all_cards(conn)]
    rows = db.fetch_cards_correspondences(conn, titles, system=system).values()
    for kind in ("decan", "sign", "house"):
        places = Counter(analysis.own_places(r, kind) for r in rows)
        del places[frozenset()]
        assert places == Counter(analysis._deck_homes(kind)), kind
    pip = analysis.own_places(fetch(conn, "2 of Wands - Dominion", system), "decan")
    assert pip == {0}                                             # Decan 1: Mars in Aries
    assert analysis.card_home(fetch(conn, "Knight of Swords", system))[0] == 2    # Gemini, Zain


def test_withheld_lists_the_cards_left_out(conn):
    deck = db.fetch_all_cards(conn)
    drawn = [c["title"] for c in deck][3:]
    w = db.load_withheld(conn, deck, drawn)
    assert [r["title"] for r in w["cards"]] == [c["title"] for c in deck[:3]]
    assert w["deck_elements"] == {"Fire": 21, "Water": 19, "Air": 19, "Earth": 19, "Spirit": 0}


def test_french_attribution_is_the_cards_own(conn):
    # French rows give the card's own sign, planet or element ('Justice / Libra' for Libra);
    # only the Fool reads differently ('Unnumbered / Primeval Spirit').
    for title in majors(conn)[1:]:
        gd = fetch(conn, title, "golden_dawn")["attribution"]
        fr = fetch(conn, title, "french_egyptian")["attribution"]
        assert gd in fr, (title, gd, fr)


def test_atlas_frames_match_the_database(conn):
    """The Tree's paths and Book T's decans written in ootk.atlas agree with the tables."""
    from ootk import atlas
    with conn.cursor() as cur:
        cur.execute("SELECT key_scale, attributions->>'tree_of_life' AS t FROM correspondences "
                    "WHERE key_scale BETWEEN 11 AND 32")
        for r in cur.fetchall():
            assert r["t"] == "%d to %d" % atlas.PATH_ENDS[r["key_scale"]], r["key_scale"]
    titles = {c["title"] for c in db.fetch_all_cards(conn)}
    rows = db.fetch_cards_correspondences(conn, titles)
    pips = {(r["suit"], int(r["number_or_rank"])): r["attribution"] for r in rows.values()
            if r["arcana_type"] == "Minor" and r["number_or_rank"] not in ("1", "Ace")}
    for i in range(36):
        assert pips[atlas.decan_pip(i)] == f"{atlas.DECAN_RULERS[i]} in {atlas.SIGNS[i // 3]}", i


@pytest.mark.parametrize("system", ["thoth", "golden_dawn", "french_egyptian"])
def test_deck_atlas_places_every_card(conn, system):
    from ootk import atlas
    deck = db.fetch_all_cards(conn)
    rows = db.fetch_cards_correspondences(conn, [c["title"] for c in deck], system=system)
    a = atlas.deck_atlas([rows[c["title"]] for c in deck])
    majors = [c for c in a["cards"] if c["kind"] == "Major"]
    assert sorted(c["tree"]["path"] for c in majors) == list(range(11, 33))
    assert len({c["cube"]["place"] for c in majors}) == 22
    courts = [c for c in a["cards"] if c["kind"] == "Court" and c["zodiac"]["arcs"][0][1] - c["zodiac"]["arcs"][0][0] == 30]
    assert sorted(d for c in courts for d in c["zodiac"]["decans"]) == list(range(36))   # spans tile the circle
    assert all(c["solid"] for c in a["cards"]) and len(a["signs"]) == 12
    assert all(s["carrier"].get("place") for s in a["signs"])


def test_report_link_lookup_uses_its_index(conn):
    with conn.cursor() as cur:
        cur.execute("SET LOCAL enable_seqscan = off")
        cur.execute("EXPLAIN SELECT session_id FROM tarot_sessions WHERE report_settings->>'link' = %s",
                    ("x",))
        plan = " ".join(r["QUERY PLAN"] for r in cur.fetchall())
    conn.rollback()
    assert "idx_sessions_report_link" in plan


def test_report_link_lookup_returns_when_the_reading_was_saved(conn):
    with conn.transaction(force_rollback=True):
        with conn.cursor() as cur:
            cur.execute("INSERT INTO tarot_sessions (operation_type, report_settings) "
                        "VALUES ('OOTK', %s) RETURNING session_id;",
                        (db.Jsonb({"link": "L" * 22, "spread_key": "12"}),))
            session_id = cur.fetchone()["session_id"]
        found_id, settings = db.load_report_by_link(conn, "L" * 22)
        assert found_id == session_id and settings["spread_key"] == "12"
        assert settings["saved_at"].tzinfo is not None              # comparable with web.RESHUFFLE_SINCE
        assert db.load_report_by_link(conn, "M" * 22) is None


def test_testimonials_one_per_session_and_only_approved_shown(conn):
    with conn.transaction(force_rollback=True):
        with conn.cursor() as cur:
            cur.execute("DELETE FROM testimonials;")
        assert db.save_testimonial(conn, "s" * 22, "Ann", "Clear.", "UA/1", None) is True
        assert db.save_testimonial(conn, "s" * 22, "Ann", "Again.", "UA/1", None) is False
        assert db.session_has_testimonial(conn, "s" * 22)
        assert not db.session_has_testimonial(conn, "t" * 22)
        assert db.approved_testimonials(conn) == []
        with conn.cursor() as cur:
            cur.execute("UPDATE testimonials SET approved = true;")
        assert db.approved_testimonials(conn) == [{"name": "Ann", "body": "Clear."}]


def test_admin_testimonial_queries(conn):
    with conn.transaction(force_rollback=True):
        with conn.cursor() as cur:
            cur.execute("DELETE FROM testimonials;")
        db.save_testimonial(conn, "a" * 22, "", "One.", None, None)
        db.save_testimonial(conn, "b" * 22, "Bo", "Two.", None, None)
        rows = db.list_testimonials(conn)
        assert [r["body"] for r in rows] == ["Two.", "One."] and "session_id" not in rows[0]
        db.set_testimonial_approved(conn, rows[1]["testimonial_id"], True)
        assert db.approved_testimonials(conn) == [{"name": None, "body": "One."}]
        assert [r["body"] for r in db.list_testimonials(conn)] == ["Two.", "One."]   # waiting first
        db.delete_testimonial(conn, rows[0]["testimonial_id"])
        assert [r["body"] for r in db.list_testimonials(conn)] == ["One."]


@pytest.mark.parametrize("spread, significator, mapping, framework", [
    ("3", None, "thoth", "auto"),
    ("7", None, "golden_dawn", "life_path"),
    ("12", "Queen of Cups", "thoth", "auto"),
    ("12", "Prince of Swords", "french_egyptian", "post_mortem"),
])
def test_command_line_and_web_give_the_same_prompt(monkeypatch, spread, significator, mapping, framework):
    """Both entry points go through report.analyze_reading, so one seed gives one prompt."""
    from ootk import cli, web

    seen = {}
    real = cli.analyze_reading
    monkeypatch.setattr(cli, "analyze_reading", lambda *a, **k: seen.setdefault("r", real(*a, **k)))
    monkeypatch.setattr(cli, "save_spread_session", lambda *a, **k: None)
    argv = ["ootk", "--spread", spread, "--seed", "4242", "--topic", "parity check",
            "--mapping", mapping, "--framework", framework]
    if significator:
        argv += ["--significator", significator]
    monkeypatch.setattr("sys.argv", argv)
    cli.run_spread_session()

    settings = {"spread_key": spread, "seed": "4242", "topic": "parity check", "significator": significator or "",
                "framework": framework, "mapping_system": mapping}
    deck = web.reference_deck()
    titles, label = web.seeded_draw(deck, "4242", spread, significator or "")
    assert web.run_reading(settings, titles, label, deck)["analytical_prompt"] == seen["r"]["analytical_prompt"]


def test_command_line_reading_saves_without_report_settings(conn):
    card = db.fetch_all_cards(conn)[0]
    results = [{"card_data": card, "position_number": 1, "position_name": "Card"}]
    session_id = db.save_spread_session(conn, "Single Card", "q", "n", card["title"], results)
    with conn.cursor() as cur:
        cur.execute("SELECT report_settings, notes FROM tarot_sessions WHERE session_id = %s", (session_id,))
        row = cur.fetchone()
        cur.execute("DELETE FROM tarot_sessions WHERE session_id = %s", (session_id,))
    conn.commit()
    assert row == {"report_settings": None, "notes": "Prompt: q | Notes: n"}


def test_schema_has_no_stored_solids_or_unused_geometry(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'correspondences'")
        columns = {r["column_name"] for r in cur.fetchall()}
        cur.execute("SELECT to_regclass('public.spread_position_geometry') AS t")
        assert cur.fetchone()["t"] is None
    assert not columns & {"platonic_solid", "solid_faces", "solid_vertices", "dual_solid", "topological_role"}


def test_a_save_blocked_by_a_lock_gives_up(conn, monkeypatch):
    """A save waiting on a lock (a migration holds one while it runs) fails after
    DB_QUERY_TIMEOUT instead of holding a reading slot until the lock is released."""
    import time
    monkeypatch.setattr(db, "DB_QUERY_TIMEOUT", 1)
    card = db.fetch_all_cards(conn)[0]
    results = [{"card_data": card, "position_number": 1, "position_name": "Card"}]
    with db.get_db_connection() as locker:
        locker.execute("LOCK TABLE tarot_sessions IN ACCESS EXCLUSIVE MODE")
        with db.get_db_connection() as saver:
            started = time.monotonic()
            session_id = db.save_spread_session(saver, "Single Card", "q", "n", card["title"], results)
            waited = time.monotonic() - started
        locker.rollback()
    assert session_id is None and waited < 5

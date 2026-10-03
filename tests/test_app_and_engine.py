"""Run from the project root:  python -m pytest -v
Needs: pip install -e ".[dev]"
"""
import json
from contextlib import nullcontext
from pathlib import Path

import pytest

from ootk import analysis, db, report, shuffle, spreads
from ootk import web as app_module
from fastapi.testclient import TestClient


# ---------- helpers ----------

def fake_card(title, suit="Wands", arcana="Minor", attribution="Fire"):
    return {
        "card_id": 1, "title": title, "arcana_type": arcana, "suit": suit,
        "number_or_rank": "2", "description": "", "key_scale": 1,
        "path_or_sephira": "Chokmah", "hebrew_letter": "Yod",
        "gd_hebrew_letter": "Yod", "french_hebrew_letter": "Yod",
        "attribution": attribution, "element": attribution,
        "king_scale_color": "Red", "attributions": "",
        "spatial_type": "Simple_Edge", "spatial_dimension": "Edge",
        "platonic_solid": "Tetrahedron", "solid_faces": 4, "solid_vertices": 4,
        "dual_solid": "Tetrahedron", "topological_role": "Node",
    }


@pytest.fixture
def client(monkeypatch):
    """App client with the database fully mocked out."""
    saved = {}
    monkeypatch.setattr(app_module, "get_db_connection", lambda: nullcontext(object()))
    monkeypatch.setattr(app_module, "fetch_all_cards", lambda conn: [])
    lookups = []

    def fake_fetch(conn, titles, system="golden_dawn"):
        lookups.append(list(titles))
        return {t: fake_card(t) for t in titles}

    monkeypatch.setattr(app_module, "fetch_cards_correspondences", fake_fetch)

    def fake_save(conn, spread_name, query_prompt, notes, significator, results, dignity_matrix=None,
                  report_settings=None):
        saved.update(spread=spread_name, topic=query_prompt, notes=notes,
                     significator=significator, n=len(results), dignity=dignity_matrix,
                     report_settings=json.loads(json.dumps(report_settings)))
        saved["count"] = saved.get("count", 0) + 1
        return 99

    monkeypatch.setattr(app_module, "save_spread_session", fake_save)
    monkeypatch.setattr(app_module, "load_report_settings",
                        lambda conn, sid: dict(saved["report_settings"]) if sid == 99 and saved else None)
    monkeypatch.setattr(app_module, "load_withheld",
                        lambda conn, deck, titles, system="golden_dawn": analysis.withheld_summary(
                            [fake_card(c["title"]) for c in deck], titles))
    c = TestClient(app_module.app)
    c.saved = saved
    c.lookups = lookups
    return c


def post(client, follow=True, **over):
    """Posts the form; by default follows the redirect to the report, as a browser does."""
    data = {"spread_key": "3", "selected_cards": "A,B,C", "topic": "t"}
    data.update(over)
    return client.post("/generate_report", data=data, follow_redirects=follow)


# ---------- app: validation ----------

@pytest.mark.parametrize("over", [
    {"spread_key": "99"},
    {"mapping_system": "nonsense"},
    {"framework": "nonsense"},
    {"selected_cards": "A,B"},        # wrong count for spread 3
    {"selected_cards": "A,a,C"},      # duplicate (case-insensitive)
    {"selected_cards": " , "},        # nothing usable
])
def test_bad_input_returns_400(client, over):
    assert post(client, **over).status_code == 400


def test_unknown_card_returns_400(client, monkeypatch):
    monkeypatch.setattr(app_module, "fetch_cards_correspondences",
                        lambda conn, titles, system="golden_dawn": {"A": fake_card("A")})
    r = post(client)
    assert r.status_code == 400
    assert "'B'" in r.json()["detail"]                    # first missing title, in draw order


# ---------- app: happy paths ----------

def test_index_renders(client):
    assert client.get("/").status_code == 200


def test_password_off_by_default(client, monkeypatch):
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    assert client.get("/").status_code == 200


def test_password_required_when_set(client, monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "s3cret")
    r = client.get("/")
    assert r.status_code == 401
    assert r.headers["www-authenticate"].startswith("Basic")
    assert client.get("/", auth=("anyone", "wrong")).status_code == 401
    assert client.get("/static/js/index.js").status_code == 401
    assert client.get("/", auth=("anyone", "s3cret")).status_code == 200


# ---------- app: web performance ----------

def test_pages_are_compressed(client):
    for headers, encoding in [({"Accept-Encoding": "br, gzip"}, "br"),
                              ({"Accept-Encoding": "gzip"}, "gzip"),
                              ({"Accept-Encoding": "identity"}, None)]:
        r = client.get("/", headers=headers)
        assert r.status_code == 200 and "<!DOCTYPE html>" in r.text      # httpx decodes br/gzip
        assert r.headers.get("content-encoding") == encoding
        assert "Accept-Encoding" in r.headers["vary"]


def test_catalog_uses_versioned_webp_thumbnails(client, monkeypatch):
    monkeypatch.setattr(app_module, "fetch_all_cards", lambda conn: [{"title": "X - Fortune"}])
    html = client.get("/").text
    assert '/static/cards/thumb/x---fortune.webp?v=' in html
    assert 'loading="lazy"' in html and ".jpg" not in html
    assert 'src="/static/js/index.js?v=' in html and "defer" in html


def test_static_cache_headers(client):
    url = app_module.static_url("js/index.js")
    r = client.get(url, headers={"Accept-Encoding": "gzip"})
    assert r.status_code == 200
    assert r.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert r.headers["content-encoding"] == "gzip"
    assert client.get("/static/js/index.js").headers["cache-control"] == "public, max-age=3600"
    image = client.get(app_module.card_image_url("X - Fortune"), headers={"Accept-Encoding": "gzip"})
    assert image.headers["content-type"] == "image/webp"
    assert "content-encoding" not in image.headers                         # already compressed


def test_report_happy_path_and_raw_storage(client):
    r = post(client, topic="Love & War <3", significator="O'Brien")
    assert r.status_code == 200
    # stored raw, not pre-escaped (no double escaping)
    assert client.saved["topic"] == "Love & War <3"
    # hand-picked triad: no significator position, so the typed significator is not claimed
    assert client.saved["significator"] == "None (spread has no significator position)"
    assert client.saved["n"] == 3
    assert client.saved["dignity"] is not None      # dignity matrix reaches the DB layer


def test_manual_significator_is_the_card_in_position_1(client):
    cards = ",".join(["O'Brien"] + [f"Card {i}" for i in range(14)])
    assert post(client, spread_key="8", selected_cards=cards, significator="Knight of Swords").status_code == 200
    assert client.saved["significator"] == "O'Brien"                  # stored raw, not escaped


def test_form_errors_render_a_page_with_a_way_back(client):
    r = post(client, selected_cards="A,B")
    assert r.status_code == 400 and r.json()["detail"].startswith("'Triad")   # API clients: JSON
    r = client.post("/generate_report", headers={"Accept": "text/html"},
                    data={"spread_key": "<b>", "selected_cards": "A,B,C"})
    assert r.status_code == 400 and "text/html" in r.headers["content-type"]   # browsers: a page
    assert "Back to settings" in r.text
    assert "&lt;b&gt;" in r.text and "<b>" not in r.text                        # escaped


def test_spread_12_needs_75_cards(client):
    cards = ",".join(f"Card {i}" for i in range(75))
    assert post(client, follow=False, spread_key="12", selected_cards=cards).status_code == 303
    assert len(client.lookups) == 1 and len(client.lookups[0]) == 75   # one batched lookup
    assert post(client, spread_key="12", selected_cards="A,B,C").status_code == 400


def test_report_shows_framework_name_not_tuple(client):
    r = post(client)
    assert r.status_code == 200
    assert "Incarnational Life Path" in client.saved["notes"]
    assert "('" not in client.saved["notes"]                 # not a stringified tuple
    assert "Framework Basis" in r.text


def test_gui_dignities_stay_inside_each_operation(client):
    cards = ",".join(f"Card {i}" for i in range(75))
    assert post(client, spread_key="12", selected_cards=cards).status_code == 200
    pairs = {(d["from_index"], d["to_index"]) for d in client.saved["dignity"]}
    # Op boundaries for spread 12: 15 | 12 | 12 | 36 cards
    for last_of_op in (14, 26, 38):
        assert (last_of_op, last_of_op + 1) not in pairs
    # Consecutive pairs inside each op, plus the closing pair of the three wheels.
    assert len(pairs) == 75 - 4 + 3


def test_every_spread_position_count_matches(client):
    for key, spread in spreads.SPREADS.items():
        n = len(spreads.spread_positions(key))
        cards = ",".join(f"Card {i}" for i in range(n))
        assert post(client, spread_key=key, selected_cards=cards).status_code == 200, key


# ---------- engine: pure functions ----------

def results_for(*cards):
    return [{"position_number": i + 1, "position_name": f"P{i+1}", "card_data": c}
            for i, c in enumerate(cards)]


def test_dignity_scores():
    fire = fake_card("F", "Wands", attribution="Fire")
    air = fake_card("A", "Swords", attribution="Air")
    water = fake_card("W", "Cups", attribution="Water")
    earth = fake_card("E", "Disks", attribution="Earth")
    score = lambda a, b: analysis.calculate_elemental_dignities(results_for(a, b))[0]["score"]
    # Book T: same element strong, opposites contrary, every other pair friendly.
    assert score(fire, fire) == 2
    assert score(fire, water) == -2
    assert score(air, earth) == -2
    for a, b in [(fire, air), (fire, earth), (water, air), (water, earth)]:
        assert score(a, b) == score(b, a) == 1


@pytest.mark.parametrize("angle,aspect", [
    (0, "Conjunction"), (60, "Sextile"), (90, "Square"),
    (120, "Trine"), (180, "Opposition"), (150, "Quincunx"), (210.1, "Quincunx"),
    (30, "Minor"), (163.8, "Minor"),
])
def test_spatial_aspects(angle, aspect):
    assert aspect in analysis.calculate_spatial_aspect(angle)[0]


def test_shuffle_is_deterministic_and_a_permutation():
    from ootk.shuffle import shuffle_deck
    deck = [{"title": f"C{i}"} for i in range(78)]
    a = shuffle_deck(deck, "1568")
    b = shuffle_deck(deck, "1568")
    c = shuffle_deck(deck, "1569")
    assert a == b
    assert a != c
    assert sorted(x["title"] for x in a) == sorted(x["title"] for x in deck)
    assert deck[0]["title"] == "C0"  # input list is not mutated


def test_int_and_str_seed_give_same_deck():
    from ootk.shuffle import shuffle_deck
    deck = list(range(78))
    assert shuffle_deck(deck, 1568) == shuffle_deck(deck, "1568")


def test_seed_required():
    from ootk.shuffle import shuffle_deck
    with pytest.raises(ValueError):
        shuffle_deck([1, 2, 3], None)


def test_all_entry_points_use_the_single_shuffler():
    """The CLI and the web GUI must draw with ootk.shuffle.draw_spread, not their own."""
    from ootk import cli
    assert cli.draw_spread is shuffle.draw_spread
    assert app_module.draw_spread is shuffle.draw_spread


def test_draw_spread_pins_significator_and_keeps_seed_order():
    deck = [{"card_id": i, "title": f"C{i}"} for i in range(78)]
    sig = deck[10]
    positions = spreads.spread_positions("12")
    titles, pinned = shuffle.draw_spread(deck, "1568", positions, sig)
    assert pinned and titles[0] == "C10"
    assert len(titles) == 75 and len(set(titles)) == 75          # no card drawn twice
    rest = [c["title"] for c in shuffle.shuffle_deck(deck, "1568") if c["card_id"] != 10]
    assert titles[1:] == rest[:74]                                # same order the CLI always drew
    # No significator position: nothing is pinned and the shuffled deck is dealt from the top.
    titles, pinned = shuffle.draw_spread(deck, "1568", spreads.spread_positions("3"), sig)
    assert not pinned
    assert titles == [c["title"] for c in shuffle.shuffle_deck(deck, "1568")][:3]


# ---------- engine: fixed bugs (regression tests) ----------

def test_env_overrides_config_dbname(tmp_path, monkeypatch):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"database": {"dbname": "fromjson", "host": "jsonhost"}}))
    monkeypatch.setattr(db, "CONFIG_PATH", cfg)
    monkeypatch.setenv("DB_NAME", "fromenv")
    monkeypatch.delenv("DB_HOST", raising=False)
    out = db.load_db_config()
    assert out["dbname"] == "fromenv"      # env wins
    assert out["host"] == "jsonhost"       # json fills what env leaves unset


@pytest.mark.parametrize("card,expected", [
    ({"title": "The Empress", "suit": None, "attribution": "Venus"}, "Earth"),
    ({"title": "The Magus", "suit": None, "attribution": "Mercury"}, "Air"),
    ({"title": "The Priestess", "suit": None, "attribution": "Moon"}, "Water"),
    ({"title": "The Tower", "suit": None, "attribution": "Mars"}, "Fire"),
    ({"title": "The Emperor", "suit": None, "attribution": "Aries"}, "Fire"),
    ({"title": "Ace of Cups", "suit": "Cups", "attribution": "Fire"}, "Water"),  # suit wins
    ({"title": "Chair Card", "suit": None, "attribution": "Chair"}, "Spirit"),   # no substring match
])
def test_derive_primary_element(card, expected):
    assert analysis.derive_primary_element(card) == expected


def test_spatial_empty_for_uncoordinated_spreads():
    cards = [fake_card(f"C{i}") for i in range(4)]
    for key in ("7", "9", "11", "12"):
        assert analysis.analyze_spatial_vectors(results_for(*cards), key) == []


def test_spatial_centre_node_has_no_fake_aspect():
    cards = [fake_card(f"C{i}") for i in range(3)]
    out = analysis.analyze_spatial_vectors(results_for(*cards), "3")
    assert [o["aspect"] for o in out] == ["Centre Node", "Centre Node"]
    assert all(o["score_modifier"] == 0 for o in out)


def test_spatial_hexagram_uses_real_angles():
    cards = [fake_card(f"C{i}") for i in range(7)]
    out = analysis.analyze_spatial_vectors(results_for(*cards), "6")
    assert out[0]["aspect"].startswith("Sextile")          # apex -> right-top: 60 degrees
    assert out[-1]["aspect"] == "Centre Node"              # last pair touches the centre card


def test_card_is_dignified():
    matrix = [{"score": 2, "from_index": 0, "to_index": 1},
              {"score": -2, "from_index": 1, "to_index": 2},
              {"score": -2, "from_index": 2, "to_index": 3}]
    assert analysis.card_is_dignified(0, matrix) is True     # +2
    assert analysis.card_is_dignified(1, matrix) is True     # +2 + -2 = 0
    assert analysis.card_is_dignified(2, matrix) is False    # -4
    assert analysis.card_is_dignified(3, matrix) is False    # -2
    assert analysis.card_is_dignified(0, []) is True         # single card


# ---------- report round-trip: engine -> HTML -> view_output ----------

def build_report(tmp_path, monkeypatch, topic="Love & War <3", pos_prefix="[Op 1] "):
    monkeypatch.setattr(report, "BASE_DIR", tmp_path)
    cards = [fake_card("A", "Wands", attribution="Fire"),
             fake_card("B", "Swords", attribution="Air"),
             fake_card("C", "Cups", attribution="Water")]
    results = [{"position_number": i + 1, "position_name": f"{pos_prefix}Pos {i+1}", "card_data": c}
               for i, c in enumerate(cards)]
    counts = analysis.analyze_elemental_balance(results)
    dignity = analysis.calculate_elemental_dignities(results)
    spatial = analysis.analyze_spatial_vectors(results, "3")
    sdist, sdet = analysis.analyze_hebrew_spatial_distribution(results)
    solids, topo, duals = analysis.analyze_platonic_topology(results)
    framework, basis = analysis.evaluate_macro_framework(results)
    prompt = report.build_analytical_prompt("Triad <test>", topic, "Knight of Swords", "1568", results, counts,
                                        dignity, spatial, sdist, sdet, solids, topo, duals, framework,
                                        framework_basis=basis)
    report.generate_html_output(7, "Triad <test>", topic, prompt)
    return prompt, tmp_path / "output" / "ootk_output_7.html"


def load_view_output():
    import importlib.util
    path = Path(__file__).resolve().parent.parent / "scripts" / "view_output.py"
    spec = importlib.util.spec_from_file_location("view_output", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_html_export_escapes_user_text(tmp_path, monkeypatch):
    _, html_path = build_report(tmp_path, monkeypatch, topic="<script>alert(1)</script> & more")
    text = html_path.read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in text
    assert "&lt;script&gt;" in text


def test_view_output_roundtrip_and_all_sections(tmp_path, monkeypatch):
    import io
    from rich.console import Console
    prompt, html_path = build_report(tmp_path, monkeypatch)
    vo = load_view_output()

    raw = vo.parse_html_report(html_path)
    assert raw == prompt                                   # lossless round trip, incl. & < >

    vo.console = Console(record=True, width=200, file=io.StringIO())
    vo.render_rich_report(raw, html_path.name)
    out = vo.console.export_text()
    for expected in ("Elemental Vector Distribution", "Hebrew Letter Spatial Dimensions",
                     "Platonic Solid Topology", "Pairwise Elemental Dignity Interactions",
                     "Spatial & Geometric Vector Analysis", "Card Spread Matrix",
                     "Knight of Swords", "[Op 1] Pos 1"):   # bracket text survives Rich markup
        assert expected in out, expected


def test_view_output_recognises_sections_by_title_not_number():
    vo = load_view_output()
    assert vo.section_kind("## 4. PAIRWISE ELEMENTAL DIGNITY INTERACTIONS\n* x") == "dignity"
    assert vo.section_kind("## 9. PAIRWISE ELEMENTAL DIGNITY INTERACTIONS\n* x") == "dignity"
    assert vo.section_kind("## 7. SYNTHESIS & INTERPRETATION INSTRUCTIONS FOR LLM") is None


# ---------- macro framework: Sephirothic ranks ----------

@pytest.mark.parametrize("card,expected", [
    ({"arcana_type": "Minor", "key_scale": 2, "path_or_sephira": "Wisdom"}, 2.0),      # GD Sephira, English name
    ({"arcana_type": "Major", "key_scale": 19, "path_or_sephira": "Serpent"}, 4.5),    # GD path 19: Chesed-Geburah
    ({"arcana_type": "Major", "key_scale": 19,
      "path_or_sephira": "Path 18 (Chesed-Geburah)"}, 4.5),                            # French text wins
    ({"arcana_type": "Major", "key_scale": 11,
      "path_or_sephira": "Path 21 (Geburah-Tiphareth)"}, 5.5),
    ({"arcana_type": "Court", "key_scale": 11, "path_or_sephira": "Ox"}, None),        # Courts have no place
    ({}, None),
])
def test_card_sephirothic_rank(card, expected):
    assert analysis.card_sephirothic_rank(card) == expected


def test_auto_framework_sees_golden_dawn_cards():
    """GD rows only carry English names; the auto framework must still find them."""
    names = ["Crown", "Wisdom", "Understanding", "Mercy", "Strength",
             "Beauty", "Victory", "Splendour", "Foundation", "Kingdom"]
    cards = [dict(fake_card(f"C{i}"), key_scale=i + 1, path_or_sephira=n) for i, n in enumerate(names)]
    name, basis = analysis.evaluate_macro_framework(results_for(*cards))
    assert name.startswith("1. Divine Light Flow")       # ranks 1..10 in order = descent
    assert "n=10" in basis


def test_spirit_bearing_cards():
    cards = [
        {"title": "0 - The Fool", "arcana_type": "Major", "hebrew_letter": "Shin (ש)", "attribution": "x"},
        {"title": "XX - The Aeon", "arcana_type": "Major", "hebrew_letter": "Resh (ר)", "attribution": "Fire / Spirit"},
        {"title": "Princess of Wands", "arcana_type": "Court", "hebrew_letter": "ש (Shin)", "attribution": "x"},
        {"title": "XIX - The Sun", "arcana_type": "Major", "hebrew_letter": "Qoph (ק)", "attribution": "Sun"},
    ]
    results = [{"position_number": i + 1, "card_data": c} for i, c in enumerate(cards)]
    assert analysis.spirit_bearing_cards(results) == [(1, "0 - The Fool"), (2, "XX - The Aeon")]


def test_minor_spatial_letter_is_labelled_as_sephira():
    card = {"title": "6 of Disks - Success", "arcana_type": "Minor", "suit": "Disks",
            "hebrew_letter": "תִּפְאֶרֶת (Tiphareth)", "path_or_sephira": "Beauty"}
    _dist, details = analysis.analyze_hebrew_spatial_distribution([{"position_number": 1, "card_data": card}])
    assert details[0]["letter"].startswith("none - Sephira")


# ---------- shared scoring rules ----------

def test_every_module_scores_aspects_the_same_way():
    """Layout, ring and decan aspects all take their score and wording from ootk.rules."""
    from ootk import decans, rules
    for aspect in rules.ASPECTS:
        label, nature, score = analysis.calculate_spatial_aspect(aspect.angle)
        assert (label, nature, score) == (rules.aspect_label(aspect), aspect.nature, aspect.score)
    for short, label, angle, nature, score in spreads.RING_ASPECTS:
        a = rules.ASPECTS_BY_NAME[short]
        assert (label, angle, nature, score) == (rules.aspect_label(a), a.angle, a.nature, a.score)
    r = decans.evaluate_decan_aspect("2 of Wands", "2 of Swords")   # 5 deg vs 185 deg
    assert r["aspect_name"] == "Opposition"
    assert r["composite_score"] == rules.ASPECTS_BY_NAME["Opposition"].score + r["planetary_synergy"]


@pytest.mark.parametrize("angle,expected", [
    (15, "Conjunction"), (16, None), (50, "Sextile"), (100, "Square"),
    (145, "Quincunx"), (165, "Opposition"), (195, "Opposition"),
])
def test_layout_orbs_unchanged(angle, expected):
    from ootk import rules
    hit = rules.find_aspect(angle, "layout")
    assert (hit.name if hit else None) == expected


# ---------- web GUI: seeded draws, output formats, report view ----------

DECK = [{"card_id": i, "title": f"Card {i}", "arcana_type": "Minor", "key_scale": 1} for i in range(77)] + \
       [{"card_id": 77, "title": "Knight of Swords", "arcana_type": "Court", "key_scale": 1}]


@pytest.fixture
def seeded_client(client, monkeypatch):
    monkeypatch.setattr(app_module, "fetch_all_cards", lambda conn: DECK)
    return client


def test_seed_mode_draws_like_the_cli(seeded_client):
    positions = spreads.spread_positions("12")
    expected, _ = shuffle.draw_spread(DECK, "1568", positions, DECK[77])
    r = post(seeded_client, spread_key="12", draw_mode="seed", seed="1568", selected_cards="")
    assert r.status_code == 200
    assert seeded_client.lookups[-1] == expected
    assert "1568" in r.text and "ootk --spread 12 --seed 1568" in r.text
    assert "PRNG Seed: 1568" in seeded_client.saved["notes"]
    assert seeded_client.saved["significator"] == "Knight of Swords"


def test_seed_mode_same_seed_same_cards(seeded_client):
    for seed in ("42", "42", "43"):
        post(seeded_client, follow=False, spread_key="8", draw_mode="seed", seed=seed)
    a, b, c = seeded_client.lookups[-3:]
    assert a == b and a != c


def test_blank_seed_gets_a_new_seed_shown_on_the_report(seeded_client):
    r = post(seeded_client, spread_key="3", draw_mode="seed", seed="")
    assert r.status_code == 200
    seed = seeded_client.saved["notes"].split("PRNG Seed: ")[1].split(" |")[0]
    assert seed.isdigit() and f'id="seedValue">{seed}<' in r.text


def test_seed_mode_unknown_significator_is_400(seeded_client):
    assert post(seeded_client, draw_mode="seed", seed="1", significator="Nobody").status_code == 400


@pytest.mark.parametrize("over", [{"draw_mode": "nonsense"}, {"output_format": "pdf"}])
def test_bad_settings_return_400(client, over):
    assert post(client, **over).status_code == 400


def test_markdown_output_is_a_download(client):
    r = post(client, output_format="markdown")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/markdown")
    assert "attachment" in r.headers["content-disposition"]
    assert r.text.startswith("# HERMETIC ANALYTICAL REPORT")


def test_report_leads_with_summary_and_collapses_operations(client):
    cards = ",".join(f"Card {i}" for i in range(75))
    r = post(client, spread_key="12", selected_cards=cards)
    text = r.text
    assert text.index('id="summary"') < text.index('id="op1"')
    for op in ("op1", "op2", "op3", "op4"):
        assert f'<details class="section" id="{op}" >' in text      # closed until clicked
    assert text.count('class="aspect-line') > 0
    assert 'id="filters"' in text


def test_index_lists_master_pipeline_positions(client):
    r = client.get("/")
    assert r.status_code == 200
    assert '"12": ["[Op 1] 1. Significator' in r.text                # 75 slots, not 1


def test_spatial_pairs_carry_card_indices_inside_their_operation():
    cards = [fake_card(f"C{i}") for i in range(75)]
    results = [{"position_number": i + 1, "position_name": p, "card_data": c}
               for i, (p, c) in enumerate(zip(spreads.spread_positions("12"), cards))]
    bounds = [(0, 15), (15, 27), (27, 39), (39, 75)]
    for s in analysis.analyze_spatial_vectors(results, "12"):
        assert any(lo <= s["from_index"] < s["to_index"] < hi for lo, hi in bounds)
        assert s["aspect_name"] in (None, "Conjunction", "Sextile", "Square", "Trine", "Quincunx", "Opposition")


def test_report_view_draws_every_operation():
    from ootk import visual
    cards = [fake_card(f"C{i}") for i in range(75)]
    results = [{"position_number": i + 1, "position_name": p, "card_data": c}
               for i, (p, c) in enumerate(zip(spreads.spread_positions("12"), cards))]
    dignity = analysis.calculate_elemental_dignities(results, "12")
    spatial = analysis.analyze_spatial_vectors(results, "12")
    view = visual.build_report_view("12", results, analysis.analyze_elemental_balance(results),
                                    dignity, spatial, "3. Life Path", "auto")
    segs = view["segments"]
    assert [s["drawing"]["kind"] for s in segs] == ["layout", "wheel", "wheel", "wheel"]
    assert [len(s["drawing"]["slots"]) for s in segs] == [15, 12, 12, 36]
    assert sum(len(s["drawing"]["lines"]) for s in segs) == len(spatial) == view["aspects"]["total"]
    # Ring aspects: each of 36 decans has 1 opposition, 2 squares, 2 trines, 2 sextiles.
    assert len(segs[3]["aspects"]) == 36 * 7 // 2
    strong = {a["type"] for s in segs for a in s["aspects"] if a["strong"]}
    assert strong <= {"Conjunction", "Square", "Trine"}
    assert view["headline"]


def test_report_view_without_layout_falls_back_to_a_row():
    from ootk import visual
    cards = [fake_card(f"C{i}") for i in range(10)]
    results = results_for(*cards)
    view = visual.build_report_view("7", results, analysis.analyze_elemental_balance(results),
                                    analysis.calculate_elemental_dignities(results, "7"), [], "x", "y")
    assert view["segments"][0]["drawing"]["kind"] == "row"


@pytest.mark.parametrize("title,short", [
    ("XIX - The Sun", "The Sun"), ("2 of Wands - Dominion", "2 of Wands"), ("Knight of Swords", "Knight of Swords"),
])
def test_short_card_name(title, short):
    from ootk import visual
    assert visual.short_card_name(title) == short


# ---------- web GUI extras: card details, exports, search ----------

def test_report_embeds_card_details_and_reading_json(client):
    r = post(client, topic="Love & War <3")
    assert r.status_code == 200
    import re as re_mod
    def embedded(id_):
        m = re_mod.search(rf'<script type="application/json" id="{id_}">(.*?)</script>', r.text, re_mod.S)
        return json.loads(m.group(1))
    cards = embedded("cardDetails")
    assert [c["title"] for c in cards] == ["A", "B", "C"]
    assert ["Platonic solid", "Tetrahedron"] in cards[0]["fields"]
    assert cards[1]["dignities"]                                  # middle card touches two pairs
    reading = embedded("readingData")
    assert reading["settings"]["topic"] == "Love & War <3"      # raw text survives the embed
    assert len(reading["cards"]) == 3 and reading["cards"][0]["primary_element"] == "Fire"
    assert "<3" not in r.text.split('id="readingData">')[1].split("</script>")[0]   # escaped inside <script>


def test_report_cards_are_clickable_and_searchable(client):
    cards = ",".join(f"Card {i}" for i in range(75))
    text = post(client, spread_key="12", selected_cards=cards).text
    assert text.count('class="card-slot"') == 75
    assert 'data-card="74"' in text and 'data-search="[op 4] decan 36: mars in pisces (10 of cups) card 74' in text
    assert 'id="reportSearch"' in text and 'data-svg-download="op4"' in text


# ---------- reading accuracy: solids, closed wheels, withheld cards, labels ----------

def major(title, attribution=""):
    return fake_card(title, suit=None, arcana="Major", attribution=attribution)


@pytest.mark.parametrize("card,solid", [
    (fake_card("2 of Wands - Dominion", suit="Wands"), "Tetrahedron"),
    (fake_card("9 of Cups - Happiness", suit="Cups"), "Icosahedron"),
    (fake_card("6 of Swords - Science", suit="Swords"), "Octahedron"),
    (fake_card("Ace of Disks", suit="Disks"), "Hexahedron (Cube)"),
    (major("IV - The Emperor"), "Tetrahedron"),      # on Tzaddi, but still Aries
    (major("XVII - The Star"), "Octahedron"),        # on Heh, but still Aquarius
    (major("I - The Magus"), "Dodecahedron"),        # planetary
    (major("XXI - The Universe"), "Hexahedron (Cube)"),
])
def test_solid_follows_the_card(card, solid):
    row = analysis.apply_card_solid(dict(card))
    assert row["platonic_solid"] == solid
    assert row["dual_solid"] == analysis.PLATONIC_SOLIDS[solid]["dual_solid"]


def test_solid_agrees_with_the_element_count():
    cards = [major(t) for t in ("IV - The Emperor", "XVII - The Star", "XI - Lust")] + \
            [fake_card(f"{n} of {s}", suit=s) for s in ("Wands", "Cups", "Swords", "Disks") for n in (2, 5)]
    for card in cards:
        solid = analysis.apply_card_solid(dict(card))["platonic_solid"]
        assert analysis.ELEMENT_SOLIDS[analysis.derive_primary_element(card)] == solid


def blank_results(n, positions=None):
    return [{"position_number": i + 1, "position_name": (positions or [f"P{i}"] * n)[i],
             "card_data": fake_card(f"C{i}")} for i in range(n)]


def test_wheels_close_their_circle_in_the_master_pipeline():
    positions = spreads.spread_positions("12")
    pairs = {(d["from_index"], d["to_index"])
             for d in analysis.calculate_elemental_dignities(blank_results(75, positions), "12")}
    assert {(26, 15), (38, 27), (74, 39)} <= pairs        # 27<->16, 39<->28, 75<->40
    assert (14, 0) not in pairs                           # Op 1 is a heap, not a wheel
    assert len(pairs) == 14 + 12 + 12 + 36


@pytest.mark.parametrize("key,n", [("9", 12), ("10", 12), ("11", 36)])
def test_standalone_wheels_close_their_circle(key, n):
    pairs = [(d["from_index"], d["to_index"]) for d in analysis.calculate_elemental_dignities(blank_results(n), key)]
    assert pairs[-1] == (n - 1, 0) and len(pairs) == n


def test_closing_pair_counts_towards_dignity():
    results = blank_results(12)
    results[0]["card_data"] = fake_card("C0", suit="Cups")
    results[11]["card_data"] = fake_card("C11", suit="Wands")
    matrix = analysis.calculate_elemental_dignities(results, "9")
    assert any(d["from_index"] == 11 and d["to_index"] == 0 and d["score"] == -2 for d in matrix)


def test_decan_positions_name_the_decan():
    labels = spreads.SPREADS["11"]["positions"]
    assert labels[0] == "Decan 1: Mars in Aries (2 of Wands)"
    assert labels[3] == "Decan 4: Mercury in Taurus (5 of Disks)"
    assert labels[35] == "Decan 36: Mars in Pisces (10 of Cups)"
    assert len(set(labels)) == 36


def test_op1_is_not_called_the_classic_first_operation():
    assert "variant" in spreads.SPREADS["8"]["name"] and "IHVH" in spreads.SPREADS["8"]["name"]


def test_ring_aspects_carry_the_cards_dignity():
    results = blank_results(12)
    results[6]["card_data"] = fake_card("C6", suit="Cups")
    spatial = analysis.analyze_spatial_vectors(results, "9")
    opp = next(s for s in spatial if s["from_index"] == 0 and s["to_index"] == 6)
    assert opp["aspect_name"] == "Opposition"
    assert (opp["card_score"], opp["card_relationship"]) == (-2, "Contrary / Ill-Dignified (Fire + Water)")


def test_withheld_summary():
    deck = [fake_card("A", suit="Wands"), fake_card("B", suit="Disks"), fake_card("C", suit="Disks")]
    w = analysis.withheld_summary(deck, ["A"])
    assert [r["title"] for r in w["cards"]] == ["B", "C"]
    assert w["elements"]["Earth"] == 2 and w["deck_elements"]["Fire"] == 1
    assert analysis.withheld_summary(deck, ["A", "B", "C"]) is None
    big = [fake_card(f"X{i}") for i in range(40)]
    assert analysis.withheld_summary(big, ["X0"]) is None          # too many left out to list


def test_report_lists_withheld_cards(seeded_client):
    r = post(seeded_client, spread_key="12", draw_mode="seed", seed="1568", selected_cards="")
    drawn = set(seeded_client.lookups[-1])
    left = [c["title"] for c in DECK if c["title"] not in drawn]
    assert len(left) == 3
    assert "Withheld" in r.text and all(t in r.text for t in left)
    assert "### Withheld (3 cards not drawn)" in r.text            # in the Markdown prompt too


def test_framework_basis_explains_n():
    _name, basis = analysis.evaluate_macro_framework(
        [{"position_number": i, "position_name": "", "card_data": fake_card(f"C{i}")} for i in range(10)])
    assert "n=10 cards with a place on the Tree" in basis


def test_headline_names_ties_and_absent_elements():
    from ootk.visual import _element_rows, _headline
    none = {"pairs": 0}, {"total": 0}
    one = _headline(_element_rows({"Fire": 1}), *none)
    assert one[0] == "Fire leads (100%); Water, Air and Earth are absent."
    tie = _headline(_element_rows({"Fire": 1, "Water": 1, "Air": 1}), *none)
    assert tie[0] == "Fire, Water and Air share the lead (33.3% each); Earth is absent."
    low = _headline(_element_rows({"Fire": 3, "Water": 1, "Air": 1, "Earth": 2}), *none)
    assert low[0] == "Fire leads (42.9%); Water and Air are weakest (14.3% each)."


def test_report_has_its_own_link_and_reloading_saves_nothing(client):
    r = post(client, follow=False)
    assert r.status_code == 303 and r.headers["location"] == "/report/99"
    assert client.saved["count"] == 1
    assert client.saved["report_settings"]["card_titles"] == ["A", "B", "C"]
    for _ in range(2):                                                   # reload twice
        page = client.get("/report/99")
        assert page.status_code == 200 and "Keep this reading" in page.text
    assert client.saved["count"] == 1
    missing = client.get("/report/5", headers={"Accept": "text/html"})
    assert missing.status_code == 404 and "Back to settings" in missing.text

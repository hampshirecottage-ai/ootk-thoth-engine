"""Run from the project root:  python -m pytest -v
Needs: pip install -e ".[dev]"
"""
import json
from contextlib import nullcontext
from pathlib import Path

import pytest

from ootk import analysis, db, report, shuffle, spreads
from ootk import web as app_module
from ootk.lockout import FailedLogins
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
    monkeypatch.setattr(app_module, "_sample_cache", {})
    monkeypatch.setattr(app_module, "_sign_carriers_cache", {s: {} for s in app_module.MAPPING_SYSTEMS})
    monkeypatch.setattr(app_module, "get_db_connection", lambda: nullcontext(object()))
    monkeypatch.setattr(app_module, "fetch_all_cards", lambda conn: [])
    lookups, systems = [], []

    def fake_fetch(conn, titles, system="thoth"):
        lookups.append(list(titles))
        systems.append(system)
        return {t: fake_card(t) for t in titles}

    monkeypatch.setattr(app_module, "fetch_cards_correspondences", fake_fetch)
    monkeypatch.setattr(app_module, "_reference_cache", {})
    monkeypatch.setattr(app_module, "failed_logins", FailedLogins())
    # Drawn cards bypass the reference cache, so each reading's lookup is recorded.
    monkeypatch.setattr(app_module, "card_rows", lambda titles, system: fake_fetch(None, titles, system))

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
    monkeypatch.setattr(app_module, "load_report_by_link",
                        lambda conn, link: (99, dict(saved["report_settings"]))
                        if saved and saved["report_settings"].get("link") == link else None)
    monkeypatch.setattr(app_module, "withheld_cards",
                        lambda deck, titles, system="thoth": analysis.withheld_summary(
                            [fake_card(c["title"]) for c in deck], titles))
    c = TestClient(app_module.app)
    c.saved = saved
    c.lookups = lookups
    c.systems = systems
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
    monkeypatch.setattr(app_module, "card_rows", lambda titles, system: {"A": fake_card("A")})
    r = post(client)
    assert r.status_code == 400
    assert "'B'" in r.json()["detail"]                    # first missing title, in draw order


# ---------- app: happy paths ----------

def test_index_renders(client):
    assert client.get("/").status_code == 200


def test_start_page_is_settings_only_and_pick_page_has_the_catalog(client, monkeypatch):
    monkeypatch.setattr(app_module, "fetch_all_cards", lambda conn: [{"title": "X - Fortune"}])
    start = client.get("/").text
    assert 'name="draw_mode" value="seed"' in start and 'href="/pick"' in start
    assert 'id="cardGrid"' not in start and 'id="presetSelect"' not in start
    pick = client.get("/pick")
    assert pick.status_code == 200
    assert 'name="draw_mode" value="manual"' in pick.text and 'id="cardGrid"' in pick.text
    assert 'id="pickBar"' in pick.text and 'name="seed"' not in pick.text


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


def test_wrong_passwords_lock_the_visitor_out(client, monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "s3cret")
    assert client.get("/").status_code == 401                 # the browser's first, empty try
    for _ in range(9):
        assert client.get("/", auth=("x", "guess")).status_code == 401
    r = client.get("/", auth=("x", "guess"))                    # the tenth wrong password
    assert r.status_code == 429 and int(r.headers["retry-after"]) == 900
    r = client.get("/", auth=("x", "s3cret"))                   # even the right one, while locked
    assert r.status_code == 429 and "Try again in 15 minutes" in r.text
    assert r.headers["x-frame-options"] == "DENY"


def test_right_password_resets_the_count(client, monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "s3cret")
    for _ in range(9):
        client.get("/", auth=("x", "guess"))
    assert client.get("/", auth=("x", "s3cret")).status_code == 200
    for _ in range(9):
        assert client.get("/", auth=("x", "guess")).status_code == 401


def test_lockout_ends_and_old_failures_expire():
    now = [0.0]
    f = FailedLogins(attempts=3, window=60, clock=lambda: now[0])
    assert f.failed("a") == 0 and f.failed("a") == 0
    now[0] = 61                                                 # both fall out of the window
    assert f.failed("a") == 0 and f.retry_after("a") == 0
    f.failed("a")
    assert f.failed("a") == 60 and f.retry_after("a") == 60
    assert f.retry_after("b") == 0                              # other visitors unaffected
    now[0] = 121.5
    assert f.retry_after("a") == 0 and f.failed("a") == 0


def test_lockout_table_stays_bounded():
    f = FailedLogins(max_tracked=5)
    for i in range(50):
        f.failed(str(i))
    assert len(f._failures) == 5 and "49" in f._failures


def test_lockout_uses_cloudflares_address_on_render_not_x_forwarded_for(monkeypatch):
    class Req:
        def __init__(self, headers):
            self.headers, self.client = headers, type("C", (), {"host": "10.0.0.1"})()

    spoof = {"x-forwarded-for": "1.2.3.4", "cf-connecting-ip": "203.0.113.9"}
    monkeypatch.delenv("RENDER", raising=False)
    assert app_module.visitor_address(Req(spoof)) == "10.0.0.1"
    monkeypatch.setenv("RENDER", "true")
    assert app_module.visitor_address(Req(spoof)) == "203.0.113.9"
    assert app_module.visitor_address(Req({"x-forwarded-for": "1.2.3.4"})) == "10.0.0.1"


def test_security_headers(client, monkeypatch):
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    for path in ["/", "/static/js/index.js", "/robots.txt"]:
        r = client.get(path)
        assert r.headers["x-content-type-options"] == "nosniff"
        assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
        assert r.headers["referrer-policy"] == "strict-origin-when-cross-origin"
        assert "strict-transport-security" not in r.headers          # plain http here
    assert client.get("https://testserver/").headers["strict-transport-security"] == "max-age=31536000"
    monkeypatch.setenv("APP_PASSWORD", "s3cret")
    assert client.get("/").headers["x-frame-options"] == "DENY"     # the password prompt too


def test_api_docs_are_off(client):
    for path in ["/docs", "/redoc", "/openapi.json"]:
        assert client.get(path).status_code == 404


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
    html = client.get("/pick").text
    assert '/static/cards/thumb/x---fortune.webp?v=' in html
    assert 'loading="lazy"' in html and "/static/images/" not in html    # no full-size JPG scans
    assert 'src="/static/js/index.js?v=' in html and "defer" in html


def test_reference_tables_are_read_once_per_process(client, monkeypatch):
    calls = {"deck": 0, "rows": 0, "connect": 0}

    def fake_deck(conn):
        calls["deck"] += 1
        return [{"card_id": 1, "title": "X - Fortune", "arcana_type": "Major", "key_scale": 1}]

    def fake_rows(conn, titles, system="thoth"):
        calls["rows"] += 1
        return {t: fake_card(t) for t in titles}

    def connect():
        calls["connect"] += 1
        return nullcontext(object())

    monkeypatch.setattr(app_module, "fetch_all_cards", fake_deck)
    monkeypatch.setattr(app_module, "fetch_cards_correspondences", fake_rows)
    monkeypatch.setattr(app_module, "get_db_connection", connect)
    for _ in range(3):
        assert client.get("/maps").status_code == 200
    assert calls == {"deck": 1, "rows": 1, "connect": 2}     # first request only


def test_card_rows_are_copies(monkeypatch):
    monkeypatch.setattr(app_module, "_reference_cache",
                        {"deck": [{"title": "A"}], "thoth": {"A": fake_card("A")}})
    row = app_module.card_rows(["A", "missing"], "thoth")
    assert list(row) == ["A"]
    row["A"]["title"] = "changed"
    assert app_module.reference_rows("thoth")["A"]["title"] == "A"


def test_static_url_is_cached_briefly(monkeypatch):
    from ootk import assets
    monkeypatch.setattr(assets, "_url_cache", {})
    url = assets.static_url("js/index.js")
    assert url.startswith("/static/js/index.js?v=") and assets.static_url("js/index.js") == url
    assert assets.static_url("js/missing.js") is None
    assert set(assets._url_cache) == {"js/index.js", "js/missing.js"}


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
    assert "issues/new?template=bug_report.yml" in r.text                      # and a way to report it


def test_pages_link_to_bug_report_and_contact(client):
    for html in (client.get("/").text, post(client).text):              # settings and report pages
        assert 'class="site-footer"' in html
        assert "/issues/new?template=bug_report.yml" in html and "/discussions" in html


def test_pages_have_description_previews_and_icons(client, monkeypatch):
    monkeypatch.setenv("SITE_URL", "https://example.org/")
    for path in ("/", "/pick"):
        page = client.get(path).text
        assert '<meta name="description"' in page and 'name="robots"' not in page
        assert '<meta property="og:image" content="https://example.org/static/site/og-image.jpg">' in page
        assert f'<link rel="canonical" href="https://example.org{path}">' in page
        assert 'name="twitter:card" content="summary_large_image"' in page
        assert 'href="/favicon.ico"' in page and 'href="data:,"' not in page
    report = post(client).text
    assert '<meta name="robots" content="noindex">' in report    # readings stay unlisted
    assert 'rel="canonical"' not in report and 'property="og:image"' in report


def test_robots_sitemap_and_favicon(client, monkeypatch):
    monkeypatch.delenv("SITE_URL", raising=False)
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://ootk.example.com")
    robots = client.get("/robots.txt")
    assert robots.status_code == 200 and robots.headers["content-type"].startswith("text/plain")
    assert "Disallow: /report/" in robots.text and "Disallow: /reading" in robots.text
    assert "Sitemap: https://ootk.example.com/sitemap.xml" in robots.text
    sitemap = client.get("/sitemap.xml")
    assert sitemap.headers["content-type"].startswith("application/xml")
    assert "<loc>https://ootk.example.com/</loc>" in sitemap.text
    assert "<loc>https://ootk.example.com/pick</loc>" in sitemap.text and "/report" not in sitemap.text
    for path in ("/start", "/history", "/examples", "/library", "/maps", "/method"):
        assert f"<loc>https://ootk.example.com{path}</loc>" in sitemap.text
    assert f"<loc>https://ootk.example.com/day/{app_module.utc_today().isoformat()}</loc>" in sitemap.text
    icon = client.get("/favicon.ico")
    assert icon.status_code == 200 and icon.headers["content-type"] == "image/x-icon"
    for name in ("site/favicon.svg", "site/apple-touch-icon.png", "site/og-image.jpg"):
        assert client.get(f"/static/{name}").status_code == 200


def test_guide_pages_render_and_link_each_other(client, monkeypatch):
    monkeypatch.setattr(app_module, "_examples_cache", {})
    for path, heading in [("/start", "Your first reading, step by step"), ("/history", "The Golden Dawn"),
                          ("/examples", "Open the report"),
                          ("/library", "Every spread"), ("/maps", "Pick a card"), ("/method", "Limitations")]:
        page = client.get(path)
        assert page.status_code == 200 and heading in page.text
        assert f'<a href="{path}" aria-current="page">' in page.text      # nav marks this page
        assert 'class="site-footer"' in page.text and 'rel="canonical"' in page.text
    assert 'href="/start"' in client.get("/").text                       # start page links in


def test_history_page_credits_every_photo_and_links_from_start_here(client):
    assert 'href="/history"' in client.get("/start").text
    page = client.get("/history").text
    assert 'href="/method#art"' in page                                  # links the art explainer, not a copy
    photos = sorted(p.name for p in (app_module.BASE_DIR / "static" / "history").glob("*.webp"))
    assert photos, "no history photos"
    for name in photos:
        assert f"/static/history/{name}?v=" in page, name               # every photo shown
    credits = (app_module.BASE_DIR / "static" / "history" / "CREDITS.md").read_text()
    for name in photos:
        assert name in credits, name                                    # and credited


def test_start_here_links_preselect_each_spread(client):
    page = client.get("/start").text
    for key in app_module.SPREADS:
        assert f'href="/?spread={key}#readingForm"' in page


def test_spread_picker_groups_every_spread_by_stage_and_starts_on_three_cards(client):
    staged = [key for _, _, keys, _ in app_module.SPREAD_STAGES for key in keys]
    assert sorted(staged) == sorted(app_module.SPREADS)                  # each spread once
    page = client.get("/").text
    assert page.count("<optgroup") == len(app_module.SPREAD_STAGES)
    assert f'<option value="{app_module.DEFAULT_SPREAD}" selected>' in page


def test_report_opens_on_the_next_step_not_the_settings(client):
    page = post(client).text
    assert page.index('id="nowStep"') < page.index('id="summary"') < page.index('id="readingDetails"')
    assert "<h1>Your reading · " in page


def test_examples_link_shared_readings_and_draw_cards_with_a_full_deck(client, monkeypatch):
    monkeypatch.setattr(app_module, "_examples_cache", {})
    page = client.get("/examples").text                                  # empty deck: links only
    for ex in app_module.EXAMPLES:
        assert f"/reading?seed={ex['seed']}&amp;spread={ex['spread_key']}" in page
    deck = [fake_card(f"Card {i}") | {"card_id": i} for i in range(78)]
    examples = app_module.example_readings(deck)
    assert [len(ex["cards"]) for ex in examples] == [ex["count"] for ex in examples]
    assert examples[0]["cards"][0]["title"] == shuffle.shuffle_deck(deck, "2026-01-01")[0]["title"]


def test_library_terms_are_sorted_and_have_text():
    library = app_module.load_library()
    names = [t["term"].lower() for t in library["terms"]]
    assert names == sorted(names) and len(set(names)) == len(names)
    assert all(t["text"].strip() for t in library["terms"])
    assert all(r["url"].startswith("https://") for r in library["reading"])


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


def test_hexagram_follows_the_golden_dawn_layout():
    # Planets as on the Tree of Life: Saturn top, Jupiter/Venus right, Mars/Mercury left,
    # Sun centre, Moon bottom.
    where = {"Saturn": (0.0, 1.0), "Jupiter": (0.866, 0.5), "Mars": (-0.866, 0.5),
             "Venus": (0.866, -0.5), "Mercury": (-0.866, -0.5), "Sun": (0.0, 0.0),
             "Moon": (0.0, -1.0)}
    labels = spreads.SPREADS["6"]["positions"]
    coords = spreads.SPREAD_DEFAULT_COORDINATES["6"]
    assert len(labels) == len(coords) == 7
    for label, xy in zip(labels, coords):
        assert xy == where[label.split()[1]], label


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
    """Layout and ring aspects both take their score and wording from ootk.rules."""
    from ootk import rules
    for aspect in rules.ASPECTS:
        label, nature, score = analysis.calculate_spatial_aspect(aspect.angle)
        assert (label, nature, score) == (rules.aspect_label(aspect), aspect.nature, aspect.score)
    for short, label, angle, nature, score in spreads.RING_ASPECTS:
        a = rules.ASPECTS_BY_NAME[short]
        assert (label, angle, nature, score) == (rules.aspect_label(a), a.angle, a.nature, a.score)


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
    r = post(seeded_client, spread_key="12", draw_mode="seed", seed="1568", selected_cards="",
             significator="Knight of Swords")
    assert r.status_code == 200
    assert seeded_client.lookups[-1] == expected
    assert "1568" in r.text and "ootk --spread 12 --seed 1568" in r.text
    assert "PRNG Seed: 1568" in seeded_client.saved["notes"]
    assert seeded_client.saved["significator"] == "Knight of Swords"


def test_seed_mode_same_seed_same_cards(seeded_client):
    for seed in ("42", "42", "43"):
        post(seeded_client, follow=False, spread_key="8", draw_mode="seed", seed=seed,
             significator="Knight of Swords")
    a, b, c = seeded_client.lookups[-3:]
    assert a == b and a != c


def test_blank_seed_gets_a_new_seed_shown_on_the_report(seeded_client):
    r = post(seeded_client, spread_key="3", draw_mode="seed", seed="")
    assert r.status_code == 200
    seed = seeded_client.saved["notes"].split("PRNG Seed: ")[1].split(" |")[0]
    assert seed.isdigit() and f'id="seedValue">{seed}<' in r.text


def test_seed_mode_unknown_significator_is_400(seeded_client):
    assert post(seeded_client, draw_mode="seed", seed="1", significator="Nobody").status_code == 400


def test_seed_mode_needs_a_significator_only_where_the_spread_has_one(seeded_client):
    r = post(seeded_client, follow=False, spread_key="8", draw_mode="seed", seed="1")
    assert r.status_code == 400 and "needs a significator" in r.json()["detail"]
    assert post(seeded_client, spread_key="3", draw_mode="seed", seed="1").status_code == 200
    assert seeded_client.saved["significator"] == "None (spread has no significator position)"


# ---------- shareable links and card of the day ----------

def test_report_share_link_redraws_the_same_cards_without_the_topic(seeded_client):
    r = post(seeded_client, spread_key="12", draw_mode="seed", seed="918851", selected_cards="",
             significator="Knight of Swords", mapping_system="golden_dawn", topic="private question")
    drawn = seeded_client.lookups[-1]
    path = "/reading?seed=918851&spread=12&system=golden_dawn&significator=Knight+of+Swords"
    assert f'data-path="{path.replace("&", "&amp;")}"' in r.text
    saves = seeded_client.saved["count"]
    shared = seeded_client.get(path)
    assert shared.status_code == 200
    assert seeded_client.lookups[-1] == drawn and seeded_client.systems[-1] == "golden_dawn"
    assert "private question" not in shared.text and "Shared reading" in shared.text
    assert seeded_client.saved["count"] == saves                 # opening a link saves nothing


def test_share_link_accepts_short_system_names_and_the_start_page_forwards(seeded_client):
    assert seeded_client.get("/reading?seed=1&spread=3&system=gd").status_code == 200
    assert seeded_client.systems[-1] == "golden_dawn"
    r = seeded_client.get("/?seed=1&spread=3&system=gd", follow_redirects=False)
    assert r.status_code == 307 and r.headers["location"] == "/reading?seed=1&spread=3&system=gd"


@pytest.mark.parametrize("query", ["spread=3", "seed=1&spread=99", "seed=1&spread=3&system=nope",
                                   "seed=1&spread=3&framework=nope", "seed=" + "9" * 65 + "&spread=3",
                                   "seed=1&spread=8"])
def test_bad_share_links_are_400(seeded_client, query):
    assert seeded_client.get(f"/reading?{query}").status_code == 400


def test_hand_picked_report_has_no_share_link(client):
    r = post(client, draw_mode="manual")
    assert r.status_code == 200 and "shareLink" not in r.text


def test_reports_are_not_indexed(seeded_client):
    assert '<meta name="robots" content="noindex">' in seeded_client.get("/reading?seed=1&spread=3").text


def test_card_of_the_day_is_the_top_card_of_the_date_seeded_deck(seeded_client, monkeypatch):
    from datetime import date
    monkeypatch.setattr(app_module, "utc_today", lambda: date(2026, 10, 3))
    r = seeded_client.get("/today", follow_redirects=False)
    assert r.status_code == 307 and r.headers["location"] == "/day/2026-10-03"
    r = seeded_client.get("/day/2026-10-03")
    assert r.status_code == 200
    top = shuffle.shuffle_deck(DECK, "2026-10-03")[0]["title"]
    assert seeded_client.lookups[-1] == [top] and f"<h2>{top}</h2>" in r.text
    assert 'href="/day/2026-10-02"' in r.text and "Next day" not in r.text
    assert "/reading?seed=2026-10-03&amp;spread=1&amp;system=thoth" in r.text
    assert seeded_client.get("/day/2026-09-30").status_code == 200
    assert "Next day" in seeded_client.get("/day/2026-09-30").text


@pytest.mark.parametrize("day", ["2026-10-05", "2026-1-3", "yesterday", "2026-02-30"])
def test_card_of_the_day_rejects_bad_or_future_dates(seeded_client, monkeypatch, day):
    from datetime import date
    monkeypatch.setattr(app_module, "utc_today", lambda: date(2026, 10, 3))
    assert seeded_client.get(f"/day/{day}").status_code == 404


def test_cli_command_leaves_out_a_blank_significator():
    assert "--significator" not in app_module.cli_command("3", "1", "golden_dawn", "auto", "", "")
    assert "--significator 'Queen of Cups'" in app_module.cli_command("8", "1", "golden_dawn", "auto",
                                                                      "Queen of Cups", "")


def test_start_page_has_the_picker_and_no_default_card(client):
    page = client.get("/").text
    assert 'id="sigRank"' in page and 'id="birthSpans"' in page
    assert 'value="Knight of Swords"' not in page               # no preset significator
    assert 'name="sig_birthday"' not in page and 'id="sigBirthday"' in page   # date is never sent
    pick = client.get("/pick").text
    assert 'name="significator"' not in pick and "first card you place is the significator" in pick


def sample_deck():
    """78 fake cards, one of them the sample's significator."""
    deck = [dict(fake_card(f"Card {i}"), card_id=i) for i in range(77)]
    return deck + [dict(fake_card("Queen of Cups", suit="Cups", arcana="Court"), card_id=77)]


def test_start_page_shows_the_sample_reading_before_the_settings(client, monkeypatch):
    deck = sample_deck()
    monkeypatch.setattr(app_module, "fetch_all_cards", lambda conn: deck)
    page = client.get("/").text
    s = app_module.SAMPLE_SETTINGS
    expected, _ = app_module.seeded_draw(deck, s["seed"], s["spread_key"], s["significator"])
    assert len(expected) == 75 and all(title in page for title in expected)
    assert page.count('<details class="op">') == 4
    assert page.index('id="sample"') < page.index('id="readingForm"')
    assert 'id="copySample"' in page and "HERMETIC ANALYTICAL REPORT" in page
    assert client.saved == {}                                   # the sample is never saved
    assert 'id="sample"' not in client.get("/pick").text


def test_start_page_links_the_card_of_the_day_and_the_sample_report(client, monkeypatch):
    from datetime import date
    deck = sample_deck()
    monkeypatch.setattr(app_module, "fetch_all_cards", lambda conn: deck)
    monkeypatch.setattr(app_module, "utc_today", lambda: date(2026, 10, 3))
    page = client.get("/").text
    top = shuffle.shuffle_deck(deck, "2026-10-03")[0]["title"]
    assert f'<a href="/today" class="today-link">Today&rsquo;s card: <strong>{top}</strong>' in page
    link = "/reading?seed=12345&spread=12&system=thoth&significator=Queen+of+Cups"
    assert f'href="{link.replace("&", "&amp;")}"' in page
    assert client.get(link).status_code == 200
    assert 'href="/today">Today' not in client.get("/pick").text


def test_start_page_first_screen_says_who_it_is_for_and_what_to_do(client):
    page = client.get("/").text
    assert "For tarot readers who use ChatGPT" in page
    assert 'class="btn-cta" href="#readingForm"' in page
    assert f'href="{app_module.REPO_URL}"' in page


def test_start_page_without_a_full_deck_skips_the_sample(client):
    page = client.get("/").text
    assert page.count('id="sample"') == 0 and 'id="readingForm"' in page


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


def test_report_view_explains_and_lists_each_operations_links():
    from ootk import visual
    elements = ["Wands", "Cups", "Swords", "Pentacles"]
    cards = [fake_card(f"C{i}", suit=elements[i % 4], attribution=None) for i in range(75)]
    results = [{"position_number": i + 1, "position_name": p, "card_data": c}
               for i, (p, c) in enumerate(zip(spreads.spread_positions("12"), cards))]
    dignity = analysis.calculate_elemental_dignities(results, "12")
    spatial = analysis.analyze_spatial_vectors(results, "12")
    segs = visual.build_report_view("12", results, analysis.analyze_elemental_balance(results),
                                    dignity, spatial, "x", "y")["segments"]
    assert "1 with 2" in segs[0]["how"][0]
    assert "4 houses apart is a trine (120\u00b0, +2)" in segs[1]["how"][2]
    assert "18 decans apart is an opposition (180\u00b0, -1)" in segs[3]["how"][2]
    for seg in segs:
        links = seg["links"]
        # Every element pair and aspect is listed once, and drawn once in element-pair mode.
        assert len(links["pairs"]) == len(seg["dignity_rows"]) == len(seg["drawing"]["pair_links"])
        assert len(links["aspects"]) == len(seg["aspects"])
        assert all(p["why"] for p in links["pairs"])
    # On a wheel each card has two neighbours and seven aspects; each aspect also gives the cards' score.
    decans = segs[3]["links"]
    for i in range(36):
        assert sum(i in (p["a"], p["b"]) for p in decans["pairs"]) == 2
        assert sum(i in (a["a"], a["b"]) for a in decans["aspects"]) == 7
    assert decans["aspects"][0]["apart"] == "18 decans apart (180\u00b0)"
    assert decans["aspects"][0]["cards"]
    assert segs[1]["links"]["cards"][2]["where"] == "3. Third House: Local Mind & Travel"
    assert segs[2]["links"]["cards"][0]["where"] == "1. Aries"
    houses = segs[1]["drawing"]["labels"]
    assert houses[0] == dict(houses[0], text="House 1", sub=["Ascendant /", "Physical Self"])
    assert houses[6]["sub"] == ["Partnerships"]


@pytest.mark.parametrize("e1,e2,text", [
    ("Fire", "Fire", "both Fire: same element"), ("Fire", "Water", "Fire and Water: contrary elements"),
    ("Air", "Fire", "Air and Fire: friendly elements"), ("Spirit", "Earth", "Spirit and Earth: Spirit scores 0 with any element"),
])
def test_element_reason(e1, e2, text):
    from ootk import visual
    assert visual.element_reason(e1, e2) == text


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
    links = embedded("links-op1")
    assert [c["title"] for c in links["cards"]] == ["A", "B", "C"] and len(links["pairs"]) == 2
    assert "How the cards are linked" in r.text and 'id="inspect-op1"' in r.text
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
    r = post(seeded_client, spread_key="12", draw_mode="seed", seed="1568", selected_cards="",
             significator="Knight of Swords")
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
    link = client.saved["report_settings"]["link"]
    assert r.status_code == 303 and r.headers["location"] == f"/report/{link}"
    assert client.saved["count"] == 1
    assert client.saved["report_settings"]["card_titles"] == ["A", "B", "C"]
    for _ in range(2):                                                   # reload twice
        page = client.get(f"/report/{link}")
        assert page.status_code == 200 and 'id="nextStep"' in page.text
    assert client.saved["count"] == 1
    missing = client.get("/report/5", headers={"Accept": "text/html"})
    assert missing.status_code == 404 and "Back to settings" in missing.text


def test_report_links_are_random_not_session_numbers(client):
    post(client, follow=False)
    first = client.saved["report_settings"]["link"]
    post(client, follow=False)
    second = client.saved["report_settings"]["link"]
    assert first != second and len(first) >= 20 and not first.isdigit()
    assert client.get("/report/99").status_code == 404                  # the session number


# ---------- database/schema.sql ----------

def test_schema_sql_never_drops_an_existing_database():
    """schema.sql builds a new database; on one that already has ootk tables it must stop first."""
    sql = (Path(__file__).resolve().parents[1] / "database" / "schema.sql").read_text()
    assert "DROP TABLE" not in sql and "DROP SEQUENCE" not in sql
    lines = sql.splitlines()
    stop, restrict = lines.index("\\set ON_ERROR_STOP on"), next(
        i for i, line in enumerate(lines) if line.startswith("\\restrict "))
    assert stop < restrict                      # \restrict blocks backslash commands after it
    guard = sql.index("RAISE EXCEPTION")
    assert guard < sql.index("CREATE TABLE") and guard < sql.index("setval")


# ---------- significator methods ----------

def test_book_t_card():
    from ootk import significator
    assert significator.book_t_card("Queen", "Cups") == "Queen of Cups"
    with pytest.raises(ValueError):
        significator.book_t_card("King", "Cups")              # Thoth titles only


@pytest.mark.parametrize("month, day, card", [
    (1, 1, "Queen of Disks"), (1, 9, "Queen of Disks"), (1, 10, "Prince of Swords"),
    (3, 10, "Knight of Cups"), (3, 11, "Queen of Wands"), (5, 20, "Knight of Swords"),
    (7, 12, "Prince of Wands"), (8, 11, "Prince of Wands"), (11, 13, "Knight of Wands"),
    (12, 12, "Knight of Wands"), (12, 13, "Queen of Disks"), (12, 31, "Queen of Disks"),
])
def test_card_for_birthday(month, day, card):
    from ootk import significator
    assert significator.card_for_birthday(month, day) == card


def test_birth_spans_cover_the_twelve_dated_courts_once():
    from ootk import significator
    cards = [c for _, c in significator.BIRTH_SPANS]
    assert len(set(cards)) == 12 and not any(c.startswith("Princess") for c in cards)
    assert [s for s, _ in significator.BIRTH_SPANS] == sorted(s for s, _ in significator.BIRTH_SPANS)


# ---------- mapping systems: the Tzaddi/Heh swap ----------

def test_default_mapping_is_thoth_and_says_so(client):
    r = post(client)
    assert client.systems[-1] == "thoth"
    assert "Emperor on Tzaddi, Star on Heh" in r.text


def test_golden_dawn_is_labelled_unswapped(client):
    r = post(client, mapping_system="golden_dawn")
    assert client.systems[-1] == "golden_dawn"
    assert "Emperor on Heh, Star on Tzaddi" in r.text
    assert client.saved["report_settings"]["mapping_version"] == app_module.MAPPING_VERSION


def test_old_golden_dawn_links_keep_the_thoth_swap(client):
    """Before 'thoth' existed, 'golden_dawn' readings were built with the swap applied."""
    post(client, mapping_system="golden_dawn")
    del client.saved["report_settings"]["mapping_version"]
    r = client.get(f"/report/{client.saved['report_settings']['link']}")
    assert client.systems[-1] == "thoth"
    assert "Emperor on Tzaddi, Star on Heh" in r.text


def test_sample_summary_states_facts_not_meanings():
    def item(n, pos, title, arcana="Minor", place=None):
        return {"position_number": n, "position_name": pos,
                "card_data": {"title": title, "arcana_type": arcana, "spatial_dimension": place}}
    r = {
        "spread_results": [item(1, "1. Significator / Core Nature of Question", "Queen of Cups",
                                "Court", "Lower-East Edge"),
                           item(2, "2. Development", "V - The Hierophant", "Major"),
                           item(3, "3. Ultimate Climax / Resolution", "XIV - Art", "Major")],
        "element_counts": {"Fire": 1, "Water": 1, "Air": 0, "Earth": 1, "Spirit": 0},
        "dignity_matrix": [{"from_index": 0, "to_index": 1, "score": 1},
                           {"from_index": 1, "to_index": 2, "score": -2}],
    }
    settings = {"seed": "12345", "significator": "Queen of Cups", "spread_key": "3"}
    first, second = app_module.sample_summary(r, settings)
    assert first.startswith("Seed 12345, with the Queen of Cups as significator, dealt 3 cards.")
    assert "closes on Art (ultimate climax / resolution)" in first
    assert "1 Fire, 1 Water and 1 Earth" in second
    assert "Of the 2 scored pairs, 1 is friendly and 1 is contrary, a net score of -1." in second
    assert "One of the heap's cards sits on the Cube of Space." in second
    assert second.endswith("What it means is left to your AI.")


def test_start_page_sample_is_the_full_opening_of_the_key():
    assert app_module.SAMPLE_SETTINGS["spread_key"] == "12"
    assert app_module.SAMPLE_SETTINGS["significator"]


# ---------- error handling: failures give a page, never a crash ----------

HTML = {"Accept": "text/html"}


def _db_down(*_args, **_kw):
    raise app_module.psycopg.OperationalError("connection refused")


def test_database_down_gives_a_retry_page_and_keeps_static_pages(client, monkeypatch):
    monkeypatch.setattr(app_module, "get_db_connection", _db_down)
    for path in ("/", "/pick", "/maps", "/day/2026-10-01", "/reading?seed=1&spread=3"):
        r = client.get(path, headers=HTML)
        assert r.status_code == 503, path
        assert "isn&rsquo;t answering" in r.text or "isn’t answering" in r.text
        assert "Try again" in r.text and r.headers["retry-after"] == "30"
        assert "connection refused" not in r.text                  # no internals shown
    r = client.post("/generate_report", headers=HTML, data={"spread_key": "3", "selected_cards": "A,B,C"})
    assert r.status_code == 503
    api = client.get("/maps")
    assert api.status_code == 503 and "card database" in api.json()["detail"]
    for path in ("/start", "/history", "/library", "/method"):
        assert client.get(path).status_code == 200, path
    examples = client.get("/examples")                               # listed, without card names
    assert examples.status_code == 200 and "/reading?seed=777" in examples.text


def test_connection_is_retried_once_after_a_quick_refusal(monkeypatch):
    calls = []

    def flaky(**kw):
        calls.append(kw)
        if len(calls) == 1:
            raise app_module.psycopg.OperationalError("waking up")
        return "conn"

    monkeypatch.setattr(app_module.psycopg, "connect", flaky)
    monkeypatch.setattr(app_module.time, "sleep", lambda s: None)
    assert app_module.get_db_connection() == "conn" and len(calls) == 2
    assert "connect_timeout" in calls[0]


def test_outdated_database_is_a_page_not_a_server_exit(client, monkeypatch):
    def outdated(conn, titles, system="thoth"):
        raise db.DatabaseOutdated("column tc.french_number does not exist")

    monkeypatch.setattr(app_module, "fetch_cards_correspondences", outdated)
    monkeypatch.setattr(app_module, "fetch_all_cards", lambda conn: [{"title": "X - Fortune"}])
    r = client.get("/maps", headers=HTML)
    assert r.status_code == 503 and "needs an update" in r.text


def test_fetch_cards_raises_instead_of_exiting_on_a_missing_column():
    class Cursor:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def execute(self, *a):
            raise db.psycopg.errors.UndefinedColumn()

    class Conn:
        def cursor(self): return Cursor()

    with pytest.raises(db.DatabaseOutdated):
        db.fetch_cards_correspondences(Conn(), ["The Fool"])


def test_unexpected_errors_get_an_apology_page(client, monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("secret internals")

    monkeypatch.setattr(app_module, "load_library", boom)
    c = TestClient(app_module.app, raise_server_exceptions=False)
    r = c.get("/library", headers=HTML)
    assert r.status_code == 500 and "Something went wrong" in r.text
    assert "secret internals" not in r.text and "Report a bug" in r.text


def test_router_errors_and_incomplete_forms_render_pages(client):
    r = client.get("/no-such-page", headers=HTML)
    assert r.status_code == 404 and "Page not found" in r.text
    assert client.get("/no-such-page").json() == {"detail": "Not Found"}     # API clients unchanged
    r = client.post("/generate_report", headers=HTML, data={"topic": "x"})
    assert r.status_code == 400 and "spread_key" in r.text and "Back to settings" in r.text
    assert client.post("/generate_report", data={"topic": "x"}).status_code == 422


def test_long_seed_and_topic_are_refused(seeded_client):
    r = post(seeded_client, draw_mode="seed", seed="9" * 65, selected_cards="")
    assert r.status_code == 400 and "at most 64" in r.json()["detail"]
    r = post(seeded_client, topic="q" * 2001)
    assert r.status_code == 400 and "at most 2000" in r.json()["detail"]
    assert "count" not in seeded_client.saved


def test_earliest_day_has_no_previous_link(seeded_client):
    r = seeded_client.get("/day/0001-01-01")
    assert r.status_code == 200 and "Previous day" not in r.text


# ---------- app: privacy and input limits ----------

def test_saved_reports_are_never_cached_or_indexed(client):
    r = post(client, follow=False)
    assert r.headers["cache-control"] == "no-store" and "noindex" in r.headers["x-robots-tag"]
    page = client.get(f"/report/{client.saved['report_settings']['link']}")
    assert page.headers["cache-control"] == "no-store" and "noindex" in page.headers["x-robots-tag"]
    assert "x-robots-tag" not in client.get("/").headers


def test_report_shows_no_session_number(client):
    post(client, follow=False)
    page = client.get(f"/report/{client.saved['report_settings']['link']}")
    assert "session #" not in page.text and '"session_id"' not in page.text
    r = post(client, output_format="markdown")
    assert r.headers["content-disposition"] == 'attachment; filename="ootk_report.md"'


def test_malformed_report_links_never_reach_the_database(client, monkeypatch):
    def no_db():
        raise AssertionError("database opened for a link that can't exist")

    monkeypatch.setattr(app_module, "get_db_connection", no_db)
    for link in ["5", "x" * 65, "abc$def%20ghijklmnopq", "' OR 1=1 --aaaaaaaaaa"]:
        assert client.get(f"/report/{link}").status_code == 404


def test_access_log_hides_report_links():
    import logging
    record = logging.LogRecord("uvicorn.access", logging.INFO, "", 0, '%s - "%s %s HTTP/%s" %d',
                               ("1.2.3.4:5", "GET", "/report/AbC_123-xyzAbC_123-xy?x=1", "1.1", 200), None)
    app_module.RedactReportLinks().filter(record)
    assert "AbC_123" not in record.getMessage() and "/report/<redacted>?x=1" in record.getMessage()


def test_oversized_posts_are_refused_unread(client):
    r = client.post("/generate_report", data={"spread_key": "3", "topic": "q" * 70_000})
    assert r.status_code == 413
    assert "count" not in client.saved


@pytest.mark.parametrize("over", [
    {"significator": "Q" * 65},
    {"spread_key": "3" * 65},
    {"mapping_system": "m" * 65},
    {"selected_cards": "A," * 2001},
])
def test_overlong_fields_are_refused(client, over):
    r = post(client, **over)
    assert r.status_code == 400 and "count" not in client.saved
    assert "Q" * 41 not in r.text and "m" * 41 not in r.text


def test_error_messages_echo_at_most_40_characters(client):
    r = client.get("/day/" + "9" * 60)
    assert r.status_code == 404 and "9" * 41 not in r.text and "…" in r.json()["detail"]
    r = client.get("/reading", params={"seed": "1", "spread": "s" * 64})
    assert r.status_code == 400 and "s" * 41 not in r.text

"""FastAPI web GUI: `uvicorn ootk.web:app`."""
import base64
import html
import json
import os
import secrets
import shlex
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
import psycopg
from psycopg.rows import dict_row

from ootk import PROJECT_ROOT as BASE_DIR
from ootk.analysis import (
    analyze_elemental_balance, analyze_hebrew_spatial_distribution, analyze_platonic_topology,
    analyze_spatial_vectors, calculate_elemental_dignities, evaluate_macro_framework,
)
from ootk.assets import CachedStaticFiles, CompressionMiddleware, static_url
from ootk.db import (
    DB_CONFIG, DEFAULT_MAPPING, MAPPING_SYSTEMS, fetch_all_cards, fetch_cards_correspondences, load_report_by_link, load_report_settings, load_withheld,
    save_spread_session,
)
from ootk.report import MAPPING_LABELS, build_analytical_prompt
from ootk import significator as significator_methods
from ootk.shuffle import draw_spread, has_significator_position, resolve_significator
from ootk.spreads import SPREADS, spread_positions
from ootk.visual import build_report_view, card_image_url, card_srcset, short_card_name, withheld_view

VALID_MAPPINGS = set(MAPPING_SYSTEMS)
VALID_FRAMEWORKS = {"auto", "light_descent", "soul_formation", "life_path", "post_mortem"}
VALID_DRAW_MODES = {"seed", "manual"}
VALID_OUTPUT_FORMATS = {"visual", "markdown"}
# Readings saved before 'thoth' existed stored 'golden_dawn' for what is now 'thoth' (the
# swap was always applied). New readings carry this version, so old links keep their cards.
MAPPING_VERSION = 2

app = FastAPI(title="OOTK Thoth Graphic GUI")

static_dir = BASE_DIR / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", CachedStaticFiles(directory=str(static_dir)), name="static")
app.add_middleware(CompressionMiddleware)


@app.middleware("http")
async def require_password(request: Request, call_next):
    """When APP_PASSWORD is set (e.g. on a public host), every page asks for it via HTTP
    Basic auth; any user name is accepted. Unset, the app is open as before."""
    password = os.getenv("APP_PASSWORD")
    if not password:
        return await call_next(request)
    scheme, _, encoded = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() == "basic":
        try:
            given = base64.b64decode(encoded).decode("utf-8").partition(":")[2]
        except (ValueError, UnicodeDecodeError):
            given = ""
        if secrets.compare_digest(given.encode(), password.encode()):
            return await call_next(request)
    return PlainTextResponse("Password required.", status_code=401,
                             headers={"WWW-Authenticate": 'Basic realm="ootk"'})

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

REPO_URL = "https://github.com/hampshirecottage-ai/ootk-thoth-engine"
BUG_REPORT_URL = f"{REPO_URL}/issues/new?template=bug_report.yml"
CONTACT_URL = f"{REPO_URL}/discussions"
SITE_DESCRIPTION = ("Draw a Thoth tarot spread and get its Golden Dawn dignities, decans and "
                    "Liber 777 correspondences calculated, as a prompt for your LLM to interpret.")
# Pages search engines may list (the sitemap adds today's card). Saved and shared readings stay out.
PUBLIC_PAGES = ["/", "/pick"]


def site_url(request: Request) -> str:
    """The public address, for links that must be absolute (link previews, sitemap).

    SITE_URL wins, then the address Render gives the service, then the address the request
    came in on (fine locally; behind a proxy it may say http instead of https)."""
    url = os.getenv("SITE_URL") or os.getenv("RENDER_EXTERNAL_URL") or str(request.base_url)
    return url.rstrip("/")


@app.exception_handler(HTTPException)
async def form_error_page(request: Request, exc: HTTPException):
    """A browser posting the form gets a readable page with a way back; API clients keep JSON."""
    if "text/html" not in request.headers.get("accept", ""):
        return await http_exception_handler(request, exc)
    return HTMLResponse(status_code=exc.status_code, content=(
        '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>Reading not shown</title><style>'
        'body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;'
        'background:#f5f4f8;color:#1d1b22;margin:0;padding:24px}'
        '@media (prefers-color-scheme:dark){body{background:#121212;color:#e0e0e0}}'
        'main{max-width:560px;margin:10vh auto}h1{color:#6b3fc4;font-size:1.3em}'
        'a{display:inline-block;background:#6b3fc4;color:#fff;padding:10px 16px;'
        'border-radius:6px;text-decoration:none;font-weight:600}'
        '.more{font-size:.9em}.more a.plain{background:none;color:inherit;padding:0;'
        'text-decoration:underline;font-weight:normal}</style></head><body><main>'
        f'<h1>This reading can&rsquo;t be shown</h1><p>{html.escape(str(exc.detail))}</p>'
        '<p><a href="/" onclick="if (history.length > 1) { history.back(); return false; }">'
        '&larr; Back to settings</a></p>'
        f'<p class="more">Think this is a mistake? <a class="plain" href="{BUG_REPORT_URL}" '
        'target="_blank" rel="noopener">Report a bug</a></p></main></body></html>'))
templates.env.globals.update(static_url=static_url, card_image_url=card_image_url,
                             card_srcset=card_srcset, bug_report_url=BUG_REPORT_URL,
                             contact_url=CONTACT_URL, site_url=site_url,
                             site_description=SITE_DESCRIPTION)


def get_db_connection():
    return psycopg.connect(**DB_CONFIG, row_factory=dict_row)


def new_seed() -> str:
    """A fresh six-digit seed, shown on the report so the reading can be repeated."""
    return str(secrets.randbelow(900000) + 100000)


def cli_command(spread_key, seed, mapping_system, framework, significator, topic) -> str:
    """The `ootk` command that repeats a seeded reading from the terminal."""
    parts = ["ootk", "--spread", spread_key, "--seed", seed, "--mapping", mapping_system,
             "--framework", framework]
    if significator:
        parts += ["--significator", significator]
    if topic:
        parts += ["--topic", topic]
    return " ".join(shlex.quote(p) for p in parts)


def reading_export(session_id, spread_name, settings, significator, framework, framework_basis,
                   element_counts, spread_results, view, dignity_matrix, spatial_matrix,
                   withheld=None):
    """The whole reading as plain JSON data, for the report's JSON download."""
    reading = {
        "session_id": session_id,
        "spread": spread_name,
        "settings": {k: v for k, v in settings.items() if k not in ("output_format", "selected_cards")},
        "significator": significator,
        "framework": framework,
        "framework_basis": framework_basis,
        "element_counts": element_counts,
        "cards": [
            dict(item["card_data"], position_number=item["position_number"],
                 position_name=item["position_name"], primary_element=card["element"],
                 dignified=card["dignified"])
            for item, card in zip(spread_results, view["card_details"])
        ],
        "dignities": dignity_matrix,
        "aspects": spatial_matrix,
        "withheld": [row["title"] for row in withheld["cards"]] if withheld else [],
    }
    # Round-trip through json so dates, decimals and the like become plain strings.
    return json.loads(json.dumps(reading, default=str))


# The start page shows this reading before asking for any settings. The seed is a throwaway
# number, so the sample holds no personal data, and the same seed always draws the same cards.
SAMPLE_SETTINGS = {
    "spread_key": "3", "seed": "12345", "topic": "", "significator": "", "framework": "auto",
    "mapping_system": DEFAULT_MAPPING, "draw_mode": "seed", "output_format": "visual",
}
_sample_cache = {}


def sample_reading(conn, deck):
    """The start page's sample: drawn and analysed once per process, then reused. None when
    the deck can't produce it (an empty or partial database), so the page still renders."""
    if "sample" in _sample_cache:
        return _sample_cache["sample"]
    if len(deck) != 78:            # another deck size would draw other cards for this seed
        return None
    try:
        positions = spread_positions(SAMPLE_SETTINGS["spread_key"])
        card_titles, _ = draw_spread(deck, SAMPLE_SETTINGS["seed"], positions, None)
        r = run_reading(conn, SAMPLE_SETTINGS, card_titles,
                        "None (spread has no significator position)", deck)
    except (HTTPException, LookupError, ValueError):
        return None
    sample = {
        "seed": SAMPLE_SETTINGS["seed"],
        "spread_name": r["spread_name"],
        "mapping_label": MAPPING_LABELS[SAMPLE_SETTINGS["mapping_system"]],
        "cards": [{"position": item["position_name"], **item["card_data"]}
                  for item in r["spread_results"]],
        "dignities": r["dignity_matrix"],
        "prompt": r["analytical_prompt"],
        "url": share_path(SAMPLE_SETTINGS),
    }
    _sample_cache["sample"] = sample
    return sample


def seeded_draw(deck, seed, spread_key, significator):
    """The cards `seed` draws for the spread, exactly as `ootk --seed` does.
    Returns (card_titles, significator_label)."""
    positions = spread_positions(spread_key)
    sig_card = resolve_significator(deck, significator)
    if significator and sig_card is None:
        raise HTTPException(status_code=400,
                            detail=f"Significator {significator!r} was not found in the deck. "
                                   f"Pick a title from the list, e.g. 'Queen of Cups' "
                                   f"or 'Princess of Disks'.")
    if sig_card is None and has_significator_position(positions):
        raise HTTPException(status_code=400,
                            detail=f"{SPREADS[spread_key]['name']} needs a significator. "
                                   f"Choose one under Significator on the start page.")
    card_titles, pinned = draw_spread(deck, seed, positions, sig_card)
    return card_titles, (sig_card["title"] if pinned else "None (spread has no significator position)")


def share_path(settings) -> str:
    """The /reading address that redraws a seeded reading. It carries the seed and settings
    but never the topic, so a shared link doesn't reveal what the question was."""
    params = {"seed": settings["seed"], "spread": settings["spread_key"],
              "system": settings["mapping_system"]}
    if settings["framework"] != "auto":
        params["framework"] = settings["framework"]
    if settings["significator"]:
        params["significator"] = settings["significator"]
    return "/reading?" + urlencode(params)


def settings_page(request: Request, name: str, mode: str):
    """Sync endpoint body: FastAPI executes in threadpool to prevent blocking the event loop."""
    with get_db_connection() as conn:
        cards = fetch_all_cards(conn)
        sample = sample_reading(conn, cards) if mode == "seed" else None
    todays_card = None
    if mode == "seed" and cards:
        # Same draw as /day/<today>, so the link names the card it opens.
        titles, _ = draw_spread(cards, utc_today().isoformat(), spread_positions("1"))
        todays_card = short_card_name(titles[0])
    return templates.TemplateResponse(
        request=request,
        name=name,
        context={
            "cards": cards,
            "mode": mode,
            "sample": sample,
            "todays_card": todays_card,
            "spreads": SPREADS,
            "positions": {key: spread_positions(key) for key in SPREADS},
            "sig_ranks": significator_methods.RANKS,
            "sig_suits": significator_methods.SUITS,
            "birth_spans": significator_methods.BIRTH_SPANS,
        }
    )


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt(request: Request):
    """Search engines may list the start, pick and card-of-the-day pages, never saved or
    shared readings or the API."""
    return ("User-agent: *\n"
            "Disallow: /report/\n"
            "Disallow: /generate_report\n"
            "Disallow: /reading\n"
            "Disallow: /docs\n"
            "Disallow: /redoc\n"
            "Disallow: /openapi.json\n"
            f"\nSitemap: {site_url(request)}/sitemap.xml\n")


@app.get("/sitemap.xml")
def sitemap_xml(request: Request):
    base = site_url(request)
    pages = PUBLIC_PAGES + [f"/day/{utc_today().isoformat()}"]
    urls = "".join(f"<url><loc>{html.escape(base + path)}</loc></url>" for path in pages)
    return Response('<?xml version="1.0" encoding="UTF-8"?>'
                    f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>',
                    media_type="application/xml")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Browsers and crawlers ask for /favicon.ico whatever the page links to."""
    return FileResponse(static_dir / "site" / "favicon.ico", media_type="image/x-icon",
                        headers={"Cache-Control": "public, max-age=86400"})


@app.get("/", response_class=HTMLResponse)
def main_gui(request: Request):
    """Start page: a sample reading and the settings. '/?seed=...' opens that shared reading."""
    if request.query_params.get("seed"):
        return RedirectResponse(f"/reading?{request.url.query}", status_code=307)
    return settings_page(request, "index.html", "seed")


@app.get("/pick", response_class=HTMLResponse)
def pick_gui(request: Request):
    """Pick by hand: the same settings plus the spread board and card catalog."""
    return settings_page(request, "pick.html", "manual")


@app.post("/generate_report", response_class=HTMLResponse)
def generate_report(
    request: Request,
    spread_key: str = Form(...),
    topic: str = Form(""),
    significator: str = Form(""),
    framework: str = Form("auto"),
    mapping_system: str = Form(DEFAULT_MAPPING),
    selected_cards: str = Form(""),
    draw_mode: str = Form("manual"),
    seed: str = Form(""),
    output_format: str = Form("visual"),
):
    """Builds the spread, executes geometric/vector analysis, and renders the synthesis report.

    draw_mode 'seed' draws the cards from `seed` exactly as `ootk --seed` does (a blank seed
    gets a fresh one); 'manual' uses the comma-separated `selected_cards`.
    output_format 'visual' renders the summary-first report; 'markdown' returns the
    analytical prompt as a .md download.
    """
    topic = topic.strip()
    significator = significator.strip()
    spread_key = spread_key.strip()
    framework = framework.strip()
    mapping_system = mapping_system.strip()
    draw_mode = draw_mode.strip()
    seed = seed.strip()
    output_format = output_format.strip()

    # --- Domain Input Validation ---
    if spread_key not in SPREADS:
        raise HTTPException(status_code=400, detail=f"Unknown spread key: {spread_key!r}.")
    if mapping_system not in VALID_MAPPINGS:
        raise HTTPException(status_code=400, detail=f"Unknown mapping system: {mapping_system!r}.")
    if framework not in VALID_FRAMEWORKS:
        raise HTTPException(status_code=400, detail=f"Unknown framework: {framework!r}.")
    if draw_mode not in VALID_DRAW_MODES:
        raise HTTPException(status_code=400, detail=f"Unknown draw mode: {draw_mode!r}.")
    if output_format not in VALID_OUTPUT_FORMATS:
        raise HTTPException(status_code=400, detail=f"Unknown output format: {output_format!r}.")

    selected_spread = SPREADS[spread_key]
    positions = spread_positions(spread_key)
    significator_label = significator

    with get_db_connection() as conn:
        deck = None
        if draw_mode == "seed":
            seed = seed or new_seed()
            deck = fetch_all_cards(conn)
            card_titles, significator_label = seeded_draw(deck, seed, spread_key, significator)
        else:
            seed = ""
            card_titles = [c.strip() for c in selected_cards.split(",") if c.strip()]
            significator_label = (card_titles[0] if card_titles and has_significator_position(positions)
                                  else "None (spread has no significator position)")
            if not card_titles:
                raise HTTPException(status_code=400, detail="No card titles were provided.")

            if len(card_titles) != len(positions):
                raise HTTPException(
                    status_code=400,
                    detail=f"'{selected_spread['name']}' requires {len(positions)} cards; received {len(card_titles)}."
                )

            lowered = [t.lower() for t in card_titles]
            if len(set(lowered)) != len(lowered):
                raise HTTPException(status_code=400, detail="Duplicate cards are not allowed in a single spread draw.")

        settings = {
            "spread_key": spread_key, "topic": topic, "significator": significator,
            "framework": framework, "mapping_system": mapping_system, "draw_mode": draw_mode,
            "seed": seed, "output_format": "visual",
            "selected_cards": ",".join(card_titles) if draw_mode == "manual" else "",
        }
        reading = run_reading(conn, settings, card_titles, significator_label, deck)

        source = f"PRNG Seed: {seed}" if seed else "GUI Selection"
        # The report's address: random, so readings can't be found by counting session numbers.
        link = secrets.token_urlsafe(16)
        session_id = save_spread_session(
            conn,
            selected_spread["name"],
            topic,
            f"{source} | Mapping: {mapping_system} | Framework: {reading['macro_framework']}",
            significator_label,
            reading["spread_results"],
            reading["dignity_matrix"],
            report_settings=dict(settings, card_titles=card_titles, significator_label=significator_label,
                                 link=link, mapping_version=MAPPING_VERSION),
        )
        # An older database saves the reading without its settings; then there is no link.
        linked = bool(session_id) and (load_report_settings(conn, session_id) or {}).get("link") == link

    if output_format == "markdown":
        return PlainTextResponse(
            reading["analytical_prompt"],
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="ootk_report_{session_id or "latest"}.md"'},
        )
    if linked:
        # Post/Redirect/Get: the report gets its own link, and reloading it saves nothing.
        return RedirectResponse(f"/report/{link}", status_code=303)
    return render_report(request, session_id, settings, reading)


# Short names accepted in shared links, e.g. ?system=gd.
SYSTEM_ALIASES = {"gd": "golden_dawn", "fe": "french_egyptian"}
SHARED_SEED_MAX = 64


@app.get("/reading", response_class=HTMLResponse)
def shared_reading(request: Request, seed: str = "", spread: str = "",
                   system: str = DEFAULT_MAPPING, framework: str = "auto", significator: str = ""):
    """A seeded reading rebuilt from its link, e.g. /reading?seed=918851&spread=12&system=thoth.

    The same seed and settings always draw the same cards, so the link alone is the reading.
    Nothing is saved, and no saved reading can be reached this way: those keep their random
    /report/<link> addresses.
    """
    seed, spread, framework, significator = seed.strip(), spread.strip(), framework.strip(), significator.strip()
    system = SYSTEM_ALIASES.get(system.strip().lower(), system.strip().lower())
    if not seed:
        raise HTTPException(status_code=400, detail="This link has no seed, so there are no cards to draw.")
    if len(seed) > SHARED_SEED_MAX:
        raise HTTPException(status_code=400, detail=f"A seed can be at most {SHARED_SEED_MAX} characters.")
    if spread not in SPREADS:
        raise HTTPException(status_code=400, detail=f"Unknown spread: {spread!r}. Use a number from 1 to {len(SPREADS)}.")
    if system not in VALID_MAPPINGS:
        raise HTTPException(status_code=400, detail=f"Unknown system: {system!r}. Use thoth, gd or french_egyptian.")
    if framework not in VALID_FRAMEWORKS:
        raise HTTPException(status_code=400, detail=f"Unknown framework: {framework!r}.")
    settings = {
        "spread_key": spread, "topic": "", "significator": significator, "framework": framework,
        "mapping_system": system, "draw_mode": "seed", "seed": seed, "output_format": "visual",
        "selected_cards": "",
    }
    with get_db_connection() as conn:
        deck = fetch_all_cards(conn)
        card_titles, significator_label = seeded_draw(deck, seed, spread, significator)
        reading = run_reading(conn, settings, card_titles, significator_label, deck)
    return render_report(request, None, settings, reading, shared=True)


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


@app.get("/today")
def card_of_the_day_today():
    """Today's card (UTC). Redirects so each day keeps its own address."""
    return RedirectResponse(f"/day/{utc_today().isoformat()}", status_code=307)


@app.get("/day/{day}", response_class=HTMLResponse)
def card_of_the_day(request: Request, day: str):
    """The card of the day: the top card of the deck shuffled with the ISO date as the seed,
    the same card `ootk --seed 2026-10-03 --spread 1` draws."""
    try:
        when = date.fromisoformat(day)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"{day!r} is not a date. Use the form 2026-10-03.")
    if when.isoformat() != day:
        raise HTTPException(status_code=404, detail=f"{day!r} is not a date. Use the form 2026-10-03.")
    today = utc_today()
    # A day ahead of UTC is allowed, so it is "today" everywhere on Earth.
    if when > today + timedelta(days=1):
        raise HTTPException(status_code=404, detail="That day's card hasn't been drawn yet.")
    settings = {
        "spread_key": "1", "topic": "", "significator": "", "framework": "auto",
        "mapping_system": DEFAULT_MAPPING, "draw_mode": "seed", "seed": day,
        "output_format": "visual", "selected_cards": "",
    }
    with get_db_connection() as conn:
        deck = fetch_all_cards(conn)
        card_titles, significator_label = seeded_draw(deck, day, "1", "")
        reading = run_reading(conn, settings, card_titles, significator_label, deck)
    card = reading["spread_results"][0]["card_data"]
    title = card["title"]
    return templates.TemplateResponse(
        request=request,
        name="day.html",
        context={
            "day": when,
            "is_today": when == today,
            "card": card,
            "name": short_card_name(title),
            "image": card_image_url(title, "full"),
            "prompt": reading["analytical_prompt"],
            "reading_url": share_path(settings),
            "previous": (when - timedelta(days=1)).isoformat(),
            "next": (when + timedelta(days=1)).isoformat() if when < today else None,
            "today": today.isoformat(),
        },
    )


@app.get("/report/{link}", response_class=HTMLResponse)
def show_report(request: Request, link: str):
    """A saved reading's report, rebuilt from the cards and settings stored with the session."""
    with get_db_connection() as conn:
        found = load_report_by_link(conn, link)
        if not found:
            raise HTTPException(status_code=404, detail=(
                "No reading has this link. Check that the whole address was copied; readings "
                "saved before links were random get theirs from "
                "database/migrations/add_report_links.sql."))
        session_id, stored = found
        stored.pop("link", None)
        if stored.pop("mapping_version", 1) < 2 and stored.get("mapping_system") == "golden_dawn":
            stored["mapping_system"] = "thoth"
        card_titles = stored.pop("card_titles")
        significator_label = stored.pop("significator_label")
        reading = run_reading(conn, stored, card_titles, significator_label)
    return render_report(request, session_id, stored, reading)


def run_reading(conn, settings, card_titles, significator_label, deck=None):
    """Looks up the drawn cards and runs every analysis. Returns the pieces the report needs."""
    spread_key, mapping_system = settings["spread_key"], settings["mapping_system"]
    selected_spread = SPREADS[spread_key]
    positions = spread_positions(spread_key)
    spread_results = []
    rows = fetch_cards_correspondences(conn, card_titles, system=mapping_system)
    for idx, title in enumerate(card_titles):
        card_data = rows.get(title)
        if not card_data:
            raise HTTPException(
                status_code=400,
                detail=f"Card title {title!r} was not found in the database."
            )
        spread_results.append({
            "position_number": idx + 1,
            "position_name": positions[idx],
            "card_data": card_data
        })

    element_counts = analyze_elemental_balance(spread_results)
    dignity_matrix = calculate_elemental_dignities(spread_results, spread_key)
    spatial_matrix = analyze_spatial_vectors(spread_results, spread_key)
    spatial_dist, spatial_details = analyze_hebrew_spatial_distribution(spread_results)
    solid_counts, topology_details, dual_pairings = analyze_platonic_topology(spread_results)
    macro_framework, framework_basis = evaluate_macro_framework(spread_results,
                                                                forced_framework=settings["framework"])
    withheld = load_withheld(conn, deck or fetch_all_cards(conn), card_titles, mapping_system)

    analytical_prompt = build_analytical_prompt(
        spread_name=selected_spread["name"],
        query_prompt=settings["topic"],
        significator=significator_label,
        seed_val=settings["seed"] or "Graphical Selection",
        spread_results=spread_results,
        element_counts=element_counts,
        dignity_matrix=dignity_matrix,
        spatial_matrix=spatial_matrix,
        spatial_dist=spatial_dist,
        spatial_details=spatial_details,
        solid_counts=solid_counts,
        topology_details=topology_details,
        dual_pairings=dual_pairings,
        macro_framework=macro_framework,
        mapping_system=mapping_system,
        framework_basis=framework_basis,
        withheld=withheld,
    )
    return {
        "spread_name": selected_spread["name"], "significator_label": significator_label,
        "spread_results": spread_results, "element_counts": element_counts,
        "dignity_matrix": dignity_matrix, "spatial_matrix": spatial_matrix,
        "spatial_dist": spatial_dist, "spatial_details": spatial_details,
        "solid_counts": solid_counts, "topology_details": topology_details,
        "dual_pairings": dual_pairings, "macro_framework": macro_framework,
        "framework_basis": framework_basis, "withheld": withheld,
        "analytical_prompt": analytical_prompt,
    }


def render_report(request, session_id, settings, r, shared=False):
    """The visual report for a reading from run_reading()."""
    spread_key, seed = settings["spread_key"], settings["seed"]
    mapping_system, framework = settings["mapping_system"], settings["framework"]
    view = build_report_view(spread_key, r["spread_results"], r["element_counts"], r["dignity_matrix"],
                             r["spatial_matrix"], r["macro_framework"], r["framework_basis"])
    return templates.TemplateResponse(
        request=request,
        name="report.html",
        context={
            "session_id": session_id,
            "spread_name": r["spread_name"],
            "topic": settings["topic"],
            "prompt": r["analytical_prompt"],
            "spread_results": r["spread_results"],
            "dignity_matrix": r["dignity_matrix"],
            "element_counts": r["element_counts"],
            "mapping_system": mapping_system,
            "mapping_label": MAPPING_LABELS[mapping_system],
            "significator": r["significator_label"],
            "seed": seed,
            "settings": settings,
            "shared": shared,
            "share_path": share_path(settings) if seed else "",
            "cli_command": cli_command(spread_key, seed, mapping_system, framework,
                                       settings["significator"], settings["topic"]) if seed else "",
            "spatial_details": r["spatial_details"],
            "spatial_dist": r["spatial_dist"],
            "solid_counts": r["solid_counts"],
            "topology_details": r["topology_details"],
            "dual_pairings": r["dual_pairings"],
            "withheld": withheld_view(r["withheld"]),
            "view": view,
            "reading": reading_export(session_id, r["spread_name"], settings, r["significator_label"],
                                      r["macro_framework"], r["framework_basis"], r["element_counts"],
                                      r["spread_results"], view, r["dignity_matrix"],
                                      r["spatial_matrix"], r["withheld"]),
        }
    )

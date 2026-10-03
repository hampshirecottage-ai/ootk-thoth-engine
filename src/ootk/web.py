"""FastAPI web GUI: `uvicorn ootk.web:app`."""
import base64
import html
import json
import os
import secrets
import shlex

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
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
    DB_CONFIG, fetch_all_cards, fetch_cards_correspondences, load_report_by_link, load_report_settings, load_withheld,
    save_spread_session,
)
from ootk.report import build_analytical_prompt
from ootk.shuffle import draw_spread, resolve_significator
from ootk.spreads import SPREADS, spread_positions
from ootk.visual import build_report_view, card_image_url, card_srcset, withheld_view

VALID_MAPPINGS = {"golden_dawn", "french_egyptian"}
VALID_FRAMEWORKS = {"auto", "light_descent", "soul_formation", "life_path", "post_mortem"}
VALID_DRAW_MODES = {"seed", "manual"}
VALID_OUTPUT_FORMATS = {"visual", "markdown"}
MAPPING_LABELS = {
    "golden_dawn": "Golden Dawn / English System (Liber 777)",
    "french_egyptian": "French / Egyptian System (Lévi / Papus / Wirth)",
}

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
        'border-radius:6px;text-decoration:none;font-weight:600}</style></head><body><main>'
        f'<h1>This reading can&rsquo;t be shown</h1><p>{html.escape(str(exc.detail))}</p>'
        '<p><a href="/" onclick="if (history.length > 1) { history.back(); return false; }">'
        '&larr; Back to settings</a></p></main></body></html>'))
templates.env.globals.update(static_url=static_url, card_image_url=card_image_url,
                             card_srcset=card_srcset)


def get_db_connection():
    return psycopg.connect(**DB_CONFIG, row_factory=dict_row)


def new_seed() -> str:
    """A fresh six-digit seed, shown on the report so the reading can be repeated."""
    return str(secrets.randbelow(900000) + 100000)


def cli_command(spread_key, seed, mapping_system, framework, significator, topic) -> str:
    """The `ootk` command that repeats a seeded reading from the terminal."""
    parts = ["ootk", "--spread", spread_key, "--seed", seed, "--mapping", mapping_system,
             "--framework", framework, "--significator", significator]
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


@app.get("/", response_class=HTMLResponse)
def main_gui(request: Request):
    """Sync endpoint: FastAPI executes in threadpool to prevent blocking the event loop."""
    with get_db_connection() as conn:
        cards = fetch_all_cards(conn)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "cards": cards,
            "spreads": SPREADS,
            "positions": {key: spread_positions(key) for key in SPREADS},
        }
    )


@app.post("/generate_report", response_class=HTMLResponse)
def generate_report(
    request: Request,
    spread_key: str = Form(...),
    topic: str = Form(""),
    significator: str = Form("Knight of Swords"),
    framework: str = Form("auto"),
    mapping_system: str = Form("golden_dawn"),
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
    significator = significator.strip() or "Knight of Swords"
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
            sig_card = resolve_significator(deck, significator)
            if sig_card is None:
                raise HTTPException(status_code=400,
                                    detail=f"Significator {significator!r} was not found in the deck. "
                                           f"Pick a title from the list, e.g. 'Knight of Swords' "
                                           f"or 'Princess of Disks'.")
            card_titles, pinned = draw_spread(deck, seed, positions, sig_card)
            significator_label = (sig_card["title"] if pinned
                                  else "None (spread has no significator position)")
        else:
            seed = ""
            card_titles = [c.strip() for c in selected_cards.split(",") if c.strip()]
            has_sig_position = bool(positions) and "significator" in positions[0].lower()
            significator_label = (card_titles[0] if card_titles and has_sig_position
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
                                 link=link),
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


def render_report(request, session_id, settings, r):
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

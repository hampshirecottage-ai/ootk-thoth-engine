"""FastAPI web GUI: `uvicorn ootk.web:app`."""
import json
import secrets
import shlex

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import psycopg
from psycopg.rows import dict_row

from ootk import PROJECT_ROOT as BASE_DIR
from ootk.analysis import (
    analyze_elemental_balance, analyze_hebrew_spatial_distribution, analyze_platonic_topology,
    analyze_spatial_vectors, calculate_elemental_dignities, evaluate_macro_framework,
)
from ootk.db import DB_CONFIG, fetch_all_cards, fetch_cards_correspondences, save_spread_session
from ootk.report import build_analytical_prompt
from ootk.shuffle import draw_spread, resolve_significator
from ootk.spreads import SPREADS, spread_positions
from ootk.visual import build_report_view

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
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


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
                   element_counts, spread_results, view, dignity_matrix, spatial_matrix):
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
        if draw_mode == "seed":
            seed = seed or new_seed()
            deck = fetch_all_cards(conn)
            sig_card = resolve_significator(deck, significator)
            if sig_card is None:
                raise HTTPException(status_code=400,
                                    detail=f"Significator {significator!r} was not found in the deck.")
            card_titles, pinned = draw_spread(deck, seed, positions, sig_card)
            significator_label = (sig_card["title"] if pinned
                                  else "None (spread has no significator position)")
        else:
            seed = ""
            card_titles = [c.strip() for c in selected_cards.split(",") if c.strip()]
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

        # --- Build Spread & Execute Analytical Calculations ---
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
        macro_framework, framework_basis = evaluate_macro_framework(spread_results, forced_framework=framework)

        analytical_prompt = build_analytical_prompt(
            spread_name=selected_spread["name"],
            query_prompt=topic,
            significator=significator_label,
            seed_val=seed or "Graphical Selection",
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
            framework_basis=framework_basis
        )

        source = f"PRNG Seed: {seed}" if seed else "GUI Selection"
        session_id = save_spread_session(
            conn,
            selected_spread["name"],
            topic,
            f"{source} | Mapping: {mapping_system} | Framework: {macro_framework}",
            significator_label,
            spread_results,
            dignity_matrix
        )

    if output_format == "markdown":
        return PlainTextResponse(
            analytical_prompt,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="ootk_report_{session_id or "latest"}.md"'},
        )

    view = build_report_view(spread_key, spread_results, element_counts, dignity_matrix,
                             spatial_matrix, macro_framework, framework_basis)
    settings = {
        "spread_key": spread_key, "topic": topic, "significator": significator,
        "framework": framework, "mapping_system": mapping_system, "draw_mode": draw_mode,
        "seed": seed, "output_format": "visual",
        "selected_cards": ",".join(card_titles) if draw_mode == "manual" else "",
    }
    return templates.TemplateResponse(
        request=request,
        name="report.html",
        context={
            "session_id": session_id,
            "spread_name": selected_spread["name"],
            "topic": topic,
            "prompt": analytical_prompt,
            "spread_results": spread_results,
            "dignity_matrix": dignity_matrix,
            "element_counts": element_counts,
            "mapping_system": mapping_system,
            "mapping_label": MAPPING_LABELS[mapping_system],
            "significator": significator_label,
            "seed": seed,
            "settings": settings,
            "cli_command": cli_command(spread_key, seed, mapping_system, framework, significator, topic) if seed else "",
            "spatial_details": spatial_details,
            "spatial_dist": spatial_dist,
            "solid_counts": solid_counts,
            "topology_details": topology_details,
            "dual_pairings": dual_pairings,
            "view": view,
            "reading": reading_export(session_id, selected_spread["name"], settings, significator_label,
                                      macro_framework, framework_basis, element_counts, spread_results,
                                      view, dignity_matrix, spatial_matrix),
        }
    )

import html
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

from src.spread_engine import (
    DB_CONFIG, SPREADS, fetch_all_cards, fetch_card_correspondences,
    analyze_elemental_balance, calculate_elemental_dignities,
    analyze_spatial_vectors, analyze_hebrew_spatial_distribution,
    analyze_platonic_topology, evaluate_macro_framework,
    build_analytical_prompt, save_spread_session
)

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

VALID_MAPPINGS = {"golden_dawn", "french_egyptian"}
VALID_FRAMEWORKS = {"auto", "light_descent", "soul_formation", "life_path", "post_mortem"}

app = FastAPI(title="OOTK Thoth Graphic GUI")

static_dir = BASE_DIR / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def get_db_connection():
    return psycopg.connect(**DB_CONFIG, row_factory=dict_row)


def resolve_positions(spread: dict) -> list:
    """Returns the ordered position labels for a spread, flattening multi-operation spreads."""
    if "operations" in spread:
        positions = []
        for idx_op, op_key in enumerate(spread["operations"], start=1):
            for p in SPREADS[op_key]["positions"]:
                positions.append(f"[Op {idx_op}] {p}")
        return positions
    return list(spread.get("positions", []))


@app.get("/", response_class=HTMLResponse)
def main_gui(request: Request):
    """Sync endpoint: FastAPI executes in threadpool to prevent blocking the event loop."""
    with get_db_connection() as conn:
        cards = fetch_all_cards(conn)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"cards": cards, "spreads": SPREADS}
    )


@app.post("/generate_report", response_class=HTMLResponse)
def generate_report(
    request: Request,
    spread_key: str = Form(...),
    topic: str = Form(""),
    significator: str = Form("Knight of Swords"),
    framework: str = Form("auto"),
    mapping_system: str = Form("golden_dawn"),
    selected_cards: str = Form(...)
):
    """Builds the spread, executes geometric/vector analysis, and renders the synthesis report."""
    topic = topic.strip()
    significator = significator.strip() or "Knight of Swords"
    spread_key = spread_key.strip()
    framework = framework.strip()
    mapping_system = mapping_system.strip()

    # --- Domain Input Validation ---
    if spread_key not in SPREADS:
        raise HTTPException(status_code=400, detail=f"Unknown spread key: {spread_key!r}.")
    if mapping_system not in VALID_MAPPINGS:
        raise HTTPException(status_code=400, detail=f"Unknown mapping system: {mapping_system!r}.")
    if framework not in VALID_FRAMEWORKS:
        raise HTTPException(status_code=400, detail=f"Unknown framework: {framework!r}.")

    card_titles = [c.strip() for c in selected_cards.split(",") if c.strip()]
    if not card_titles:
        raise HTTPException(status_code=400, detail="No card titles were provided.")

    selected_spread = SPREADS[spread_key]
    positions = resolve_positions(selected_spread)

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
    with get_db_connection() as conn:
        for idx, title in enumerate(card_titles):
            card_data = fetch_card_correspondences(conn, title, system=mapping_system)
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
            significator=significator,
            seed_val="Graphical Selection",
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

        session_id = save_spread_session(
            conn,
            selected_spread["name"],
            topic,
            f"GUI Selection | Mapping: {mapping_system} | Framework: {macro_framework}",
            significator,
            spread_results,
            dignity_matrix
        )

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
            "mapping_system": mapping_system
        }
    )

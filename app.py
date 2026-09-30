from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import psycopg
from psycopg.rows import dict_row
import os
import json
from dotenv import load_dotenv

from src import ootk_engine
from src.spread_engine import (
    DB_CONFIG, SPREADS, fetch_all_cards, fetch_card_correspondences,
    analyze_elemental_balance, calculate_elemental_dignities,
    evaluate_macro_framework, build_analytical_prompt, save_spread_session
)

load_dotenv()

app = FastAPI(title="OOTK Thoth Graphic GUI")

if not os.path.exists("static"):
    os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

def get_db_connection():
    return psycopg.connect(**DB_CONFIG, row_factory=dict_row)

@app.get("/", response_class=HTMLResponse)
async def main_gui(request: Request):
    with get_db_connection() as conn:
        cards = fetch_all_cards(conn)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"cards": cards, "spreads": SPREADS}
    )

@app.post("/generate_report", response_class=HTMLResponse)
async def generate_report(
    request: Request,
    spread_key: str = Form(...),
    topic: str = Form(""),
    significator: str = Form("Knight of Swords"),
    framework: str = Form("auto"),
    mapping_system: str = Form("golden_dawn"),
    selected_cards: str = Form(...)
):
    card_titles = [c.strip() for c in selected_cards.split(",") if c.strip()]
    selected_spread = SPREADS.get(spread_key, SPREADS["1"])
    positions = selected_spread.get("positions", [f"Pos {i+1}" for i in range(len(card_titles))])

    spread_results = []
    with get_db_connection() as conn:
        for idx, title in enumerate(card_titles):
            card_data = fetch_card_correspondences(conn, title, system=mapping_system)
            pos_name = positions[idx] if idx < len(positions) else f"Position {idx+1}"
            spread_results.append({
                "position_number": idx + 1,
                "position_name": pos_name,
                "card_data": card_data
            })

        element_counts = analyze_elemental_balance(spread_results)
        dignity_matrix = calculate_elemental_dignities(spread_results)
        macro_framework = evaluate_macro_framework(spread_results, forced_framework=framework)

        analytical_prompt = build_analytical_prompt(
            selected_spread["name"], topic, significator, "Graphical Selection",
            spread_results, element_counts, dignity_matrix, macro_framework, mapping_system=mapping_system
        )

        session_id = save_spread_session(
            conn, selected_spread["name"], topic, f"GUI Selection | Mapping: {mapping_system} | Framework: {macro_framework}", significator, spread_results
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

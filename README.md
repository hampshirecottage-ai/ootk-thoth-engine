# OOTK Thoth Engine

A high-precision Hermetic tarot calculation and analytical engine built around the 78-card Thoth Tarot deck, Liber 777 correspondence mappings, and Tree of Life spatial-platonic geometry.

The engine automates and formalizes the Opening of the Key (OOTK) master pipeline, evaluating quantitative elemental dignities, Sefer Yetzirah dimensional coordinates, dynamic Gematria reduction matrices, Platonic solid dual inversions, and decanic zodiacal dynamics.

---

## Key Features

- 4-Operation OOTK Master Pipeline:
  - Operation 1 (Core & Climax): Analyzes core nature, subconscious psychological roots, environmental conditions, and material climax.
  - Operation 2 (Zodiacal Houses): Evaluates spatial distribution across the 12 Astrological Houses.
  - Operation 3 (Zodiacal Progression): Tracks developmental progression across the 12 signs of the Zodiac (Aries through Pisces).
  - Operation 4 (Decanic Cycle): Processes complete structural closure across all 36 Decans.
- Liber 777 & Cabbalistic Calculation:
  - Dynamic Gematria matrix mapping and reduction formulas.
  - Multi-layer elemental vector scoring (Fire, Water, Air, Earth).
  - Hebrew letter path attributions and Tree of Life topological coordinates.
  - PRNG deck shuffling with Fisher–Yates algorithms and Linear Congruential Generators.
- Robust Persistence & Reporting:
  - PostgreSQL 16+ Data Layer: Structured relational schema for operation sessions, card pulls, and geometry.
  - Rich CLI: Terminal interface with styled visual tables and audit logging.
  - FastAPI Web Server: Interactive API endpoints and rendered SVG/HTML report dashboards.

---

## Architectural Layout

ootk-thoth-engine/
├── app/                      # FastAPI Web Application
│   ├── routes/               # API endpoints & session views
│   ├── templates/            # Jinja2 HTML/SVG dashboards
│   └── main.py               # Application entry point
├── db/                       # Database Schema & Seed Data
│   ├── schema.sql            # Core relational DDL & indexes
│   └── seed.sql              # Static reference data (cards, geometries)
├── scripts/                  # CLI Operational Tools
│   ├── execute.py            # Primary pipeline execution script
│   ├── view_output.py        # CLI log and session renderer
│   └── prng_shuffler.py      # LCG & Fisher–Yates engine
├── .env.example              # Environment variable template
├── .gitignore                # Git untracked pattern rules
├── requirements.txt          # Python dependency pin manifest
└── README.md                 # Project documentation

---

## Tech Stack & Prerequisites

- Core Runtime: Python 3.12+
- Database: PostgreSQL 16+
- Primary Dependencies: FastAPI, Uvicorn, Jinja2, Psycopg 3, Python-Dotenv, Rich

---

## Quick Start Guide

### 1. Repository Setup

Clone the repository and navigate into the project directory:

git clone git@github.com:hampshirecottage-ai/ootk-thoth-engine.git
cd ootk-thoth-engine

### 2. Environment Configuration

Create and activate an isolated virtual environment:

python3 -m venv venv
source venv/bin/activate

Install core dependencies:

pip install -r requirements.txt

### 3. Database Initialization

1. Create a local environment file from the template:
   cp .env.example .env

2. Configure your local PostgreSQL connection settings in .env:
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=my_tarot_db
   DB_USER=postgres
   DB_PASSWORD=your_password_here

3. Initialize the database schema and populate reference mappings:
   createdb -U postgres -h localhost my_tarot_db
   psql -U postgres -h localhost -d my_tarot_db -f db/schema.sql
   psql -U postgres -h localhost -d my_tarot_db -f db/seed.sql

---

## Execution Workflows

### Command Line Interface (CLI)

Run an automated OOTK pipeline operation with custom PRNG seeding:

python scripts/execute.py --spread ootk_4op --seed 777-7 --significator "Knight of Swords"

Render detailed session results directly to the terminal:

python scripts/view_output.py --latest

### Interactive Web Server

Launch the local FastAPI development server:

uvicorn app.main:app --reload --port 8000

Open your browser to http://localhost:8000 to inspect interactive visual dashboards and API documentation at http://localhost:8000/docs.

---

## Database Schema Model

┌──────────────────┐        ┌──────────────────┐        ┌─────────────────────┐
│  tarot_sessions  │ 1    * │   spread_pulls   │ 1    * │ session_card_pulls  │
├──────────────────┤────────┼──────────────────┤────────┼─────────────────────┤
│ session_id (PK)  │        │ spread_id (PK)   │        │ pull_id (PK)        │
│ operation_type   │        │ session_id (FK)  │        │ session_id (FK)     │
│ significator     │        │ spread_name      │        │ spread_id (FK)      │
│ created_at       │        │ pull_order       │        │ card_id (FK)        │
└──────────────────┘        └──────────────────┘        │ position_index      │
                                                        │ is_dignified        │
                                                        └──────────┬──────────┘
                                                                   │ *
                                                                   │
                                                                   │ 1
                                                        ┌──────────┴──────────┐
                                                        │     thoth_cards     │
                                                        ├─────────────────────┤
                                                        │ card_id (PK)        │
                                                        │ title               │
                                                        │ arcana_type         │
                                                        │ suit / key_scale    │
                                                        └─────────────────────┘

---

## License & Operational Directives

Distributed under the MIT License. See LICENSE for further details.

OOTK Thoth Engine

A high-precision Hermetic tarot calculation and reporting engine built around the 78-card Thoth Tarot deck, Liber 777 correspondence mappings, and Tree of Life spatial-platonic geometry.

The engine executes the full Opening of the Key (OOTK) master pipeline, evaluating elemental dignities, Sefer Yetzirah dimensional coordinates, Platonic solid dual inversions, and decanic zodiacal dynamics.

Features

⚬ 4-Operation OOTK Pipeline:
  ⚬ Op 1: Core Nature, Psychological Basis, Environmental Factors, and Final Synthesis.
  ⚬ Op 2: 12 Astrological Houses (Ascendant, Asset, Mind, Home, etc.).
  ⚬ Op 3: 12 Zodiacal Progression Paths (Aries through Pisces).
  ⚬ Op 4: 36 Decanic Zodiacal Cycle.
⚬ Liber 777 & Cabbalistic Engine: Dynamic PRNG deck shuffling, dynamic Gematria matrix reduction, Hebrew letter paths, and elemental vector scoring.
⚬ PostgreSQL Persistence: Structured schema for storing operation sessions, card vector distributions, and analytical outputs.
⚬ Rich CLI & Modern Web UI: Execute operations directly via command line or launch the FastAPI web server for interactive reports.

Tech Stack & Requirements

⚬ Language: Python 3.12+
⚬ Database: PostgreSQL 16+
⚬ Frameworks & Core Libraries: FastAPI, Uvicorn, Jinja2, Psycopg 3, Python-Dotenv, Rich

Project Structure

ootk-thoth-engine/
├── app/                  # FastAPI web application & routes
├── db/                   # Database scripts & schema definition
│   ├── schema.sql        # Core database tables & constraints
│   └── seed.sql          # Sample data & initial setup
├── scripts/              # CLI execution scripts (execute.py, view_output.py, etc.)
├── .env.example          # Template for local environment configuration
├── .gitignore            # Git exclusion rules
├── requirements.txt      # Python dependencies
└── README.md


Getting Started

1. Clone the Repository

git clone git@github.com:hampshirecottage-ai/ootk-thoth-engine.git
cd ootk-thoth-engine


2. Environment Setup

Create and activate a virtual environment:

python3 -m venv venv
source venv/bin/activate


Install required dependencies:

pip install "fastapi[standard]" uvicorn jinja2 python-multipart psycopg[binary] python-dotenv rich


3. Database Configuration

1. Copy the environment template:
   cp .env.example .env
   
2. Update .env with your local PostgreSQL credentials:
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=ootk_db
   DB_USER=postgres
   DB_PASSWORD=your_password_here
   
3. Create the database and import the schema:
   createdb -U postgres -h localhost ootk_db
   psql -U postgres -h localhost -d ootk_db -f db/schema.sql
   

Running the Engine

CLI Execution

Run an OOTK operation pipeline directly from the command line:

python scripts/execute.py --spread ootk_4op --seed 777-7


Render HTML/SVG analytical reports:

python scripts/view_output.py


Web Application

Populate required local assets (if applicable) and launch the web server:

uvicorn app:app --reload --port 8000


Access the interactive engine at http://localhost:8000.

Contributing & License

This project is open-source and licensed under the MIT License. Contributions, bug reports, and pull requests are welcome!
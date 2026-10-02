# OOTK Thoth Engine

A Hermetic tarot calculation and analytical engine built around the 78-card Thoth deck, Liber 777 correspondences, and Tree of Life spatial/Platonic geometry.

It automates the Opening of the Key (OOTK) pipeline: elemental dignities, Hebrew letter and path attributions, Platonic solid dual inversions, and decanic zodiacal aspects. Draws are deterministic: the same seed always gives the same deck order.

---

## Features

- **Spreads 1-12**, from a single card up to the full 4-operation OOTK master pipeline (key 12):
  - Operation 1: 15-card active heap (core nature and climax)
  - Operation 2: 12 astrological houses
  - Operation 3: 12 zodiacal signs
  - Operation 4: 36 decans
- **Two mapping schemes** for tarot-to-Kabbalah attributions: `golden_dawn` and `french_egyptian`.
- **Macro frameworks**: `auto`, `light_descent`, `soul_formation`, `life_path`, `post_mortem`.
- **Deterministic PRNG shuffler** (`src/prng_shuffler.py`), shared by every entry point.
- **PostgreSQL persistence** of sessions, spreads and card pulls.
- **Three interfaces**: CLI (`src/spread_engine.py`), FastAPI web GUI (`app.py`), and a Rich terminal viewer for saved reports (`scripts/view_output.py`).

---

## Project layout

```
ootk-thoth-engine/
├── app.py                  # FastAPI web GUI (uvicorn app:app)
├── check_run.py            # Sanity-checks a saved 4-operation run (run.txt)
├── src/
│   ├── spread_engine.py    # Main engine + CLI entry point
│   ├── ootk_engine.py      # OOTK deck/config helpers
│   ├── decan_aspects.py    # Decanic aspect analysis
│   └── prng_shuffler.py    # Seeded shuffler (single source of truth)
├── scripts/
│   ├── view_output.py      # Render an HTML report in the terminal
│   ├── download_images.py  # Fetch card images into static/images/
│   ├── fetch_cards.py      # Quick DB card query
│   └── inspect_*.py, diag_*.py, check_db_consistency.py   # DB debugging helpers
├── database/
│   ├── schema.sql          # Full schema (includes all migrations below)
│   ├── seed.sql            # Cards, correspondences, spread geometry
│   └── migrations/         # Only needed for DBs created before the current schema
├── config/                 # config.json (scoring weights, DB host/port), default_params.json
├── prompts/                # System/operation prompts for LLM-assisted readings
├── templates/              # Jinja2 templates for the web GUI and reports
├── static/images/          # Card images (not in git; see below)
├── output/                 # Generated HTML reports (not in git)
├── docs/                   # Thoth_Tarot_Engine_Guide.docx
└── tests/                  # pytest suite
```

---

## Prerequisites

- Python 3.12+
- PostgreSQL 16+

---

## Setup

### 1. Clone and install

```bash
git clone git@github.com:hampshirecottage-ai/ootk-thoth-engine.git
cd ootk-thoth-engine

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# for tests:
pip install -r requirements-dev.txt
```

### 2. Configure the database

```bash
cp .env.example .env
```

Edit `.env`:

```
DB_NAME=my_tarot_db
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_HOST=localhost
DB_PORT=5432
```

Environment variables take priority over the `database` block in `config/config.json`, which only supplies `dbname`, `host` and `port` defaults. Keep usernames and passwords in `.env`.

### 3. Create and seed the database

```bash
createdb -U postgres -h localhost my_tarot_db
psql -U postgres -h localhost -d my_tarot_db -f database/schema.sql
psql -U postgres -h localhost -d my_tarot_db -f database/seed.sql
```

The schema already includes everything in `database/migrations/`. Run those files only against an older database.

### 4. Card images (optional)

The 80 card images (about 180 MB) are not stored in git. Regenerate them with:

```bash
python scripts/download_images.py
```

---

## Usage

### Command line

```bash
python src/spread_engine.py \
  --spread 12 \
  --seed 77 \
  --mapping french_egyptian \
  --significator "Knight of Swords" \
  --topic "Is everything working correctly?" \
  --html
```

| Flag | Description | Default |
|---|---|---|
| `--spread` | Spread key, 1-12 | asks interactively |
| `--seed` | Numeric seed for deterministic draws. Omit it to enter cards by hand | manual entry |
| `--significator` | Significator card title (pinned to Position 1) | `Knight of Swords` |
| `--topic` | Question or intent text | asks interactively |
| `--mapping` | `golden_dawn` or `french_egyptian` | `golden_dawn` |
| `--framework` | `auto`, `light_descent`, `soul_formation`, `life_path`, `post_mortem` | `auto` |
| `--html` | Write an HTML report to `output/` | off |

View the latest saved report in the terminal:

```bash
python scripts/view_output.py            # latest report in output/
python scripts/view_output.py --file output/ootk_output_20.html
```

### Web GUI

```bash
uvicorn app:app --reload --port 8000
```

Open http://localhost:8000 for the form and http://localhost:8000/docs for the API docs.

### Sanity-check a full run

```bash
python src/spread_engine.py --spread 12 --seed 77 --mapping french_egyptian \
  --significator "Knight of Swords" --topic "Is everything working correctly?" | tee run.txt
python check_run.py run.txt
```

`check_run.py` exits 0 when every check passes. WARN lines are known data gaps, not failures.

### Tests

```bash
python -m pytest -v
```

---

## Database model

| Table | Purpose |
|---|---|
| `thoth_cards` | The 78 cards (title, arcana, suit, rank, key scale, description) |
| `correspondences` | Hebrew letter, path/sephira, element/planet/sign, colour scale, Platonic solid and spatial data, for both mapping schemes |
| `spread_position_geometry` | 3D/polar coordinates for each spread position |
| `tarot_sessions` | One row per reading (operation, significator, notes) |
| `spread_pulls` | Spreads within a session |
| `session_card_pulls` | Each drawn card, its position, and dignity flag |

Relationships: `tarot_sessions` 1-* `spread_pulls` 1-* `session_card_pulls` *-1 `thoth_cards`.

---

## License

MIT. See [LICENSE](LICENSE).

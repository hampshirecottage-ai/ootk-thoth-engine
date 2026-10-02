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
- **Deterministic PRNG shuffler** (`src/ootk/shuffle.py`), shared by every entry point.
- **PostgreSQL persistence** of sessions, spreads and card pulls.
- **Three interfaces**: CLI (`ootk`), FastAPI web GUI (`ootk.web`), and a Rich terminal viewer for saved reports (`scripts/view_output.py`).

---

## Project layout

```
ootk-thoth-engine/
├── pyproject.toml          # Dependencies, dev extras and the `ootk` command
├── src/ootk/
│   ├── cli.py              # Command line: `ootk` / `python -m ootk`
│   ├── web.py              # FastAPI web GUI: `uvicorn ootk.web:app`
│   ├── spreads.py          # Spread definitions, layout coordinates, operation segments
│   ├── analysis.py         # Elements, dignities, geometry, topology, macro framework
│   ├── report.py           # Analytical report (Markdown prompt) and HTML export
│   ├── db.py               # DB settings, card lookups, saving sessions
│   ├── shuffle.py          # Seeded shuffler (single source of truth)
│   ├── rules.py            # Book T dignities, aspects and orbs (the one source of scoring rules)
│   └── decans.py           # Decanic aspect analysis (not yet wired in)
├── scripts/
│   ├── check_run.py        # Sanity-checks a saved 4-operation run (run.txt)
│   ├── db_inspect.py       # DB audit / schema / join inspection (audit, schema, joins)
│   ├── download_images.py  # Fetch card images into static/images/
│   └── view_output.py      # Render an HTML report in the terminal
├── database/
│   ├── schema.sql          # Full dump: schema, all migrations, and reference data
│   └── migrations/         # Only needed for DBs created before the current schema
├── config/                 # config.json (DB name/host/port defaults)
├── prompts/                # System/operation prompts for LLM-assisted readings
├── templates/              # Jinja2 templates for the web GUI and reports
├── static/images/          # Card images (not in git; see below)
├── output/                 # Generated HTML reports (not in git)
├── docs/                   # Thoth_Tarot_Engine_Guide.docx
└── tests/                  # pytest suite (+ opt-in real-database tests)
```

---

## Prerequisites

- Python 3.11+
- PostgreSQL 16+

---

## Setup

### 1. Clone and install

```bash
git clone git@github.com:hampshirecottage-ai/ootk-thoth-engine.git
cd ootk-thoth-engine

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"     # the package, its `ootk` command, and test tools
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

### 3. Create the database

```bash
createdb my_tarot_db
psql -d my_tarot_db -f database/schema.sql
python scripts/db_inspect.py audit
```

`schema.sql` is a full dump: it creates the tables and loads the 78 cards, correspondences and spread geometry, so there is no separate seed step. It already includes everything in `database/migrations/`, which you only need for older databases.

These commands use your own Postgres role. If your install has a `postgres` superuser, add `-U postgres -h localhost` and set `DB_USER=postgres` in `.env`. On Homebrew installs the role is your macOS username instead, so set `DB_USER` to that.

On a fresh machine `schema.sql` may print errors about `transaction_timeout` (the dump came from a newer Postgres) and about a missing `dbuser` role (table ownership). Both are harmless: the data still loads, and the audit above confirms it.

### 4. Card images (optional)

The 80 card images (about 180 MB) are not stored in git. Regenerate them with:

```bash
python scripts/download_images.py
```

---

## Usage

### Command line

```bash
ootk \
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
uvicorn ootk.web:app --reload --port 8000
```

Open http://localhost:8000 for the form and http://localhost:8000/docs for the API docs.

### Sanity-check a full run

```bash
ootk --spread 12 --seed 77 --mapping french_egyptian \
  --significator "Knight of Swords" --topic "Is everything working correctly?" | tee run.txt
python scripts/check_run.py run.txt
```

`check_run.py` exits 0 when every check passes. WARN lines are known data gaps, not failures.

### Inspect the database

```bash
python scripts/db_inspect.py audit              # consistency checks; exit 1 on failure
python scripts/db_inspect.py schema             # thoth_cards columns, tables, sample row
python scripts/db_inspect.py joins --card-id 1  # one card with all joined correspondences
```

### Tests

```bash
python -m pytest -v
```

The default suite mocks the database. To also run the real SQL against a database built from `schema.sql`:

```bash
createdb ootk_test && psql -d ootk_test -f database/schema.sql
OOTK_TEST_DB=1 DB_NAME=ootk_test python -m pytest tests/test_db_integration.py -v
```

Existing databases created before `thoth_cards.french_number` existed need `database/migrations/add_french_number.sql`.
Databases created before the correspondence fixes (no `thoth_cards.attribution` column) need `database/migrations/fix_correspondences.sql`; it is safe to re-run, and the engine stops with that instruction if it is missing.

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

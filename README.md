# OOTK Thoth Engine (`ootk-thoth-engine`)

An open-source Hermetic operational engine, database architecture, and FastAPI web application designed to automate Tarot operations using Aleister Crowley’s Thoth Tarot framework. The engine performs dynamic card selection, automated Hermetic synthesis reporting, elemental balance and dignity calculations, and direct asset integration with Lady Frieda Harris’s original artwork.

---

## Features

- **Interactive Graphic Web GUI (`FastAPI` + `Jinja2`):**
  - Grid-based visual card selector operating at `http://localhost:8000`.
  - Dynamic spread slotting (Opening of the Key 15-card spread, 3-card, 5-card, and custom layouts).
  - Built-in visual previews for card selections and active position assignment.

- **Hermetic Synthesis & Calculation Engine:**
  - **Elemental Dignities Matrix:** Quantitative calculation of passive/active elemental interactions (Mutual Strengths, Weaknesses, Neutralities, Incompatibilities).
  - **Elemental Distribution Analysis:** Automatic tally and percentage balance for Fire, Water, Air, and Earth vectors across positions.
  - **Liber 777 Correspondences:** Direct SQL query mappings for Golden Dawn/Thoth attributions, including astrological decans, Hebrew letters, Kabbalistic Tree of Life paths, and Chaldean zodiacal decans.

- **Asset Management & Artwork Retrieval Pipeline:**
  - Automated download script (`scripts/download_images.py`) to fetch and normalize high-resolution scans of Lady Frieda Harris’s Thoth card paintings.
  - Multi-CDN fallback mechanism with alias resolution mapping idiosyncratic Thoth card titles (*The Magus*, *The Priestess*, *Adjustment*, *Lust*, *Art*, *The Aeon*, *The Universe*).

- **Database-Driven Session Logging:**
  - PostgreSQL integration via `psycopg3` (`dict_row`) storing session parameters, topic inputs, active significators, card position assignments, and generated Hermetic prompts into `my_tarot_db`.

---

## Project Structure

```text
ootk-thoth-engine/
├── app.py                   # FastAPI web application server & endpoint handlers
├── schema.sql               # PostgreSQL database schema and index definitions
├── .env                     # Database connection credentials (git-ignored)
├── .gitignore               # Version control exclusion rules
├── README.md                # System documentation
├── templates/
│   ├── index.html           # Visual card selector grid & interactive spread board
│   └── report.html          # HTML Hermetic synthesis report generator
├── static/
│   └── images/              # Local storage for Lady Frieda Harris artwork (.jpg)
│       └── .gitkeep         # Placeholder maintaining directory structure in Git
└── scripts/
    ├── download_images.py   # Multi-CDN artwork downloader & title alias resolver
    ├── spread_engine.py     # Core elemental calculation & database helper modules
    ├── ootk_engine.py       # Terminal interactive CLI engine loop
    ├── execute.py           # Command-line execution entry point
    └── view_output.py       # Rich terminal log viewer & report renderer


Parameter Flag	Accepted Values	Default	Description
--mapping	golden_dawn
french_egyptian	golden_dawn	Controls the Tarot-Kabbalah correspondence system (e.g., swapping Hebrew letters/attributions for Major Arcana).
--framework	auto
light_descent
soul_formation
life_path
post_mortem	auto	Overrides the Cabbalistic Macro Framework lens used during synthesis evaluation.
--html	(None — Flag)	False	When present, generates an HTML report inside the output/ directory.
--spread	1 through 12	None	Selects the spread layout or pipeline operation.
--seed	Any string/integer	None	Sets the PRNG seed for deterministic card draws.
--topic	Quoted String	None	Defines the question or topic for the spread session.
--significator	Card Title String	Knight of Swords	Defines the central significator card.
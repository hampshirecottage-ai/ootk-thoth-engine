# OOTK Thoth Tarot Analysis Engine

![OOTK Architecture Diagram](https://raw.githubusercontent.com/hampshirecottage-ai/ootk-thoth-engine/main/assets/social.jpeg)

A streamlined Python CLI engine designed for deterministic shuffling simulations, elemental dignity calculations, and multi-format report generation based on the Golden Dawn **Opening of the Key (OOTK)** methodology and Thoth Tarot attributions.

---

## Key Features

* **Deterministic PRNG Shuffling**: Employs Linear Congruential Generators (LCG) and Fisher-Yates shuffle algorithms for perfectly reproducible deck state permutations.
* **Hermetic & Golden Dawn Logic**: Automatically processes elemental dignities, zodiacal decan attributions, and Kabbalistic Tree of Life paths.
* **Multi-Format Output Pipeline**: Generates structured Markdown reports, styled standalone HTML documents, and SVG terminal renders.
* **Terminal UI & Viewer**: Built with `rich` for elegant terminal rendering and interactive report inspection.

---

## Repository Structure

```text
ootk-thoth-engine/
├── assets/
│   └── social.jpeg           # Architecture preview diagram
├── outputs/                  # Local execution artifacts (git-ignored)
│   └── .gitkeep
├── scripts/
│   ├── execute.py            # Primary CLI execution runner
│   └── view_output.py        # Terminal rendering & export viewer
├── .gitignore
├── README.md
└── requirements.txt          # Python dependencies

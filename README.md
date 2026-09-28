# OOTK Thoth Tarot Calculation & Vector Engine

A deterministic Python CLI framework and PostgreSQL analytical engine for conducting Crowley/Thoth Tarot operations, calculating Liber 777 Kabbalistic correspondences, evaluating multi-card elemental dignity interactions, and generating structured system prompts for Hermetic LLM synthesis.

---

## Key Capabilities

* **Deterministic PRNG Deck Shuffling:** Linear Congruential Generator (LCG) and SHA-256 seed-based Fisher–Yates shuffling algorithm for repeatable, audited digital card draws.
* **Liber 777 Correspondence Engine:** Automated database mapping across Key Scales 0–32, Hebrew glyphs, paths/Sephiroth, astrological decans, and King Scale color attributions.
* **Pairwise Elemental Dignity Scoring:** Automated adjacent card interaction calculation ($+2$ active attraction/nourishment, $+1$ direct reinforcement, $0$ neutral, $-2$ active hostility/friction).
* **Master Pipeline Operations:** Supports 12 standard spread layouts ranging from daily 1-card operations to the full 75-card 4-Operation Opening of the Key (OOTK) sequence.
* **Multi-Format Export & Rendering:** Generates dark-mode HTML reports, raw Markdown prompt vectors, PostgreSQL database session persistence, and styled terminal visualization via `rich`.

---

## Directory Layout

```text
.
├── config/             # Parameter specifications and environment templates
├── output/             # Saved session output reports (.html, .md)
├── prompts/            # System prompt specifications and operational guidelines
├── scripts/
│   ├── fetch_cards.py     # Database schema setup and card verification
│   ├── ootk_engine.py     # Base vector calculation helper module
│   ├── prng_shuffler.py   # Standalone PRNG shuffle algorithm
│   ├── spread_engine.py   # Primary CLI execution, PRNG, and DB engine
│   └── view_output.py     # Rich terminal report visualizer
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt

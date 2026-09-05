# OOTK Thoth Vector & PRNG Engine

A deterministic, rule-based algorithmic framework for executing Opening of the Key (OOTK) Thoth Tarot vector analysis driven by a seed-based PRNG Fisher-Yates shuffle.

## Features
- **Deterministic Shuffling:** Uses an LCG PRNG paired with the Fisher-Yates algorithm for reproducible card dealing.
- **Elemental Dignity Matrix:** Calculates vector interactions across Fire, Water, Air, and Earth.
- **Strict Nomenclature:** Enforces standard Thoth suit nomenclature (Disks) and explicit output schemas.

## Usage
Run the unified pipeline:
```bash
python3 ootk_engine.py

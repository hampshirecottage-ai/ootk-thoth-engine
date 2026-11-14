"""Write src/ootk/chance.json: what random shuffles give for each spread's headline numbers
(see ootk/chance.py). Uses the card tables in tests/fixtures/reference_cards.json, which a test
keeps equal to the database, so no database is needed. Rerun after changing a rule that moves
these numbers:  .venv/bin/python scripts/make_chance_table.py"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ootk import chance, web                      # noqa: E402
from ootk.spreads import BOOK_T_KEY, SPREADS      # noqa: E402


def load_fixture_tables():
    ref = json.loads((ROOT / "tests" / "fixtures" / "reference_cards.json").read_text())
    web._reference_cache["deck"] = ref["deck"]
    for system in ("thoth", "golden_dawn", "french_egyptian"):
        web._reference_cache[system] = ref["rows"]


def main():
    load_fixture_tables()
    table = {}
    for key in sorted([*SPREADS, BOOK_T_KEY], key=int):
        start = time.time()
        table[key] = chance.simulate(key)
        print(f"spread {key}: {time.time() - start:.1f}s, at least one unusual in "
              f"{table[key]['_unusual'] / table[key]['_draws']:.0%}")
    chance.CHANCE_FILE.write_text(json.dumps(table, indent=1, sort_keys=True) + "\n")
    print(f"wrote {chance.CHANCE_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

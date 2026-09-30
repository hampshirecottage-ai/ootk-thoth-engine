Thoth Tarot & Liber 777 Calculation Engine

Technical Documentation & Spread Reference Guide

1. Command-Line Options Reference

The calculation engine (scripts/spread_engine.py) provides an extensive command-line interface for running manual, automated, and deterministic Hermetic tarot analysis sessions.

CLI Flags & Arguments

Flag	Type / Choices	Default	Description
--topic	str	None	Optional query or intent topic string.
--seed	str	None	PRNG seed for deterministic deck shuffling and drawing.
--significator	str	"Knight of Swords"	Title of the card acting as the operation's significator.
--spread	str (1–12)	None	Key identifier for selecting a spread layout.
--framework	auto, light_descent, soul_formation, life_path, post_mortem	"auto"	Overrides the automatic Macro Conceptual Framework detection.
--mapping	golden_dawn, french_egyptian	"golden_dawn"	Selects the Tarot-Kabbalah correspondence system.
--html	Flag	False	Auto-generates an HTML report inside output/.

2. Command-Line Usage Examples

Basic Interactive Run

Prompts the user interactively to select a spread and input card titles manually:

[bash]
python scripts/spread_engine.py


Deterministic PRNG Auto-Draw

Draws cards automatically for Spread 3 (Triad) using a seed for reproducible results:

[bash]
python scripts/spread_engine.py --spread 3 --seed 42 --topic "Career Progression"


Auto-Generating HTML Reports

Executes Spread 1 (Single Card) and exports an HTML report into output/:

[bash]
python scripts/spread_engine.py --spread 1 --topic "Daily Reflection" --html


Full Configuration Override

Configures a custom significator, alternative French/Egyptian mapping scheme, and forced macro conceptual framework:

[bash]
python scripts/spread_engine.py \
  --spread 5 \
  --significator "Queen of Wands" \
  --mapping french_egyptian \
  --framework soul_formation \
  --topic "Spiritual Alignment" \
  --html


3. Detailed Spread Layout Catalog

The engine supports 12 distinct spread configurations categorized into four operational tiers.

Tier I: Core & Progressive Spreads

1. Single Card / Daily Operations (1 Card)

⚬ Position 1: Core Theme / Focus

2. Dyad — Polarity & Dynamics (2 Cards)

⚬ Position 1: Active Force (Thesis)

⚬ Position 2: Receptive / Resistance Force (Antithesis)

3. Triad — Timeline & Motion (3 Cards)

⚬ Position 1: Past / Root Cause

⚬ Position 2: Present / Active Dynamics

⚬ Position 3: Future / Manifest Result

4. Sub-Elemental Quadrant Cross — Elemental Sub-Division (4 Cards)

⚬ Position 1: Yod of Yod (Fire of Fire — Pure Flash)

⚬ Position 2: Heh of Yod (Water of Fire — Emotional Will)

⚬ Position 3: Vav of Yod (Air of Fire — Directed Focus)

⚬ Position 4: Heh Final of Yod (Earth of Fire — Physicalized Action)

5. Tetragrammaton Spread — 4 Elemental Vectors (4 Cards)

⚬ Position 1: Atziluth / Yod (Fire — Creative Spark)

⚬ Position 2: Briah / Heh (Water — Mental/Emotional Container)

⚬ Position 3: Yetzirah / Vav (Air — Formative Processing)

⚬ Position 4: Assiah / Heh Final (Earth — Material Result)

Tier II: Hermetic & Macrocosmic Layouts

6. Hexagram Spread — Planetary Operations & Macrocosm (7 Cards)

⚬ Position 1: Saturn (Top Apex / Form, Constraints & Karma)

⚬ Position 2: Jupiter (Right Top / Expansion, Luck & Growth)

⚬ Position 3: Mars (Right Bottom / Drive, Severity & Force)

⚬ Position 4: Venus (Bottom Apex / Harmony, Affection & Value)

⚬ Position 5: Mercury (Left Bottom / Intellect, Logic & Communication)

⚬ Position 6: Sun (Left Top / Core Vitality, Identity & Spirit)

⚬ Position 7: Moon (Center Core / Subconscious, Instinct & Foundation)

7. Tree of Life Layout — 10 Sephiroth Mapping (10 Cards)

⚬ Position 1: Kether (Crown / Primary Impulse)

⚬ Position 2: Chokmah (Wisdom / Dynamic Force)

⚬ Position 3: Binah (Understanding / Structural Form)

⚬ Position 4: Chesed (Mercy / Expansion)

⚬ Position 5: Geburah (Severity / Action & Severity)

⚬ Position 6: Tiphareth (Beauty / Harmony & Core Self)

⚬ Position 7: Netzach (Victory / Emotions & Instinct)

⚬ Position 8: Hod (Splendor / Intellect & Logic)

⚬ Position 9: Yesod (Foundation / Subconscious & Astral)

⚬ Position 10: Malkuth (Kingdom / Manifest World)

Tier III: Opening of the Key (OOTK) Operations

8. OOTK — First Operation (15 Cards)

⚬ Position 1: Significator / Core Nature of Question

⚬ Positions 2–3: Development of Question (Left Pair A & B)

⚬ Positions 4–5: Further Outcome (Right Pair A & B)

⚬ Positions 6–7: Unexpected / External Factors (Center Pair A & B)

⚬ Positions 8–9: Psychological / Subconscious Basis (Base Left A & B)

⚬ Positions 10–11: Environmental / Material Basis (Base Right A & B)

⚬ Positions 12–13: Final Synthesis / Karma (Top Apex A & B)

⚬ Position 14: Key Counter-Balance / Receptivity

⚬ Position 15: Ultimate Climax / Resolution

9. OOTK — Second Operation — 12 Astrological Houses (12 Cards)

⚬ Positions 1–12: Mapped sequentially from First House (Ascendant / Physical Self) through Twelfth House (Subconscious & Hidden).

10. OOTK — Third Operation — 12 Zodiacal Signs (12 Cards)

⚬ Positions 1–12: Mapped sequentially from Aries through Pisces.

11. OOTK — Fourth Operation — 36 Zodiacal Decans (36 Cards)

⚬ Positions 1–36: Mapped sequentially from Decan 1 through Decan 36.

Tier IV: Master Pipeline

12. Complete Opening of the Key (OOTK) — 4-Operation Master Pipeline (75 Cards)

Executes Operations 1 through 4 (8, 9, 10, and 11) sequentially in a single automated pass.

4. Mathematics of the 75-Card Master Pipeline

A common question regarding Option 12 is why exactly 75 cards are drawn during the full Opening of the Key sequence:

$$\text{Operation 1 (15 cards)} + \text{Operation 2 (12 cards)} + \text{Operation 3 (12 cards)} + \text{Operation 4 (36 cards)} = 75\text{ cards total}$$

Golden Dawn Protocol

In traditional Hermetic Golden Dawn protocol, the full tarot deck consists of 78 cards. Before starting the First Operation, the Significator card is selected separately to represent the querent or topic, removing it from the active deck before drawing the remaining 15 cards for Operation 1.

While all 78 cards participate in the complete ceremonial framework, the active draw sequence across the four operations total exactly 75 pulls.
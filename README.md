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

Getting Started
Prerequisites
⚬	macOS / Linux environment
⚬	Python 3.10+
Installation
	1.	Clone the repository:
git clone [https://github.com/hampshirecottage-ai/ootk-thoth-engine.git](https://github.com/hampshirecottage-ai/ootk-thoth-engine.git)
cd ootk-thoth-engine

	2.	Set up a virtual environment (optional but recommended):
python3 -m venv venv
source venv/bin/activate

	3.	Install dependencies:
pip install -r requirements.txt

Execution Engine (scripts/execute.py)
scripts/execute.py serves as the primary CLI entry point for running deterministic shuffling simulations and OOTK analysis operations.
Usage Syntax
python scripts/execute.py --seed <PRNG_SEED> [FLAGS]

CLI Parameters & Options
Option	Type	Required / Default	Description
--seed	int	Required	Integer seed value for reproducible PRNG shuffling.
--operation	int	Default: 1	OOTK Operation phase (1 through 5).
--html	flag	Default: Enabled	Automatically compiles HTML reports alongside Markdown.
--no-html	flag	—	Disables HTML output and exports .md files only.
Execution Examples
⚬	Run Operation 1 with a deterministic seed:
python scripts/execute.py --seed 84920491823

⚬	Run Operation 3 without generating HTML:
python scripts/execute.py --operation 3 --seed 1049281 --no-html

⚬	Display CLI help and available options:
python scripts/execute.py --help

Generated Artifacts
Running execute.py outputs files into the git-ignored outputs/ directory following standard naming conventions:
⚬	outputs/ootk_op1_84920491823.md — Raw Markdown report for terminal viewing.
⚬	outputs/ootk_op1_84920491823.html — Styled HTML report for web browser review.
Output Viewer (scripts/view_output.py)
Render reports inside your terminal using rich formatting, or convert existing Markdown outputs into additional formats:
# View report in terminal
python scripts/view_output.py outputs/ootk_op1_84920491823.md

# Render and export to SVG image card
python scripts/view_output.py outputs/ootk_op1_84920491823.md --svg

Development & Git Hygiene
Generated analytical reports reside in the outputs/ directory and are excluded from Git tracking via .gitignore. Only the .gitkeep anchor file is tracked to maintain folder structure.
# Verify output directory exclusion
git status

License
Distributed under the MIT License. See LICENSE for details.
EOF

---

### Method 2: Open in VS Code or Terminal Text Editor

1. Open `README.md` directly in VS Code or `nano`:
   ```bash
   code README.md   # VS Code
   # or
   nano README.md   # Terminal Editor

	1.	Copy the Markdown code block from the previous response and paste it into the editor.
	2.	Save the file (Cmd + S in VS Code, or Ctrl + O then Enter in nano).
Step 3: Commit and Push
Once saved, stage, commit, and push your new README.md:
git add README.md
git commit -m "docs: create comprehensive README with architecture preview and CLI docs"
git push origin main

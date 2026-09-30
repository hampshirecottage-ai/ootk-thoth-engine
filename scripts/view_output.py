import os
import sys
import glob
import argparse
import re
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress_bar import ProgressBar
from rich.tree import Tree
from rich.text import Text

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

console = Console()

def find_latest_html_report():
    output_pattern = str(BASE_DIR / "output" / "ootk_output_*.html")
    files = glob.glob(output_pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def parse_html_report(filepath):
    """Extracts raw Markdown prompt text inside <pre> tags from HTML report."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    match = re.search(r"<pre>(.*?)</pre>", content, re.DOTALL)
    if not match:
        return None
    
    # Unescape basic HTML entities
    raw_text = match.group(1).replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    return raw_text

def render_rich_report(raw_text, filename):
    console.print(Panel(f"[bold cyan]OOTK VISUALIZER[/bold cyan] — [yellow]{filename}[/yellow]", expand=False))

    # Parse Sections
    sections = raw_text.split("---")

    for section in sections:
        section_str = section.strip()
        if not section_str:
            continue

        # Header / Title block
        if "HERMETIC ANALYTICAL REPORT" in section_str:
            lines = [l.strip() for l in section_str.split("\n") if l.strip()]
            title = lines[0].replace("#", "").strip() if lines else "HERMETIC REPORT"
            
            meta_table = Table(show_header=False, box=None)
            meta_table.add_column("Key", style="bold magenta")
            meta_table.add_column("Value", style="bold white")

            for line in lines[1:]:
                if "**" in line:
                    parts = line.replace("**", "").split(":", 1)
                    if len(parts) == 2:
                        meta_table.add_row(parts[0].strip(), parts[1].strip())
            
            console.print(Panel(meta_table, title=f"[bold green]{title}[/bold green]", border_style="green"))

        # Section 1: Elemental Distribution
        elif "1. ELEMENTAL VECTOR DISTRIBUTION" in section_str:
            table = Table(title="1. Elemental Vector Distribution", border_style="blue", header_style="bold cyan")
            table.add_column("Element", style="bold yellow", width=12)
            table.add_column("Count & Percentage", style="bold white", width=20)
            table.add_column("Visual Bar", style="bold magenta")

            for line in section_str.split("\n"):
                if line.startswith("* **"):
                    # Format: * **Fire  **: █ 2 (50.0%)
                    match = re.search(r"\*\*(\w+)\s*\*\*:\s*([█\s]+)?\s*(\d+)\s*\(([\d\.]+\%)\)", line)
                    if match:
                        elem, bar, count, pct = match.groups()
                        table.add_row(elem.capitalize(), f"{count} ({pct})", bar or "")

            console.print(table)

        # Section 2: Pairwise Dignity Interactions
        elif "2. PAIRWISE ELEMENTAL DIGNITY INTERACTIONS" in section_str:
            table = Table(title="2. Pairwise Elemental Dignity Interactions", border_style="yellow", header_style="bold magenta")
            table.add_column("Adjacent Card Pair", style="bold white")
            table.add_column("Score", style="bold cyan", justify="center", width=8)
            table.add_column("Relationship / Dynamic", style="italic green")

            for line in section_str.split("\n"):
                if line.startswith("* **"):
                    # Format: * **Pos 1 (...) <-> Pos 2 (...)**: `Score: +2` | Dynamic
                    parts = line.split("`Score:")
                    if len(parts) == 2:
                        pair_part = parts[0].replace("* **", "").replace("**:", "").strip()
                        rest = parts[1].split("` | ")
                        score_str = rest[0].strip()
                        rel_str = rest[1].strip() if len(rest) > 1 else ""
                        
                        # Style score
                        if "+2" in score_str or "+1" in score_str:
                            score_styled = f"[bold green]{score_str}[/bold green]"
                        elif "-2" in score_str:
                            score_styled = f"[bold red]{score_str}[/bold red]"
                        else:
                            score_styled = f"[dim]{score_str}[/dim]"

                        table.add_row(pair_part, score_styled, rel_str)

            console.print(table)

        # Section 3: Card-by-Card Tree / Matrix
        elif "3. CARD-BY-CARD CORRESPONDENCE MATRIX" in section_str:
            tree = Tree("[bold cyan]3. Card Spread Matrix & Liber 777 Correspondences[/bold cyan]")
            
            cards_raw = section_str.split("### Position ")
            for c_raw in cards_raw[1:]:
                lines = [l.strip() for l in c_raw.split("\n") if l.strip()]
                pos_header = lines[0] if lines else "Position"
                
                pos_node = tree.add(f"[bold yellow]Position {pos_header}[/bold yellow]")
                for line in lines[1:]:
                    if line.startswith("- **"):
                        key_val = line.replace("- **", "").split("**:", 1)
                        if len(key_val) == 2:
                            pos_node.add(f"[bold white]{key_val[0]}:[/bold white] [dim green]{key_val[1].strip()}[/dim green]")

            console.print(Panel(tree, border_style="cyan"))

def main():
    parser = argparse.ArgumentParser(description="OOTK Rich Terminal Output Visualizer")
    parser.add_argument("--file", type=str, help="Path to HTML report in output/ (defaults to latest)")
    args = parser.parse_args()

    filepath = args.file if args.file else find_latest_html_report()

    if not filepath or not os.path.exists(filepath):
        console.print("[bold red]Error:[/bold red] No valid HTML output file found in `output/`.")
        sys.exit(1)

    raw_text = parse_html_report(filepath)
    if not raw_text:
        console.print(f"[bold red]Error:[/bold red] Could not parse report content from {filepath}.")
        sys.exit(1)

    render_rich_report(raw_text, filepath)

if __name__ == "__main__":
    main()

import os
import sys
import glob
import html
import argparse
import re
from pathlib import Path
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

BASE_DIR = Path(__file__).resolve().parent.parent

console = Console()

HEADING_RE = re.compile(r"^## \d+\.\s*(.+)$", re.MULTILINE)


def find_latest_html_report():
    output_pattern = str(BASE_DIR / "output" / "ootk_output_*.html")
    files = glob.glob(output_pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def parse_html_report(filepath):
    """Extracts the raw Markdown prompt text inside the <pre> tag of an HTML report."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    match = re.search(r"<pre>(.*?)</pre>", content, re.DOTALL)
    if not match:
        return None
    return html.unescape(match.group(1))


def split_sections(raw_text):
    """Splits on horizontal-rule lines only, so '---' inside content can't break parsing."""
    return [s.strip() for s in re.split(r"^\s*---\s*$", raw_text, flags=re.MULTILINE) if s.strip()]


def section_kind(section):
    """Identifies a section by its heading text, not its number, so renumbering can't break it."""
    if "HERMETIC ANALYTICAL REPORT" in section.split("\n", 1)[0]:
        return "header"
    m = HEADING_RE.search(section)
    if not m:
        return None
    title = m.group(1).upper()
    for key, kind in (
        ("ELEMENTAL VECTOR", "elements"),
        ("HEBREW LETTER SPATIAL", "hebrew"),
        ("PLATONIC SOLID", "platonic"),
        ("PAIRWISE ELEMENTAL DIGNITY", "dignity"),
        ("SPATIAL & GEOMETRIC", "spatial"),
        ("CARD-BY-CARD", "cards"),
    ):
        if key in title:
            return kind
    return None


def strip_md(text):
    return text.replace("**", "").replace("`", "").strip()


def score_style(score_str):
    if score_str.startswith("+"):
        return f"[bold green]{escape(score_str)}[/bold green]"
    if score_str.startswith("-"):
        return f"[bold red]{escape(score_str)}[/bold red]"
    return f"[dim]{escape(score_str)}[/dim]"


def render_header(section):
    lines = [l.strip() for l in section.split("\n") if l.strip()]
    title = lines[0].replace("#", "").strip() if lines else "HERMETIC REPORT"
    meta = Table(show_header=False, box=None)
    meta.add_column("Key", style="bold magenta")
    meta.add_column("Value", style="bold white")
    for line in lines[1:]:
        if "**" in line:
            parts = line.replace("**", "").split(":", 1)
            if len(parts) == 2:
                meta.add_row(escape(parts[0].strip()), escape(parts[1].strip()))
    console.print(Panel(meta, title=f"[bold green]{escape(title)}[/bold green]", border_style="green"))


def render_elements(section):
    table = Table(title="Elemental Vector Distribution", border_style="blue", header_style="bold cyan")
    table.add_column("Element", style="bold yellow", width=12)
    table.add_column("Count & Percentage", style="bold white", width=20)
    table.add_column("Visual Bar", style="bold magenta")
    for line in section.split("\n"):
        m = re.search(r"\*\*(\w+)\s*\*\*:\s*(█*)\s*(\d+)\s*\(([\d.]+%)\)", line)
        if m:
            elem, bar, count, pct = m.groups()
            table.add_row(elem.capitalize(), f"{count} ({pct})", bar)
    console.print(table)


def render_hebrew(section):
    counts = Table(title="Hebrew Letter Spatial Dimensions", border_style="magenta", header_style="bold cyan")
    counts.add_column("Category", style="bold yellow")
    counts.add_column("Count", justify="center", style="bold white")
    for line in section.split("\n"):
        m = re.match(r"\* \*\*(.+?)\*\*:\s*`(\d+)`", line.strip())
        if m:
            counts.add_row(escape(m.group(1)), m.group(2))
    console.print(counts)

    vectors = Table(title="Card Spatial Vectors", border_style="magenta", header_style="bold cyan")
    vectors.add_column("Card", style="bold white")
    vectors.add_column("Letter", style="cyan")
    vectors.add_column("Type / Dimension", style="green")
    for line in section.split("\n"):
        m = re.match(r"- Pos (\d+) \((.+?)\): Letter `(.+?)` -> \*\*(.+?)\*\* \[(.+?)\]", line.strip())
        if m:
            pos, title, letter, stype, sdim = m.groups()
            vectors.add_row(escape(f"{pos}. {title}"), escape(letter), escape(f"{stype} [{sdim}]"))
    if vectors.row_count:
        console.print(vectors)


def render_platonic(section):
    table = Table(title="Platonic Solid Topology", border_style="cyan", header_style="bold magenta")
    table.add_column("Solid", style="bold yellow")
    table.add_column("Count", justify="center", style="bold white")
    duals = []
    for line in section.split("\n"):
        line = line.strip()
        m = re.match(r"\* \*\*(.+?)\s*\*\*:\s*`(\d+)`", line)
        if m:
            table.add_row(escape(m.group(1).strip()), m.group(2))
        elif line.startswith("* Positions"):
            duals.append(line[2:].strip())
    console.print(table)
    if duals:
        console.print(Panel("\n".join(escape(d) for d in duals), title="Dual Pairings", border_style="cyan"))


def render_dignity(section):
    table = Table(title="Pairwise Elemental Dignity Interactions", border_style="yellow", header_style="bold magenta")
    table.add_column("Adjacent Card Pair", style="bold white")
    table.add_column("Score", justify="center", width=8)
    table.add_column("Relationship / Dynamic", style="italic green")
    for line in section.split("\n"):
        m = re.match(r"\* \*\*(.+?)\*\*: `Score: ([+-]?\d+)` \| (.+)", line.strip())
        if m:
            pair, score, rel = m.groups()
            table.add_row(escape(pair), score_style(score), escape(rel))
    console.print(table)


def render_spatial(section):
    table = Table(title="Spatial & Geometric Vector Analysis", border_style="green", header_style="bold magenta")
    table.add_column("Pair", style="bold white")
    table.add_column("Distance", justify="center", style="cyan")
    table.add_column("Angle", justify="center", style="cyan")
    table.add_column("Aspect", style="italic green")
    table.add_column("Mod", justify="center", width=5)

    pair = dist = angle = None
    group = None      # heap layouts state their shared aspect once, above their pairs
    for raw in section.split("\n"):
        line = raw.strip()
        m = re.match(r"_(.+?) - (.+) \[Modifier: `([+-]?\d+)`\]_$", line)
        if m:
            group = m.groups()
            continue
        m = re.match(r"\* \*\*(.+?)\*\*: Spatial Distance `(.+?)` units$", line)
        if m and group:
            aspect, desc, mod = group
            table.add_row(escape(m.group(1)), m.group(2), "", escape(f"{aspect} - {desc}"), score_style(mod))
            continue
        m = re.match(r"\* \*\*(.+?)\*\*:$", line)
        if m:
            pair = m.group(1)
            continue
        m = re.match(r"- Spatial Distance: `(.+?)` units \| Angular Delta: `(.+?)°`", line)
        if m:
            dist, angle = m.groups()
            continue
        m = re.match(r"- Geometric Aspect: \*\*(.+?)\*\* \((.+?)\) \[Modifier: `([+-]?\d+)`\]", line)
        if m and pair:
            aspect, desc, mod = m.groups()
            table.add_row(escape(pair), dist or "", f"{angle}°" if angle else "",
                          escape(f"{aspect} - {desc}"), score_style(mod))
            pair = dist = angle = None
    if table.row_count:
        console.print(table)
    else:
        console.print(Panel(escape(strip_md(section.split("\n", 1)[-1])), title="Spatial & Geometric Vector Analysis",
                            border_style="green"))


def render_cards(section):
    tree = Tree("[bold cyan]Card Spread Matrix & Liber 777 Correspondences[/bold cyan]")
    for c_raw in section.split("### Position ")[1:]:
        lines = [l.strip() for l in c_raw.split("\n") if l.strip()]
        pos_node = tree.add(f"[bold yellow]Position {escape(lines[0]) if lines else ''}[/bold yellow]")
        for line in lines[1:]:
            if line.startswith("- **"):
                key_val = line.replace("- **", "", 1).split("**:", 1)
                if len(key_val) == 2:
                    pos_node.add(f"[bold white]{escape(key_val[0])}:[/bold white] "
                                 f"[dim green]{escape(strip_md(key_val[1]))}[/dim green]")
    console.print(Panel(tree, border_style="cyan"))


RENDERERS = {
    "header": render_header,
    "elements": render_elements,
    "hebrew": render_hebrew,
    "platonic": render_platonic,
    "dignity": render_dignity,
    "spatial": render_spatial,
    "cards": render_cards,
}


def render_rich_report(raw_text, filename):
    console.print(Panel(f"[bold cyan]OOTK VISUALIZER[/bold cyan] — [yellow]{escape(str(filename))}[/yellow]", expand=False))
    for section in split_sections(raw_text):
        kind = section_kind(section)
        if kind in RENDERERS:
            RENDERERS[kind](section)


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

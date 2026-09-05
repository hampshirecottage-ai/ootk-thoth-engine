import argparse
import sys
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown

def process_file(
    file_path: Path, 
    export_html: bool = False, 
    export_svg: bool = False
) -> None:
    if not file_path.is_file():
        console = Console()
        console.print(f"[bold red]Error:[/bold red] File not found: [yellow]{file_path}[/yellow]")
        sys.exit(1)

    # Read markdown content
    content = file_path.read_text(encoding="utf-8")
    md = Markdown(content)

    # Enable recording on the console instance
    console = Console(record=True)
    
    # Render markdown to terminal
    console.print(md)

    # Export to HTML if requested
    if export_html:
        html_path = file_path.with_suffix(".html")
        console.save_html(str(html_path))
        console.print(f"\n[bold green]✓[/bold green] Saved HTML export to: [cyan]{html_path}[/cyan]")

    # Export to SVG if requested
    if export_svg:
        svg_path = file_path.with_suffix(".svg")
        console.save_svg(str(svg_path), title=f"OOTK Analysis - {file_path.name}")
        console.print(f"[bold green]✓[/bold green] Saved SVG export to: [cyan]{svg_path}[/cyan]")

def main():
    parser = argparse.ArgumentParser(
        description="Render OOTK Markdown output files in terminal with optional HTML/SVG exports."
    )
    parser.add_argument(
        "filepath", 
        type=str, 
        help="Path to the Markdown file in outputs/"
    )
    parser.add_argument(
        "--html", 
        action="store_true", 
        help="Export rendered output as an HTML file alongside the Markdown file"
    )
    parser.add_argument(
        "--svg", 
        action="store_true", 
        help="Export rendered output as an SVG terminal image alongside the Markdown file"
    )

    args = parser.parse_args()
    process_file(Path(args.filepath), export_html=args.html, export_svg=args.svg)

if __name__ == "__main__":
    main()

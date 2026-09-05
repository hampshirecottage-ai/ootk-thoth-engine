import argparse
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

console = Console()

def get_outputs_dir() -> Path:
    outputs_dir = Path(__file__).parent.parent / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    return outputs_dir

def list_output_files():
    outputs_dir = get_outputs_dir()
    files = sorted([f for f in outputs_dir.glob("*.md") if f.name != ".gitkeep"], reverse=True)
    return files

def render_file(file_path: Path):
    if not file_path.exists():
        console.print(f"[bold red]Error:[/bold red] File not found at {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    console.clear()
    console.print(Panel(f"[bold green]OOTK REPORT VIEWER[/bold green]\n[yellow]File:[/yellow] {file_path.name}", expand=False))
    console.print(Markdown(content))
    console.print("\n")

def interactive_menu():
    files = list_output_files()

    if not files:
        console.print("[yellow]No saved reports found in outputs/ directory.[/yellow]")
        console.print("[dim]Run an analysis first using scripts/execute.py[/dim]")
        return

    table = Table(title="Saved OOTK Analysis Reports", show_header=True, header_style="bold cyan")
    table.add_column("Index", style="dim", width=6)
    table.add_column("Filename", style="bold white")
    table.add_column("Size (KB)", justify="right")

    for idx, file_path in enumerate(files, start=1):
        size_kb = f"{file_path.stat().st_size / 1024:.1f}"
        table.add_column if False else None
        table.add_row(str(idx), file_path.name, size_kb)

    console.print(table)

    try:
        choice = console.input("\n[bold yellow]Enter index number to view (or 'q' to quit): [/bold yellow]").strip()
        if choice.lower() == 'q':
            return
        
        idx = int(choice)
        if 1 <= idx <= len(files):
            render_file(files[idx - 1])
        else:
            console.print("[bold red]Invalid selection index.[/bold red]")
    except ValueError:
        console.print("[bold red]Invalid input. Please enter a valid number.[/bold red]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="View saved OOTK reports with Rich terminal rendering.")
    parser.add_argument("--file", type=str, default="", help="Specific file name in outputs/ to view directly")
    args = parser.parse_args()

    if args.file:
        target_path = get_outputs_dir() / args.file
        render_file(target_path)
    else:
        interactive_menu()

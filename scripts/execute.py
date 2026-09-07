import os
import re
import time
import random
import argparse
import webbrowser
from pathlib import Path
from google import genai
from google.genai import types
from google.genai.errors import APIError
from rich.console import Console

# Try importing markdown for HTML generation
try:
    import markdown
except ImportError:
    markdown = None

console = Console()

# GitHub-Dark / Esoteric Theme CSS Template
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OOTK Engine Output - {title}</title>
<!-- MathJax for rendering LaTeX math formulas cleanly -->
<script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
<script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background-color: #0d1117;
    color: #c9d1d9;
    margin: 0 auto;
    padding: 30px 20px;
    max-width: 850px;
    line-height: 1.6;
  }}
  h1, h2, h3 {{ color: #f0f6fc; margin-top: 1.8em; border-bottom: 1px solid #21262d; padding-bottom: 6px; }}
  h1 {{ color: #58a6ff; font-size: 1.8em; border-bottom: 2px solid #30363d; }}
  h2 {{ color: #79c0ff; font-size: 1.3em; }}
  h3 {{ color: #d2a8ff; font-size: 1.1em; }}
  code {{ font-family: "SFMono-Regular", Consolas, monospace; background: #161b22; padding: 3px 6px; border-radius: 4px; color: #79c0ff; }}
  pre {{ background: #161b22; border: 1px solid #30363d; padding: 14px; border-radius: 6px; overflow-x: auto; }}
  table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
  th, td {{ padding: 10px 12px; border: 1px solid #30363d; text-align: left; }}
  th {{ background-color: #161b22; color: #f0f6fc; }}
  tr:nth-child(even) {{ background-color: rgba(22, 27, 34, 0.5); }}
  blockquote {{ border-left: 4px solid #58a6ff; margin: 0; padding-left: 16px; color: #8b949e; background: rgba(56, 139, 253, 0.05); }}
  .header-meta {{
    border-bottom: 2px solid #30363d;
    padding-bottom: 12px;
    margin-bottom: 24px;
    color: #8b949e;
  }}
</style>
</head>
<body>
<div class="header-meta">
  <h1>OOTK Engine Output</h1>
  <p><strong>Target Topic:</strong> {title}</p>
</div>
{content}
</body>
</html>
"""

def clean_terminal_text(text: str) -> str:
    """Strips LaTeX math environments and converts operators for clean terminal viewing."""
    if not text:
        return ""
    cleaned = re.sub(r'\\begin\{[a-zA-Z]+\}', '', text)
    cleaned = re.sub(r'\\end\{[a-zA-Z]+\}', '', cleaned)
    cleaned = cleaned.replace(r'\times', '*').replace(r'\mathbf', '')
    cleaned = cleaned.replace(r'\sum', 'SUM').replace(r'\cdot', '*')
    cleaned = cleaned.replace('$$', '').replace('$', '')
    cleaned = cleaned.replace('{', '').replace('}', '').replace('\\', '')
    return cleaned

def generate_html_document(title: str, markdown_content: str) -> str:
    """Converts markdown content to styled HTML using the GitHub-Dark theme template."""
    if markdown:
        # Markdown extensions matching your export script
        extensions = ['tables', 'fenced_code']
        try:
            import codehilite
            extensions.append('codehilite')
        except ImportError:
            pass
            
        html_body = markdown.markdown(markdown_content, extensions=extensions)
    else:
        html_body = f"<pre>{markdown_content}</pre>"

    return HTML_TEMPLATE.format(title=title, content=html_body)

def run_ootk(operation_file: str, topic: str, seed: str, significator: str = "", export_html: bool = False):
    prompt_path = Path(__file__).parent.parent / "prompts" / operation_file
    if not prompt_path.exists():
        console.print(f"[bold red]Error:[/bold red] Could not find prompt file at {prompt_path}")
        return

    with open(prompt_path, "r", encoding="utf-8") as f:
        system_instruction_content = f.read()

    # Runtime parameters passed as primary user prompt
    user_prompt = f"[RUNTIME PARAMETER EXECUTION BLOCK]\n* Target Topic: {topic}\n* PRNG Seed: {seed}"
    if significator:
        user_prompt += f"\n* Significator Card: {significator}"

    client = genai.Client()
    
    primary_model = "gemini-3.8-flash"
    fallback_model = "gemini-3.1-flash-lite"
    
    max_retries = 4
    base_delay = 3

    console.print(f"[bold cyan]Executing {operation_file} via {primary_model}...[/bold cyan]")
    
    for attempt in range(1, max_retries + 1):
        current_model = primary_model if attempt <= 2 else fallback_model
        
        try:
            response = client.models.generate_content(
                model=current_model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction_content,
                    temperature=0.0
                )
            )
            
            raw_text = response.text

            if export_html:
                if not markdown:
                    console.print("[yellow]Warning: 'markdown' library not installed. Run 'pip install markdown' for formatted rendering.[/yellow]")
                
                html_output = generate_html_document(topic, raw_text)
                output_dir = Path(__file__).parent.parent / "output"
                output_dir.mkdir(exist_ok=True)
                html_file = output_dir / f"ootk_output_{seed}.html"
                
                with open(html_file, "w", encoding="utf-8") as f:
                    f.write(html_output)
                
                console.print(f"\n[bold green]✓ Exported GitHub-Dark HTML to:[/bold green] {html_file}")
                webbrowser.open(f"file://{html_file.absolute()}")
            else:
                console.print("\n[bold green]=== OOTK ENGINE OUTPUT ===[/bold green]\n")
                console.print(clean_terminal_text(raw_text))

            return raw_text

        except APIError as e:
            status_code = getattr(e, "code", None)
            if status_code in [429, 503] or "429" in str(e) or "503" in str(e):
                sleep_time = (base_delay * (2 ** (attempt - 1))) + random.uniform(0.5, 2.0)
                console.print(
                    f"[yellow]Server busy or rate limited on {current_model} (Attempt {attempt}/{max_retries}). "
                    f"Retrying in {sleep_time:.1f}s...[/yellow]"
                )
                time.sleep(sleep_time)
            else:
                console.print(f"[bold red]API Error ({status_code}):[/bold red] {e}")
                raise e

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run OOTK Thoth Engine via Gemini API")
    parser.add_argument(
        "--operation", "--file", 
        dest="file", 
        type=str, 
        default="ootk_thoth_vector_engine.md", 
        help="Prompt file in prompts/"
    )
    parser.add_argument("--topic", type=str, required=True, help="Target topic for calculation")
    parser.add_argument("--seed", type=str, required=True, help="PRNG Seed value")
    parser.add_argument("--significator", type=str, default="", help="Optional Significator card")
    parser.add_argument("--html", action="store_true", help="Export output as GitHub-Dark HTML and open in browser")
    
    args = parser.parse_args()
    run_ootk(args.file, args.topic, args.seed, args.significator, export_html=args.html)

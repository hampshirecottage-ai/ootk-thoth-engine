import os
import re
import time
import random
import argparse
import webbrowser
from datetime import datetime
from pathlib import Path
from google import genai
from google.genai import types
from google.genai.errors import APIError
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

# Try importing markdown for HTML generation
try:
    import markdown
except ImportError:
    markdown = None

console = Console()

# Modern GitHub-Dark / Esoteric Theme CSS Template
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OOTK Engine Output - {title}</title>
<!-- MathJax Configuration for explicit inline and block math rendering -->
<script>
MathJax = {{
  tex: {{
    inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
    displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
    processEscapes: true
  }},
  options: {{
    ignoreHtmlClass: 'tex2jax_ignore',
    processHtmlClass: 'tex2jax_process'
  }}
}};
</script>
<script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
<style>
  :root {{
    --bg-primary: #0d1117;
    --bg-secondary: #161b22;
    --border-color: #30363d;
    --text-primary: #c9d1d9;
    --text-heading: #f0f6fc;
    --accent-blue: #58a6ff;
    --accent-purple: #bc8cff;
    --accent-cyan: #39c5cf;
    --accent-gold: #d2a8ff;
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background-color: var(--bg-primary);
    color: var(--text-primary);
    margin: 0 auto;
    padding: 40px 20px;
    max-width: 900px;
    line-height: 1.65;
  }}
  .header-meta {{
    border-bottom: 2px solid var(--border-color);
    padding-bottom: 16px;
    margin-bottom: 30px;
    background: var(--bg-secondary);
    padding: 20px;
    border-radius: 8px;
    border: 1px solid var(--border-color);
  }}
  .header-meta h1 {{
    color: var(--accent-blue);
    margin: 0 0 10px 0;
    font-size: 1.8em;
    border: none;
    padding: 0;
  }}
  .meta-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 10px;
    font-size: 0.9em;
    color: #8b949e;
  }}
  .meta-item strong {{ color: var(--text-heading); }}

  /* Vector Calculation Sheet Header Card Styling */
  .vector-sheet-card {{
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 20px;
    margin: 20px 0;
  }}
  .vector-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 12px;
    margin-bottom: 16px;
  }}
  .vector-item {{
    background: rgba(13, 17, 23, 0.6);
    border: 1px solid var(--border-color);
    padding: 12px 14px;
    border-radius: 6px;
    font-size: 0.9em;
  }}
  .vector-item strong {{ color: var(--accent-blue); }}
  .vector-result-box {{
    background: rgba(88, 166, 255, 0.08);
    border: 1px solid var(--accent-blue);
    padding: 16px;
    border-radius: 6px;
    margin-top: 16px;
    text-align: center;
  }}
  .vector-result-box h3 {{
    margin: 0 0 6px 0;
    border: none;
    padding: 0;
    color: var(--text-heading);
  }}

  h1, h2, h3 {{ color: var(--text-heading); margin-top: 1.8em; border-bottom: 1px solid #21262d; padding-bottom: 8px; }}
  h2 {{ color: var(--accent-blue); font-size: 1.4em; }}
  h3 {{ color: var(--accent-purple); font-size: 1.15em; }}
  code {{ font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; background: var(--bg-secondary); padding: 3px 6px; border-radius: 4px; color: var(--accent-cyan); font-size: 0.9em; }}
  pre {{ background: var(--bg-secondary); border: 1px solid var(--border-color); padding: 16px; border-radius: 6px; overflow-x: auto; font-size: 0.9em; }}
  table {{ width: 100%; border-collapse: collapse; margin: 24px 0; font-size: 0.95em; }}
  th, td {{ padding: 12px 14px; border: 1px solid var(--border-color); text-align: left; }}
  th {{ background-color: var(--bg-secondary); color: var(--text-heading); font-weight: 600; }}
  tr:nth-child(even) {{ background-color: rgba(22, 27, 34, 0.6); }}
  tr:hover {{ background-color: rgba(56, 139, 253, 0.08); }}
  blockquote {{ border-left: 4px solid var(--accent-blue); margin: 20px 0; padding: 10px 18px; color: #8b949e; background: rgba(56, 139, 253, 0.05); border-radius: 0 6px 6px 0; }}
  .mjx-chtml {{ font-size: 105% !important; padding: 2px 0; }}
</style>
</head>
<body class="tex2jax_process">
<div class="header-meta">
  <h1>OOTK Vector Engine</h1>
  <div class="meta-grid">
    <div class="meta-item"><strong>Target Topic:</strong> {title}</div>
    <div class="meta-item"><strong>PRNG Seed:</strong> {seed}</div>
    <div class="meta-item"><strong>Significator:</strong> {significator}</div>
    <div class="meta-item"><strong>Execution Timestamp:</strong> {timestamp}</div>
  </div>
</div>
{content}
</body>
</html>
"""

def clean_terminal_text(text: str) -> str:
    """Strips HTML tags, LaTeX math environments, and converts operators for clean terminal viewing."""
    if not text:
        return ""
    cleaned = re.sub(r'<[^>]+>', '', text)
    cleaned = re.sub(r'\\begin\{[a-zA-Z]+\}', '', cleaned)
    cleaned = re.sub(r'\\end\{[a-zA-Z]+\}', '', cleaned)
    cleaned = cleaned.replace(r'\times', '*').replace(r'\mathbf', '')
    cleaned = cleaned.replace(r'\sum', 'SUM').replace(r'\cdot', '*')
    cleaned = cleaned.replace(r'\to', '->').replace(r'\rightarrow', '->')
    cleaned = cleaned.replace('$$', '').replace('$', '')
    cleaned = cleaned.replace('{', '').replace('}', '').replace('\\', '')
    return cleaned

def generate_html_document(title: str, seed: str, significator: str, markdown_content: str) -> str:
    """Converts markdown content to styled HTML using the modern GitHub-Dark theme template."""
    if markdown:
        extensions = ['tables', 'fenced_code', 'extra', 'codehilite']
        html_body = markdown.markdown(markdown_content, extensions=extensions)
    else:
        html_body = f"<pre>{markdown_content}</pre>"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sig_str = significator if significator else "Auto / Unassigned"

    return HTML_TEMPLATE.format(
        title=title,
        seed=seed,
        significator=sig_str,
        timestamp=timestamp,
        content=html_body
    )

def run_ootk(operation_file: str, topic: str, seed: str, significator: str = "", export_html: bool = False):
    prompt_path = Path(__file__).parent.parent / "prompts" / operation_file
    if not prompt_path.exists():
        console.print(f"[bold red]Error:[/bold red] Could not find prompt file at {prompt_path}")
        return

    with open(prompt_path, "r", encoding="utf-8") as f:
        system_instruction_content = f.read()

    user_prompt = f"[RUNTIME PARAMETER EXECUTION BLOCK]\n* Target Topic: {topic}\n* PRNG Seed: {seed}"
    if significator:
        user_prompt += f"\n* Significator Card: {significator}"

    client = genai.Client()
    
    primary_model = "gemini-3.8-flash"
    fallback_model = "gemini-3.1-flash-lite"
    
    max_retries = 4
    base_delay = 3

    # Initialize Native System Cache
    cached_content_name = None
    try:
        console.print(f"[bold dim]Caching system prompt for {primary_model}...[/bold dim]")
        cache = client.caches.create(
            model=primary_model,
            config=types.CreateCachedContentConfig(
                contents=[system_instruction_content],
                ttl="3600s",  # Cache system instruction for 1 hour
            )
        )
        cached_content_name = cache.name
        console.print(f"[bold green]✓ Native Prompt Cache Active:[/bold green] {cached_content_name}")
    except Exception as cache_err:
        console.print(f"[yellow]Cache Initialization Skipped (using standard inline system instructions): {cache_err}[/yellow]")

    console.print(f"[bold cyan]Executing {operation_file} via {primary_model}...[/bold cyan]")
    
    for attempt in range(1, max_retries + 1):
        current_model = primary_model if attempt <= 2 else fallback_model
        
        try:
            # Configure request with cached content if available and matching model tier
            if cached_content_name and current_model == primary_model:
                config = types.GenerateContentConfig(
                    cached_content=cached_content_name,
                    temperature=0.0,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=True
                    )
                )
            else:
                config = types.GenerateContentConfig(
                    system_instruction=system_instruction_content,
                    temperature=0.0,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=True
                    )
                )

            response = client.models.generate_content(
                model=current_model,
                contents=user_prompt,
                config=config
            )
            
            raw_text = response.text

            if export_html:
                if not markdown:
                    console.print("[yellow]Warning: 'markdown' library not installed. Run 'pip install markdown' for formatted rendering.[/yellow]")
                
                html_output = generate_html_document(topic, seed, significator, raw_text)
                output_dir = Path(__file__).parent.parent / "output"
                output_dir.mkdir(exist_ok=True)
                html_file = output_dir / f"ootk_output_{seed}.html"
                
                with open(html_file, "w", encoding="utf-8") as f:
                    f.write(html_output)
                
                console.print(f"\n[bold green]✓ Exported GitHub-Dark HTML to:[/bold green] {html_file}")
                webbrowser.open(f"file://{html_file.absolute()}")
            else:
                cleaned_text = clean_terminal_text(raw_text)
                console.print("\n")
                console.print(Panel(
                    Markdown(cleaned_text),
                    title="[bold green]OOTK VECTOR ENGINE OUTPUT[/bold green]",
                    border_style="cyan",
                    padding=(1, 2)
                ))

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

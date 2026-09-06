import sys
import markdown
from pathlib import Path

# Custom GitHub-Dark / Esoteric Theme CSS Template
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
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
</style>
</head>
<body>
{content}
</body>
</html>
"""

def convert_md_to_pretty_html(md_path: str):
    path = Path(md_path)
    if not path.is_file():
        print(f"File not found: {md_path}")
        return

    raw_md = path.read_text(encoding="utf-8")
    
    # Convert Markdown to HTML with extensions for tables and code block formatting
    html_body = markdown.markdown(raw_md, extensions=['tables', 'fenced_code', 'codehilite'])
    
    # Combine with layout template
    full_html = HTML_TEMPLATE.format(title=path.stem, content=html_body)
    
    out_path = path.with_suffix(".html")
    out_path.write_text(full_html, encoding="utf-8")
    print(f"✓ Exported pretty HTML to: {out_path}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        convert_md_to_pretty_html(sys.argv[1])
    else:
        print("Usage: python scripts/export_pretty_html.py <path_to_markdown_file>")

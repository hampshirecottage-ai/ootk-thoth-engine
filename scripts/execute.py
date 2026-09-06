import os
import time
import argparse
from pathlib import Path
from google import genai
from google.genai.errors import ServerError, ClientError
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

console = Console()

def run_ootk(operation_file: str, topic: str, seed: str, significator: str = "", save_file: bool = True):
    prompt_path = Path(__file__).parent.parent / "prompts" / operation_file
    if not prompt_path.exists():
        console.print(f"[bold red]Error:[/bold red] Could not find prompt file at {prompt_path}")
        return

    with open(prompt_path, "r", encoding="utf-8") as f:
        system_instruction = f.read()

    execution_block = f"\n\n[RUNTIME PARAMETER EXECUTION BLOCK]\n* Target Topic: {topic}\n* PRNG Seed: {seed}"
    if significator:
        execution_block += f"\n* Significator Card: {significator}"
    
    full_prompt = system_instruction + execution_block

    client = genai.Client()
    model_name = "gemini-3.6-flash"
    
    console.print(f"\n[bold cyan]Executing {operation_file} via {model_name}...[/bold cyan]\n")
    
    max_retries = 3
    delay = 5
    
    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=full_prompt,
                config={"temperature": 0.0}
            )
            
            console.print(Panel(f"[bold green]OOTK ENGINE ANALYSIS RESULT[/bold green]\n[yellow]Topic:[/yellow] {topic} | [yellow]Seed:[/yellow] {seed}", expand=False))
            
            md = Markdown(response.text)
            console.print(md)

            if save_file:
                # Ensure outputs directory exists (parents=True handles missing parent folders)
                output_dir = Path(__file__).parent.parent / "outputs"
                output_dir.mkdir(parents=True, exist_ok=True)
                
                clean_op = operation_file.replace(".md", "")
                filename = f"{clean_op}_seed_{seed}.md"
                file_path = output_dir / filename
                
                with open(file_path, "w", encoding="utf-8") as out_f:
                    out_f.write(response.text)
                
                console.print(f"\n[dim]Report saved to: {file_path}[/dim]\n")
                
            return response.text

        except (ServerError, ClientError) as e:
            if "503" in str(e) or "429" in str(e):
                console.print(f"[yellow]Server busy or rate limited (Attempt {attempt}/{max_retries}). Retrying in {delay}s...[/yellow]")
                time.sleep(delay)
                delay *= 2
            else:
                raise e

    console.print("[bold red]Error:[/bold red] Request timed out due to high server demand.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run OOTK Thoth Engine via Gemini API with Rich terminal formatting")
    parser.add_argument("--file", type=str, default="ootk_thoth_vector_engine.md", help="Prompt file in prompts/")
    parser.add_argument("--topic", type=str, required=True, help="Target topic for calculation")
    parser.add_argument("--seed", type=str, required=True, help="PRNG Seed value")
    parser.add_argument("--significator", type=str, default="", help="Optional Significator card")
    
    args = parser.parse_args()
    run_ootk(args.file, args.topic, args.seed, args.significator)

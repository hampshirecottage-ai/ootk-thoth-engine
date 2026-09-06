import os
import time
import argparse
from pathlib import Path
from google import genai
from google.genai.errors import ServerError, ClientError
from rich.console import Console
from rich.markdown import Markdown

console = Console()

def run_ootk(operation_file: str, topic: str, seed: str, significator: str = ""):
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
    console.print(f"[bold cyan]Executing {operation_file} via {model_name}...[/bold cyan]")
    
    max_retries = 3
    delay = 5
    
    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=full_prompt,
                config={"temperature": 0.0}
            )
            
            console.print("\n[bold green]=== OOTK ENGINE OUTPUT ===[/bold green]\n")
            # Render Markdown cleanly inside the terminal
            md = Markdown(response.text)
            console.print(md)
            return response.text

        except (ServerError, ClientError) as e:
            if "503" in str(e) or "429" in str(e):
                console.print(f"[yellow]Server busy or rate limited (Attempt {attempt}/{max_retries}). Retrying in {delay}s...[/yellow]")
                time.sleep(delay)
                delay *= 2
            else:
                raise e

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run OOTK Thoth Engine via Gemini API")
    parser.add_argument("--file", type=str, default="ootk_thoth_vector_engine.md")
    parser.add_argument("--topic", type=str, required=True)
    parser.add_argument("--seed", type=str, required=True)
    parser.add_argument("--significator", type=str, default="")
    
    args = parser.parse_args()
    run_ootk(args.file, args.topic, args.seed, args.significator)

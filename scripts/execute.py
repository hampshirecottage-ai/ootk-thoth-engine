import os
import re
import time
import random
import argparse
from pathlib import Path
from google import genai
from google.genai import types
from google.genai.errors import APIError
from rich.console import Console

console = Console()

def clean_terminal_text(text: str) -> str:
    """Strips LaTeX environments and converts operators to clean terminal text."""
    if not text:
        return ""
    # Remove LaTeX math environments
    cleaned = re.sub(r'\\begin\{[a-zA-Z]+\}', '', text)
    cleaned = re.sub(r'\\end\{[a-zA-Z]+\}', '', cleaned)
    
    # Clean standard LaTeX commands and math formatting
    cleaned = cleaned.replace(r'\times', '*').replace(r'\mathbf', '')
    cleaned = cleaned.replace(r'\sum', 'SUM').replace(r'\cdot', '*')
    cleaned = cleaned.replace('$$', '').replace('$', '')
    cleaned = cleaned.replace('{', '').replace('}', '').replace('\\', '')
    
    return cleaned

def run_ootk(operation_file: str, topic: str, seed: str, significator: str = ""):
    prompt_path = Path(__file__).parent.parent / "prompts" / operation_file
    if not prompt_path.exists():
        console.print(f"[bold red]Error:[/bold red] Could not find prompt file at {prompt_path}")
        return

    with open(prompt_path, "r", encoding="utf-8") as f:
        system_instruction_content = f.read()

    # Runtime parameters passed as the primary user prompt
    user_prompt = f"[RUNTIME PARAMETER EXECUTION BLOCK]\n* Target Topic: {topic}\n* PRNG Seed: {seed}"
    if significator:
        user_prompt += f"\n* Significator Card: {significator}"

    client = genai.Client()
    
    # Model resilience setup with automatic fallback endpoint
    primary_model = "gemini-3.8-flash"
    fallback_model = "gemini-3.1-flash-lite"
    
    max_retries = 4
    base_delay = 3

    console.print(f"[bold cyan]Executing {operation_file} via {primary_model}...[/bold cyan]")
    
    for attempt in range(1, max_retries + 1):
        # Switch to secondary model on later retries if primary is congested
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
            
            console.print("\n[bold green]=== OOTK ENGINE OUTPUT ===[/bold green]\n")
            cleaned_output = clean_terminal_text(response.text)
            console.print(cleaned_output)

            return response.text

        except APIError as e:
            status_code = getattr(e, "code", None)
            if status_code in [429, 503] or "429" in str(e) or "503" in str(e):
                # Backoff delay with randomized jitter to break server collisions
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
    parser.add_argument("--file", type=str, default="ootk_thoth_vector_engine.md")
    parser.add_argument("--topic", type=str, required=True)
    parser.add_argument("--seed", type=str, required=True)
    parser.add_argument("--significator", type=str, default="")
    
    args = parser.parse_args()
    run_ootk(args.file, args.topic, args.seed, args.significator)

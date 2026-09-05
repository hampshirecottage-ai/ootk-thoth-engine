import os
import time
import argparse
from pathlib import Path
from google import genai
from google.genai.errors import ServerError, ClientError

def run_ootk(operation_file: str, topic: str, seed: str, significator: str = ""):
    prompt_path = Path(__file__).parent.parent / "prompts" / operation_file
    if not prompt_path.exists():
        print(f"Error: Could not find prompt file at {prompt_path}")
        return

    with open(prompt_path, "r", encoding="utf-8") as f:
        system_instruction = f.read()

    execution_block = f"\n\n[RUNTIME PARAMETER EXECUTION BLOCK]\n* Target Topic: {topic}\n* PRNG Seed: {seed}"
    if significator:
        execution_block += f"\n* Significator Card: {significator}"
    
    full_prompt = system_instruction + execution_block

    client = genai.Client()
    model_name = "gemini-3.6-flash"
    print(f"Executing {operation_file} via {model_name}...")
    
    max_retries = 3
    delay = 5
    
    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=full_prompt,
                config={"temperature": 0.0}
            )
            print("\n=== OOTK ENGINE OUTPUT ===\n")
            print(response.text)
            return
        except (ServerError, ClientError) as e:
            if "503" in str(e) or "429" in str(e):
                print(f"Server busy or rate limited (Attempt {attempt}/{max_retries}). Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2
            else:
                raise e

    print("Error: Could not complete request due to high server demand. Please try again in a few minutes.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run OOTK Thoth Engine via Gemini API")
    parser.add_argument("--file", type=str, default="ootk_thoth_vector_engine.md", help="Prompt file in prompts/")
    parser.add_argument("--topic", type=str, required=True, help="Target topic for calculation")
    parser.add_argument("--seed", type=str, required=True, help="PRNG Seed value")
    parser.add_argument("--significator", type=str, default="", help="Optional Significator card")
    
    args = parser.parse_args()
    run_ootk(args.file, args.topic, args.seed, args.significator)

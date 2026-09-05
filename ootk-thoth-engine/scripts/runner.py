import argparse
from pathlib import Path

def load_prompt_template():
    prompt_path = Path(__file__).parent.parent / "prompts" / "ootk_thoth_vector_engine.md"
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

def format_execution_block(topic: str, seed: str, operation: str) -> str:
    template = load_prompt_template()
    runtime_block = f"""
[RUNTIME PARAMETER EXECUTION BLOCK]
* Target Topic: {topic}
* PRNG Seed: {seed}
* Target Operation: {operation}
"""
    if "[RUNTIME PARAMETER EXECUTION BLOCK]" in template:
        base_prompt = template.split("[RUNTIME PARAMETER EXECUTION BLOCK]")[0]
        return base_prompt + runtime_block
    return template + "\n" + runtime_block

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OOTK Thoth System Prompt Formatter")
    parser.add_argument("--topic", type=str, default="System Baseline Evaluation", help="Target topic for calculation")
    parser.add_argument("--seed", type=str, default="43765590443", help="PRNG Seed string or numeric")
    parser.add_argument("--operation", type=str, default="Operation 1", help="OOTK Operation (1 to 5)")
    
    args = parser.parse_args()
    print(format_execution_block(args.topic, args.seed, args.operation))

# OOTK Thoth Vector Engine

> A deterministic, non-conversational LLM system protocol for executing Opening of the Key (OOTK) Hermetic Tarot operations, Elemental Dignity calculations, and quantitative vector analysis using Aleister Crowley’s Thoth Tarot framework.

---

## Overview

The **OOTK Thoth Vector Engine** converts large language models into deterministic analytical processors. It bypasses standard conversational filler, psychological projection, and intuitive tarot interpretation. Instead, it processes spread topologies strictly via:

* **Golden Dawn & Liber 777 Attributions:** Direct Kabbalistic, Zodiacal, and Decan mapping.
* **Pure Upright Orientation:** Complete removal of reversed card mechanics in compliance with classic Thoth / Golden Dawn practices.
* **Elemental Dignity Matrix:** Multi-layered vector arithmetic evaluating Fire ($\Delta$), Air ($\Delta$), Water ($\nabla$), and Earth ($\nabla$) interaction coefficients.
* **Deterministic OOTK Traversal:** Accurate card-counting step values (Aces=1, Minors=2–10, Courts=4, Princesses=7, Majors=3/5/9).

---

## Repository Structure

| File Path | Description |
| :--- | :--- |
| `prompts/ootk_thoth_vector_engine.md` | The core system prompt protocol ready for LLM injection. |
| `config/default_params.json` | Default runtime parameters (PRNG seeds, target topics, and operations). |
| `scripts/runner.py` | Python helper script to populate parameters and interface with LLM APIs. |

---

## Quick Start

### 1. Manual LLM Injection
Copy the full text inside [`prompts/ootk_thoth_vector_engine.md`](prompts/ootk_thoth_vector_engine.md) and paste it as the **System Instruction / System Prompt** in your LLM interface (e.g., OpenAI Playground, Gemini API, or Claude System Prompt).

Append your execution block at the end:

```text
[RUNTIME PARAMETER EXECUTION BLOCK]
* Target Topic: Market trajectory evaluation
* PRNG Seed: 84920491823
* Target Operation: Operation 1


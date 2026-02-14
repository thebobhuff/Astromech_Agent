---
name: gemini
description: Gemini CLI for coding assistance, generation, and file analysis.
homepage: https://ai.google.dev/
metadata:
  {
    "openclaw":
      {
        "emoji": "♊️",
        "requires": {},
        "install": [],
      },
  }
---

# Gemini CLI Integration

You can use the local `scripts/llm/gemini_cli.py` script to send prompts to Google's Gemini LLM.
This is useful for outsourcing complex coding tasks, generating content, or getting a second opinion.

## Usage

Run via the terminal tool:

```bash
python scripts/llm/gemini_cli.py "Your prompt here"
```

## Options

- `prompt`: The main instruction (required).
- `--files <path1> <path2> ...`: relevant files to include as context. The script will read these files and include them in the prompt.
- `--model <model_name>`: Specific model to use (e.g., `gemini-1.5-pro`, `gemini-2.0-flash`).

## Examples

**Generate a script:**
```bash
python scripts/llm/gemini_cli.py "Write a python script to calculate fibonacci numbers"
```

**Refactor a file:**
```bash
python scripts/llm/gemini_cli.py "Refactor this code to use async/await" --files app/core/sync_script.py
```

**Analyze multiple files:**
```bash
python scripts/llm/gemini_cli.py "Explain the relationship between these files" --files app/main.py app/core/config.py
```

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure imports resolve regardless of current working directory.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

try:
    from app.core.llm import get_llm
    from langchain_core.messages import HumanMessage, SystemMessage
except ImportError as e:
    print(f"Error importing app modules: {e}")
    print("Ensure you are running within the virtual environment and all dependencies are installed.")
    sys.exit(1)

async def run_gemini(prompt: str, files: list[str] = None, model: str = None):
    try:
        # Initialize Gemini LLM
        # Defaulting to 1.5-pro for coding tasks if not specified, assuming it's available, 
        # otherwise llm.py defaults to 2.5-flash which is also good.
        llm = get_llm(provider="gemini", model_name=model)
    except Exception as e:
        print(f"Error initializing Gemini: {e}")
        sys.exit(1)

    messages = []
    
    # Add file context if provided
    if files:
        context_str = "Below are the contents of relevant files for context:\n"
        for file_path in files:
            candidate = Path(file_path)
            if not candidate.is_absolute():
                candidate = REPO_ROOT / candidate
            if candidate.exists():
                try:
                    with open(candidate, "r", encoding="utf-8") as f:
                        file_content = f.read()
                        # Use XML-like tags for clear separation
                        context_str += f"\n<file path=\"{candidate}\">\n{file_content}\n</file>\n"
                except Exception as e:
                    print(f"Warning: Could not read {candidate}: {e}", file=sys.stderr)
            else:
                print(f"Warning: File not found: {file_path}", file=sys.stderr)
        
        messages.append(SystemMessage(content=context_str))

    messages.append(HumanMessage(content=prompt))
    
    try:
        response = await llm.ainvoke(messages)
        print(response.content)
    except Exception as e:
        print(f"Error invoking Gemini: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Astromech Gemini CLI Interface")
    parser.add_argument("prompt", help="The prompt to send to Gemini")
    parser.add_argument("--files", "-f", nargs="*", help="List of file paths to include as context")
    parser.add_argument("--model", "-m", help="Specific Gemini model to use (e.g., gemini-2.0-flash)", default=None)
    
    args = parser.parse_args()
    
    asyncio.run(run_gemini(args.prompt, args.files, args.model))

if __name__ == "__main__":
    main()

"""Clean poisoned sessions by removing dead/empty AI responses and their prompts."""
import glob
import json
from pathlib import Path

DEAD_PATTERNS = {
    '(empty response)',
    '[no response was generated]', 
    '(empty)',
    '(thinking)',
    "I processed your request but wasn't able to generate a response. Please try rephrasing or starting a new session.",
    "I processed your request but wasn't able to formulate a response.",
    "I apologize, but I encountered an unexpected issue and could not generate a response. Please try again.",
}

REPO_ROOT = Path(__file__).resolve().parents[2]
sessions_dir = REPO_ROOT / "data" / "sessions"

for path in sorted(glob.glob(str(sessions_dir / "*.json"))):
    sid = Path(path).stem
    with open(path, "r") as f:
        data = json.load(f)
    
    msgs = data.get("messages", [])
    original_count = len(msgs)
    
    # Filter out dead AI messages and their preceding user prompts
    cleaned = []
    i = 0
    removed = 0
    while i < len(msgs):
        msg = msgs[i]
        if msg["role"] == "ai" and not (msg.get("tool_calls") or []):
            content = (msg.get("content") or "").strip()
            if content.lower() in {p.lower() for p in DEAD_PATTERNS} or not content:
                # Remove this dead AI message
                # Also remove the preceding user message if it was the prompt
                if cleaned and cleaned[-1]["role"] == "user":
                    cleaned.pop()
                    removed += 1
                removed += 1
                i += 1
                continue
        cleaned.append(msg)
        i += 1
    
    if removed > 0:
        data["messages"] = cleaned
        # Adjust last_summary_index to not exceed message count
        if data.get("last_summary_index", 0) > len(cleaned):
            data["last_summary_index"] = len(cleaned)
        
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"  {sid}: {original_count} -> {len(cleaned)} messages (removed {removed} dead messages)")
    else:
        print(f"  {sid}: {original_count} messages (clean)")

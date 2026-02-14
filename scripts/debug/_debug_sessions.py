"""Debug: inspect session message history."""
import glob
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sessions_dir = REPO_ROOT / "data" / "sessions"

for path in sorted(glob.glob(str(sessions_dir / "*.json"))):
    file_path = Path(path)
    sid = file_path.stem
    with open(path, "r") as f:
        data = json.load(f)
    msgs = data.get("messages", [])
    lsi = data.get("last_summary_index", "N/A")
    print(f"=== {sid}: {len(msgs)} messages, last_summary_index={lsi} ===")
    
    # Show last 20 messages
    for i, m in enumerate(msgs[-20:], start=max(0, len(msgs)-20)):
        role = m["role"]
        content = (m.get("content") or "")[:150].replace("\n", "\\n")
        tc = len(m.get("tool_calls") or [])
        tcid = m.get("tool_call_id") or ""
        extra = f" [tool_calls={tc}]" if tc else ""
        extra += f" [tcid={tcid[:20]}]" if tcid else ""
        print(f"  [{i}] {role}: {repr(content)}{extra}")
    print()

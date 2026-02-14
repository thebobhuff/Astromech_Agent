
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
GMAIL_TOOL = REPO_ROOT / "app" / "skills" / "google-workspace" / "scripts" / "gmail_tool.py"

try:
    result = subprocess.run(
        ["python", str(GMAIL_TOOL), "list-unread", "--json"],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(REPO_ROOT),
    )
    print(result.stdout)
except subprocess.CalledProcessError as e:
    print(f"Error running gmail_tool.py: {e}")
    print(f"STDOUT: {e.stdout}")
    print(f"STDERR: {e.stderr}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

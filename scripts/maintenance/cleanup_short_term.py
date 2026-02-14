import sys
from datetime import timedelta
from pathlib import Path

# Ensure imports resolve regardless of current working directory.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from app.memory.short_term import ShortTermMemoryManager

manager = ShortTermMemoryManager()
# Assuming a default session_id for cleanup, or iterate through all if necessary.
# For this task, we'll assume the current session's memories need cleaning.
# If no session_id is provided, it attempts to clean all sessions.
manager.cleanup_expired(older_than_timedelta=timedelta(hours=2))
print("Short-term memory cleanup initiated for entries older than 2 hours.")

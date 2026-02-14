import logging
import sys
from pathlib import Path

# Ensure imports resolve regardless of current working directory.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from app.memory.rag import get_vector_memory

# Configure logging to see the output from cleanup_old_memories
logging.basicConfig(level=logging.INFO)

vector_memory = get_vector_memory()
vector_memory.cleanup_old_memories(older_than_days=30)


import os
import datetime
import sys

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.memory.rag import get_vector_memory
from app.core.config import settings

def review_long_term_memory_for_cleanup():
    vector_memory = get_vector_memory()
    all_memories = vector_memory.file_store.list_all_memories()
    
    memories_to_cleanup = []
    one_month_ago = datetime.datetime.now() - datetime.timedelta(days=30)

    print(f"Reviewing long-term memories for cleanup. Memories older than {one_month_ago.strftime('%Y-%m-%d %H:%M:%S')} will be flagged.")

    for path, content in all_memories.items():
        try:
            full_file_path = vector_memory.file_store.get_full_path(path)
            if os.path.exists(full_file_path):
                mod_timestamp = os.path.getmtime(full_file_path)
                mod_datetime = datetime.datetime.fromtimestamp(mod_timestamp)

                if mod_datetime < one_month_ago:
                    memories_to_cleanup.append((path, mod_datetime))
            else:
                print(f"Warning: File not found for memory path: {path}")
        except Exception as e:
            print(f"Error processing memory path {path}: {e}")

    if memories_to_cleanup:
        print("\nMemories identified for potential cleanup (older than 1 month):")
        for path, mod_datetime in memories_to_cleanup:
            print(f"- Path: {path}, Last Modified: {mod_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("\nNo long-term memories found older than 1 month for cleanup.")

if __name__ == "__main__":
    review_long_term_memory_for_cleanup()

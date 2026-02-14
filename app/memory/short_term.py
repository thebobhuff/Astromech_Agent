"""
Short-Term Memory Manager
=========================
Stores ephemeral conversation summaries that expire at end of day.
These bridge the gap between the sliding 10-message window and
permanent long-term RAG memories.

Storage: data/memories/short_term/<session_id>/<date>.json
"""

import os
import json
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

MEMORY_DIR = "data/memories/short_term"


class ShortTermMemory(BaseModel):
    """A single short-term memory entry."""
    summary: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    message_range: str = ""  # e.g. "messages 1-10"
    session_id: str = "default"


class ShortTermStore(BaseModel):
    """All short-term memories for a session on a given day."""
    session_id: str
    date: str  # ISO date string YYYY-MM-DD
    memories: List[ShortTermMemory] = []


class ShortTermMemoryManager:
    """Manages daily short-term conversation summaries."""

    def __init__(self, storage_dir: str = MEMORY_DIR):
        self.storage_dir = os.path.abspath(storage_dir)
        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_store_path(self, session_id: str, target_date: Optional[date] = None) -> str:
        d = target_date or date.today()
        session_dir = os.path.join(self.storage_dir, session_id)
        os.makedirs(session_dir, exist_ok=True)
        return os.path.join(session_dir, f"{d.isoformat()}.json")

    def _load_store(self, session_id: str, target_date: Optional[date] = None) -> ShortTermStore:
        path = self._get_store_path(session_id, target_date)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return ShortTermStore(**data)
            except Exception as e:
                logger.error(f"Failed to load short-term store: {e}")
        
        d = target_date or date.today()
        return ShortTermStore(session_id=session_id, date=d.isoformat())

    def _save_store(self, store: ShortTermStore):
        path = self._get_store_path(store.session_id, date.fromisoformat(store.date))
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(store.model_dump(mode="json"), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save short-term store: {e}")

    def add_memory(self, session_id: str, summary: str, message_range: str = "") -> ShortTermMemory:
        """Add a short-term memory summary for today."""
        store = self._load_store(session_id)
        memory = ShortTermMemory(
            summary=summary,
            session_id=session_id,
            message_range=message_range,
        )
        store.memories.append(memory)
        self._save_store(store)
        logger.info(f"Short-term memory added for session '{session_id}': {summary[:60]}...")
        return memory

    def get_today_memories(self, session_id: str) -> List[ShortTermMemory]:
        """Get all short-term memories for today's session."""
        store = self._load_store(session_id)
        return store.memories

    def get_today_context(self, session_id: str) -> str:
        """
        Returns a formatted string of today's short-term memories
        suitable for injection into the system prompt.
        """
        memories = self.get_today_memories(session_id)
        if not memories:
            return ""

        lines = ["--- SHORT-TERM MEMORY (Today's Conversation History) ---"]
        for i, mem in enumerate(memories, 1):
            time_str = mem.timestamp.strftime("%H:%M")
            lines.append(f"[{time_str}] {mem.summary}")
        lines.append("--- END SHORT-TERM MEMORY ---")
        return "\n".join(lines)

    def cleanup_old_memories(self, session_id: Optional[str] = None, older_than_hours: int = 2):
        """
        Remove short-term memory entries older than the specified number of hours.
        
        Args:
            session_id: Specific session to clean, or None for all sessions
            older_than_hours: Entries older than this many hours will be removed
        """
        now = datetime.utcnow()
        older_than_timedelta = timedelta(hours=older_than_hours)
        
        session_dirs_to_check: List[str] = []
        if session_id:
            session_dirs_to_check = [os.path.join(self.storage_dir, session_id)]
        else:
            try:
                session_dirs_to_check = [
                    os.path.join(self.storage_dir, d)
                    for d in os.listdir(self.storage_dir)
                    if os.path.isdir(os.path.join(self.storage_dir, d))
                ]
            except FileNotFoundError:
                return

        total_removed_memories = 0
        total_removed_files = 0

        for session_dir in session_dirs_to_check:
            if not os.path.exists(session_dir):
                continue
            
            for filename in os.listdir(session_dir):
                if filename.endswith(".json"):
                    file_date_str = filename.replace(".json", "")
                    file_path = os.path.join(session_dir, filename)

                    try:
                        store_date = date.fromisoformat(file_date_str)
                        current_session_id = session_id if session_id else os.path.basename(session_dir)
                        store = self._load_store(current_session_id, store_date)
                        initial_memory_count = len(store.memories)
                        
                        store.memories = [
                            mem for mem in store.memories
                            if (now - mem.timestamp) < older_than_timedelta
                        ]
                        
                        if len(store.memories) < initial_memory_count:
                            self._save_store(store)
                            removed_in_file = initial_memory_count - len(store.memories)
                            total_removed_memories += removed_in_file
                            logger.info(f"Cleaned {removed_in_file} memories older than {older_than_hours}h from {file_path}")
                        
                        # If after filtering, the file becomes empty, remove it
                        if not store.memories:
                            os.remove(file_path)
                            total_removed_files += 1
                            logger.info(f"Removed empty short-term memory file after cleanup: {file_path}")

                    except Exception as e:
                        logger.error(f"Failed to process short-term memory file {file_path}: {e}")
        
        if total_removed_memories > 0 or total_removed_files > 0:
            logger.info(f"Short-term memory cleanup completed. Removed {total_removed_memories} individual memories and {total_removed_files} empty files.")

    def list_all(self, session_id: str) -> List[Dict[str, Any]]:
        """List all short-term memory files for a session (for API)."""
        session_dir = os.path.join(self.storage_dir, session_id)
        if not os.path.exists(session_dir):
            return []
        
        results = []
        for filename in sorted(os.listdir(session_dir)):
            if filename.endswith(".json"):
                file_date = filename.replace(".json", "")
                store = self._load_store(session_id, date.fromisoformat(file_date))
                results.append({
                    "date": file_date,
                    "count": len(store.memories),
                    "memories": [m.model_dump(mode="json") for m in store.memories]
                })
        return results

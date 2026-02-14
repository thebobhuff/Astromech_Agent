import os
import glob
from typing import List, Optional
from pydantic import BaseModel

class MemoryFile(BaseModel):
    path: str
    content: str
    last_modified: float

class LocalMemoryStore:
    def __init__(self, root_dir: str = "./data/memories"):
        self.root_dir = os.path.abspath(root_dir)
        if not os.path.exists(self.root_dir):
            os.makedirs(self.root_dir)

    @staticmethod
    def _normalize_path(value: str | MemoryFile) -> str:
        if isinstance(value, MemoryFile):
            return value.path
        return value

    def get_full_path(self, relative_path: str | MemoryFile) -> str:
        relative_path = self._normalize_path(relative_path)
        # Remove leading slashes to prevent root escape
        clean_path = relative_path.lstrip("/\\")
        full_path = os.path.join(self.root_dir, clean_path)
        
        # Security check (even though user requested full access, we keep memories contained to the memory folder for logic sake)
        if not os.path.commonpath([self.root_dir, full_path]).startswith(self.root_dir):
             raise ValueError("Path must be within memory directory")
        return full_path

    def save_memory(self, path: str, content: str) -> str:
        """Saves a memory to a specific logical path. Returns the full local path."""
        full_path = self.get_full_path(path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Ensure extension
        if not full_path.endswith(".md"):
            full_path += ".md"
            
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return full_path

    def read_memory(self, path: str | MemoryFile) -> Optional[str]:
        path = self._normalize_path(path)
        full_path = self.get_full_path(path)
        if not full_path.endswith(".md"):
            full_path += ".md"
            
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def delete_memory(self, path: str | MemoryFile):
        """Deletes a memory file from the file system."""
        path = self._normalize_path(path)
        full_path = self.get_full_path(path)
        if not full_path.endswith(".md"):
            full_path += ".md"
        if os.path.exists(full_path):
            os.remove(full_path)
            # Clean up empty directories
            dir_path = os.path.dirname(full_path)
            while dir_path != self.root_dir and not os.listdir(dir_path):
                os.rmdir(dir_path)
                dir_path = os.path.dirname(dir_path)

    def list_all_memories(self) -> dict[str, str]:
        """Returns a dictionary of all memories with their relative paths as keys and content as values."""
        all_memories = {}
        for memory_file in self.list_memories():
            relative_path = memory_file.path
            content = self.read_memory(relative_path)
            if content is not None:
                all_memories[relative_path] = content
        return all_memories

    def list_memories(self) -> List[MemoryFile]:
        """List all markdown memories relative to the memory root, with metadata."""
        pattern = os.path.join(self.root_dir, "**", "*.md")
        files = glob.glob(pattern, recursive=True)
        memory_files = []
        for full_path in files:
            if os.path.isfile(full_path):
                relative_path = os.path.relpath(full_path, self.root_dir).replace("\\", "/")
                last_modified = os.path.getmtime(full_path)
                # Content is not needed for just listing, set to empty for efficiency
                memory_files.append(MemoryFile(path=relative_path, content="", last_modified=last_modified))
        return memory_files


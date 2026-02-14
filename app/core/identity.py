import os
import json
from pathlib import Path
from pydantic import BaseModel
from typing import Optional, Dict, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]

IDENTITY_FILE = str(_REPO_ROOT / "data" / "identity.json")
CORE_FILE = str(_REPO_ROOT / "CORE.md")
USER_FILE = str(_REPO_ROOT / "USER.md")
AGENTS_FILE = str(_REPO_ROOT / "AGENTS.md")
JUDGEMENT_FILE = str(_REPO_ROOT / "JUDGEMENT.md")
MEMORY_FILE = str(_REPO_ROOT / "MEMORY.md")

_PROMPT_CACHE: Dict[str, str] = {"prompt": ""}
_PROMPT_CACHE_KEY: Optional[Tuple] = None

class AgentIdentity(BaseModel):
    name: str = "Astromech"
    personality: str = "Helpful, logical, and efficient."
    role: str = "A personal AI assistant."
    
    def to_system_prompt(self) -> str:
        prompt_parts = []
        
        # 1. Identity / Core
        if os.path.exists(CORE_FILE):
            try:
                with open(CORE_FILE, "r", encoding="utf-8") as f:
                    prompt_parts.append(f.read().strip())
            except Exception:
                prompt_parts.append(f"You are {self.name}.\nRole: {self.role}\nPersonality: {self.personality}")
        else:
            prompt_parts.append(f"You are {self.name}.\nRole: {self.role}\nPersonality: {self.personality}")

        # 2. Operational Protocols (AGENTS.md)
        if os.path.exists(AGENTS_FILE):
            try:
                with open(AGENTS_FILE, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    # Prepend a strong header if not present, to ensure LLM pays attention to protocols
                    prompt_parts.append(f"## OPERATIONAL PROTOCOLS\n{content}")
            except Exception:
                pass
        
        # 3. Judgement Framework (JUDGEMENT.md)
        if os.path.exists(JUDGEMENT_FILE):
            try:
                with open(JUDGEMENT_FILE, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    prompt_parts.append(f"## JUDGEMENT FRAMEWORK\n{content}")
            except Exception:
                pass

        # 4. User Context
        if os.path.exists(USER_FILE):
            try:
                with open(USER_FILE, "r", encoding="utf-8") as f:
                    prompt_parts.append(f.read().strip())
            except Exception:
                pass

        # 5. Memory
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    prompt_parts.append(f.read().strip())
            except Exception:
                pass

        prompt_parts.append("Always stay in character. Use the provided tools and memory context to assist the user.")
        
        return "\n\n".join(prompt_parts)


def _safe_mtime(path: str) -> Optional[float]:
    try:
        if os.path.exists(path):
            return os.path.getmtime(path)
    except Exception:
        pass
    return None


def get_cached_system_prompt(force_reload: bool = False) -> str:
    """
    Build and cache the identity system prompt.
    Cache invalidates whenever identity/core/agents/judgement/user/memory file mtimes change.
    """
    global _PROMPT_CACHE_KEY

    cache_key = (
        _safe_mtime(IDENTITY_FILE),
        _safe_mtime(CORE_FILE),
        _safe_mtime(AGENTS_FILE),
        _safe_mtime(JUDGEMENT_FILE),
        _safe_mtime(USER_FILE),
        _safe_mtime(MEMORY_FILE),
    )

    if not force_reload and _PROMPT_CACHE_KEY == cache_key and _PROMPT_CACHE["prompt"]:
        return _PROMPT_CACHE["prompt"]

    prompt = load_identity().to_system_prompt()
    _PROMPT_CACHE["prompt"] = prompt
    _PROMPT_CACHE_KEY = cache_key
    return prompt

def load_identity() -> AgentIdentity:
    if os.path.exists(IDENTITY_FILE):
        try:
            with open(IDENTITY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return AgentIdentity(**data)
        except Exception:
            return AgentIdentity() # Default
    return AgentIdentity()

def save_identity(identity: AgentIdentity):
    global _PROMPT_CACHE_KEY
    os.makedirs(os.path.dirname(IDENTITY_FILE), exist_ok=True)
    with open(IDENTITY_FILE, "w", encoding="utf-8") as f:
        json.dump(identity.model_dump(), f, indent=2)
    _PROMPT_CACHE_KEY = None
    _PROMPT_CACHE["prompt"] = ""

def is_configured() -> bool:
    return os.path.exists(IDENTITY_FILE)

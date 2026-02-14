from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any
# from app.agents.orchestrator import AgentOrchestrator # Removed to prevent early initialization
from app.memory.file_store import LocalMemoryStore
from app.memory.rag import VectorMemory
from app.memory.short_term import ShortTermMemoryManager
from app.memory.relationship_memory import (
    RelationshipMemoryStore,
    RelationshipFactInput,
)

router = APIRouter()

# Dependency Providers
def get_file_store():
    return LocalMemoryStore()

def get_rag(store: LocalMemoryStore = Depends(get_file_store)):
    return VectorMemory(store)

def get_short_term():
    return ShortTermMemoryManager()

def get_relationship_store():
    return RelationshipMemoryStore()

class MemoryRequest(BaseModel):
    path: str
    content: str
    memory_type: str = "long-term"

class SearchRequest(BaseModel):
    query: str
    k: int = 3


class RelationshipFactRequest(BaseModel):
    fact: str
    tags: List[str] = Field(default_factory=list)
    confidence: float = 0.7

@router.get("/")
def list_memories(store: LocalMemoryStore = Depends(get_file_store)):
    """List all memory files in the logical system."""
    return {"memories": store.list_memories()}

@router.post("/")
def create_memory(mem: MemoryRequest, rag: VectorMemory = Depends(get_rag)):
    """Create a new memory file and index it."""
    try:
        rag.add_memory(mem.path, mem.content, mem.memory_type)
        return {"status": "success", "path": mem.path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/all")
def list_all_memories_with_types(store: LocalMemoryStore = Depends(get_file_store)):
    """List all memories with their content and inferred type."""
    all_memories = store.list_all_memories()
    memories_with_types: Dict[str, Dict[str, str]] = {}
    for path, content in all_memories.items():
        memory_type = "core" if "core" in path.lower() else "long-term"
        memories_with_types[path] = {"content": content, "type": memory_type}
    return memories_with_types

@router.put("/")
def edit_memory(mem: MemoryRequest, rag: VectorMemory = Depends(get_rag)):
    """Edit an existing memory file."""
    try:
        rag.edit_memory(mem.path, mem.content, mem.memory_type)
        return {"status": "success", "path": mem.path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/")
def delete_memory(path: str, rag: VectorMemory = Depends(get_rag)):
    """Delete a specific memory file."""
    try:
        rag.delete_memory(path)
        return {"status": "success", "path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/content")
def get_memory_content(path: str, rag: VectorMemory = Depends(get_rag)):
    """Read a specific memory file."""
    content = rag.get_memory_content(path)
    if content is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"content": content}

@router.post("/search")
def search_memories(search: SearchRequest, rag: VectorMemory = Depends(get_rag)):
    """Semantic search over memories."""
    results = rag.search(search.query, k=search.k)
    return [{"content": d.page_content, "metadata": d.metadata} for d in results]


# --- Relationship Memory Endpoints ---

@router.get("/relationship")
def list_relationship_facts(store: RelationshipMemoryStore = Depends(get_relationship_store)):
    facts = store.list_facts()
    return {
        "count": len(facts),
        "facts": [f.model_dump(mode="json") for f in facts],
    }


@router.post("/relationship")
def upsert_relationship_fact(
    req: RelationshipFactRequest,
    store: RelationshipMemoryStore = Depends(get_relationship_store),
):
    updated = store.upsert_facts(
        [RelationshipFactInput(fact=req.fact, tags=req.tags, confidence=req.confidence)],
        source="api",
    )
    return {"updated": len(updated), "facts": [f.model_dump(mode="json") for f in updated]}


@router.post("/relationship/search")
def search_relationship_facts(
    search: SearchRequest,
    store: RelationshipMemoryStore = Depends(get_relationship_store),
):
    results = store.search(search.query, k=search.k)
    return {
        "count": len(results),
        "facts": [f.model_dump(mode="json") for f in results],
    }


@router.delete("/relationship")
def delete_relationship_fact(
    fact: str,
    store: RelationshipMemoryStore = Depends(get_relationship_store),
):
    deleted = store.delete_fact(fact)
    if not deleted:
        raise HTTPException(status_code=404, detail="Relationship fact not found")
    return {"status": "deleted", "fact": fact}


# --- Short-Term Memory Endpoints ---

@router.get("/short-term/{session_id}")
def get_short_term_memories(session_id: str, stm: ShortTermMemoryManager = Depends(get_short_term)):
    """Get today's short-term memories for a session."""
    memories = stm.get_today_memories(session_id)
    return {
        "session_id": session_id,
        "count": len(memories),
        "memories": [m.model_dump(mode="json") for m in memories]
    }

@router.get("/short-term/{session_id}/all")
def get_all_short_term_memories(session_id: str, stm: ShortTermMemoryManager = Depends(get_short_term)):
    """Get all short-term memory files for a session (including past days before cleanup)."""
    return {
        "session_id": session_id,
        "days": stm.list_all(session_id)
    }

@router.delete("/short-term/{session_id}")
def clear_short_term_memories(session_id: str, stm: ShortTermMemoryManager = Depends(get_short_term)):
    """Clear all short-term memories for a session (forces cleanup)."""
    stm.cleanup_expired(session_id)
    return {"status": "cleared", "session_id": session_id}

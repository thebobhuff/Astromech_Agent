from langchain_core.documents import Document
from app.core.config import settings
from app.memory.file_store import LocalMemoryStore
import os
import logging
from typing import List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Enable RAG — only lightweight imports at module level
try:
    from langchain_community.vectorstores import FAISS
    from langchain_community.embeddings import OllamaEmbeddings
    from langchain_openai import OpenAIEmbeddings
    try:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
    except ImportError:
        GoogleGenerativeAIEmbeddings = None

    RAG_AVAILABLE = True
except (ImportError, Exception) as e:
    print(f"Warning: RAG components disabled due to import errors: {e}")
    RAG_AVAILABLE = False


# ── Singleton holder ──────────────────────────────────────────────────────────
_vector_memory_instance: "VectorMemory | None" = None


def get_vector_memory() -> "VectorMemory":
    """Return (or create) the process-wide VectorMemory singleton."""
    global _vector_memory_instance
    if _vector_memory_instance is None:
        _vector_memory_instance = VectorMemory(LocalMemoryStore())
    return _vector_memory_instance


class VectorMemory:
    """FAISS-backed vector memory.  Use ``get_vector_memory()`` instead of
    constructing directly so embeddings + index are loaded only once."""

    def __init__(self, file_store: LocalMemoryStore):
        self.file_store = file_store
        self.vector_db = None
        self.embeddings = None

        if RAG_AVAILABLE:
            try:
                self._init_embeddings()

                if not self.embeddings:
                    raise ValueError("No embedding model could be initialized.")

                # Load existing FAISS index
                index_path = os.path.join(settings.PERSIST_DIRECTORY, "faiss_index")
                if os.path.exists(index_path):
                    self.vector_db = FAISS.load_local(
                        index_path, self.embeddings,
                        allow_dangerous_deserialization=True,
                    )
                else:
                    self.vector_db = None  # Will init on first write

            except Exception as e:
                print(f"Failed to initialize Vector DB (FAISS): {e}")

    # ── Embedding selection (no local HuggingFace / torch) ────────────────
    def _init_embeddings(self):
        """Pick the lightest available embedding backend.
        Priority: cloud provider matching DEFAULT_LLM_PROVIDER → Gemini → OpenAI → Ollama.
        HuggingFace/torch local embeddings have been removed to save ~800 MB RAM.
        """
        provider = settings.DEFAULT_LLM_PROVIDER

        # 1. OpenAI
        if provider == "openai" and settings.OPENAI_API_KEY:
            self.embeddings = OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY)
            return

        # 2. Gemini — prefer currently supported embedding models.
        if provider == "gemini" and GoogleGenerativeAIEmbeddings and settings.GOOGLE_API_KEY:
            for embed_model in (
                "models/gemini-embedding-001",
                "models/text-embedding-004",
                "models/gemini-embedding-exp-03-07",
            ):
                try:
                    self.embeddings = GoogleGenerativeAIEmbeddings(
                        google_api_key=settings.GOOGLE_API_KEY,
                        model=embed_model,
                    )
                    self.embeddings.embed_query("test")  # Verify
                    logger.info(f"Embeddings initialized: {embed_model}")
                    return
                except Exception as e:
                    logger.warning(f"Embedding model {embed_model} failed: {e}")
                    self.embeddings = None
            logger.warning("All Gemini embedding models failed. Trying fallbacks...")

        # 3. Ollama (works offline, out-of-process — zero in-process RAM cost)
        if provider == "ollama":
            self.embeddings = OllamaEmbeddings(
                base_url=settings.OLLAMA_BASE_URL,
                model="nomic-embed-text",
            )
            return

        # 4. Fallback chain: Gemini → OpenAI → Ollama (regardless of provider)
        if GoogleGenerativeAIEmbeddings and settings.GOOGLE_API_KEY and not self.embeddings:
            for embed_model in (
                "models/gemini-embedding-001",
                "models/text-embedding-004",
                "models/gemini-embedding-exp-03-07",
            ):
                try:
                    self.embeddings = GoogleGenerativeAIEmbeddings(
                        google_api_key=settings.GOOGLE_API_KEY,
                        model=embed_model,
                    )
                    self.embeddings.embed_query("test")
                    logger.info(f"Fallback embeddings initialized: {embed_model}")
                    return
                except Exception:
                    self.embeddings = None

        if settings.OPENAI_API_KEY and not self.embeddings:
            self.embeddings = OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY)
            return

        # Last resort: Ollama (assumes server is running)
        if not self.embeddings:
            logger.warning("No cloud embedding key available. Falling back to Ollama nomic-embed-text.")
            self.embeddings = OllamaEmbeddings(
                base_url=settings.OLLAMA_BASE_URL,
                model="nomic-embed-text",
            )

    def add_memory(self, path: str, content: str, memory_type: str = "long-term"):
        """Saves to file system AND indexes in Vector DB."""
        # 1. Save to File System
        full_file_path = self.file_store.save_memory(path, content)

        # 2. Add to Vector DB
        if RAG_AVAILABLE and self.embeddings:
            try:
                doc = Document(
                    page_content=content,
                    metadata={"source": path, "timestamp": str(os.path.getmtime(full_file_path))},
                )

                if self.vector_db is None:
                    self.vector_db = FAISS.from_documents([doc], self.embeddings)
                else:
                    self.vector_db.add_documents([doc])

                # Save FAISS Index
                index_path = os.path.join(settings.PERSIST_DIRECTORY, "faiss_index")
                self.vector_db.save_local(index_path)

            except Exception as e:
                print(f"Failed to index memory: {e}")

    def delete_memory(self, path: str):
        """Deletes a memory from the file system and rebuilds the Vector DB index."""
        # 1. Delete from File System
        self.file_store.delete_memory(path)

        # 2. Rebuild Vector DB (simple approach for now)
        if RAG_AVAILABLE and self.embeddings:
            try:
                # Get all remaining memories from the file system
                all_memories = self.file_store.list_all_memories()
                docs = []
                for mem_path, content in all_memories.items():
                    full_file_path = self.file_store.get_full_path(mem_path)
                    docs.append(
                        Document(
                            page_content=content,
                            metadata={"source": mem_path, "timestamp": str(os.path.getmtime(full_file_path))},
                        )
                    )

                if docs:
                    self.vector_db = FAISS.from_documents(docs, self.embeddings)
                else:
                    self.vector_db = None # No documents left

                # Save FAISS Index
                index_path = os.path.join(settings.PERSIST_DIRECTORY, "faiss_index")
                if self.vector_db:
                    self.vector_db.save_local(index_path)
                elif os.path.exists(index_path):
                    os.remove(index_path) # Remove index if no memories left

            except Exception as e:
                print(f"Failed to delete memory and rebuild index: {e}")

    def edit_memory(self, path: str, new_content: str, memory_type: str = "long-term"):
        """Edits an existing memory by deleting the old and adding a new one."""
        self.delete_memory(path)
        self.add_memory(path, new_content, memory_type)

    def get_memory_content(self, path: str) -> str | None:
        """Retrieves the content of a specific memory by its path."""
        return self.file_store.read_memory(path)

    def list_all_memories_with_types(self) -> dict[str, dict]:
        """Lists all memories with their content and inferred type."""
        all_memories = self.file_store.list_all_memories()
        memories_with_types = {}
        for path, content in all_memories.items():
            # For now, we'll infer type based on path or default to long-term
            # In a more advanced system, memory_type would be stored with the content
            memory_type = "long-term"
            if "core" in path.lower(): # Simple heuristic for "core" memories
                memory_type = "core"
            memories_with_types[path] = {"content": content, "type": memory_type}
        return memories_with_types

    def cleanup_old_memories(self, older_than_days: int = 30):
        """Identifies and deletes memories older than a specified number of days.
        """
        if not RAG_AVAILABLE:
            logger.info("RAG is not available, skipping memory cleanup.")
            return

        logger.info(f"Starting cleanup of memories older than {older_than_days} days...")
        cutoff_timestamp = (datetime.now() - timedelta(days=older_than_days)).timestamp()
        memories_to_delete = []

        for memory_file in self.file_store.list_memories():
            if memory_file.last_modified < cutoff_timestamp:
                memories_to_delete.append(memory_file.path)

        if not memories_to_delete:
            logger.info("No old memories found for cleanup.")
            return

        logger.info(f"Found {len(memories_to_delete)} memories to delete.")
        for path in memories_to_delete:
            try:
                self.delete_memory(path)
                logger.info(f"Deleted old memory: {path}")
            except Exception as e:
                logger.error(f"Error deleting memory {path}: {e}")

        logger.info("Memory cleanup completed.")



    def search(self, query: str, k: int = 3) -> List[Document]:
        """Search memory with vector similarity, with lexical fallback."""
        if not query or not query.strip():
            return []

        safe_k = max(1, int(k))

        # Primary path: vector similarity search when index is available.
        if RAG_AVAILABLE and self.vector_db is not None and self.embeddings is not None:
            try:
                return self.vector_db.similarity_search(query, k=safe_k)
            except Exception as e:
                logger.warning(f"Vector memory search failed, using lexical fallback: {e}")

        # Fallback path: keyword scoring over file-backed memories.
        try:
            query_l = query.lower()
            tokens = [t for t in query_l.split() if len(t) > 2]
            scored: List[tuple[int, Document]] = []

            for path, content in self.file_store.list_all_memories().items():
                content_l = content.lower()
                score = content_l.count(query_l)
                if score == 0 and tokens:
                    score = sum(content_l.count(tok) for tok in tokens)
                if score > 0:
                    scored.append(
                        (
                            score,
                            Document(
                                page_content=content,
                                metadata={"source": path, "retrieval": "lexical"},
                            ),
                        )
                    )

            scored.sort(key=lambda item: item[0], reverse=True)
            return [doc for _, doc in scored[:safe_k]]
        except Exception as e:
            logger.warning(f"Lexical memory fallback failed: {e}")
            return []



from langchain.tools import tool
import logging

from app.memory.rag import get_vector_memory

logger = logging.getLogger(__name__)


@tool
def save_memory(path: str, content: str) -> str:
    """
    Save important information to long-term vector memory (RAG).

    Args:
        path: Logical memory path (for example: "users/default_user/preferences/editor").
        content: The memory content to store.
    """
    try:
        memory = get_vector_memory()
        memory.add_memory(path=path, content=content)
        return f"Saved memory to '{path}'."
    except Exception as e:
        logger.error(f"save_memory failed for path '{path}': {e}")
        return f"Error saving memory: {e}"


def get_memory_tools():
    return [save_memory]

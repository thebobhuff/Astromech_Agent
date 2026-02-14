from typing import Any, Dict, List, Tuple
import asyncio
import logging
import os

from app.agents.orchestrator_types import EvaluatorOutput
from app.core.models import AgentSession

logger = logging.getLogger(__name__)


async def build_memory_context(
    *,
    orchestrator: Any,
    user_prompt: str,
    eval_result: EvaluatorOutput,
    session: AgentSession,
    request_channel_context: str,
    log_ctx: Dict[str, Any],
) -> Tuple[str, List[str], List[str]]:
    logger.info(
        "Searching memory (queries=%d)",
        len(eval_result.memory_queries),
        extra=log_ctx,
    )

    dedup_queries = [q.strip() for q in eval_result.memory_queries if q and q.strip()]
    dedup_queries = list(dict.fromkeys(dedup_queries))
    if not dedup_queries and user_prompt.strip():
        dedup_queries = [user_prompt.strip()]

    async def _search_relationship_memory(query: str) -> str:
        return await asyncio.to_thread(orchestrator.relationship_memory.to_context_block, query, 3)

    async def _search_memory(query: str) -> Any:
        return await asyncio.to_thread(orchestrator.memory.search, query, 2)

    relationship_results = await asyncio.gather(
        *[_search_relationship_memory(q) for q in dedup_queries],
        return_exceptions=True,
    )

    relationship_blocks: List[str] = []
    seen_relationship_blocks = set()
    for idx, result in enumerate(relationship_results):
        if isinstance(result, Exception):
            q = dedup_queries[idx] if idx < len(dedup_queries) else "<unknown>"
            logger.warning(
                "Relationship memory search failed for query '%s': %s",
                q[:50],
                result,
                extra=log_ctx,
            )
            continue
        block = str(result or "").strip()
        if block and block not in seen_relationship_blocks:
            seen_relationship_blocks.add(block)
            relationship_blocks.append(block)

    query_results = await asyncio.gather(
        *[_search_memory(q) for q in dedup_queries],
        return_exceptions=True,
    )

    memories: List[str] = []
    seen_memory_chunks = set()
    for idx, result in enumerate(query_results):
        if isinstance(result, Exception):
            q = dedup_queries[idx] if idx < len(dedup_queries) else "<unknown>"
            logger.warning(
                "Memory search failed for query '%s': %s",
                q[:50],
                result,
                extra=log_ctx,
            )
            continue
        for doc in result:
            content = str(getattr(doc, "page_content", "")).strip()
            if not content or content in seen_memory_chunks:
                continue
            seen_memory_chunks.add(content)
            memories.append(content)

    memory_context = "\n---\n".join(memories)
    if relationship_blocks:
        relationship_context = "\n\n".join(relationship_blocks)
        memory_context = (
            f"{relationship_context}\n\n{memory_context}" if memory_context else relationship_context
        )

    if session.context_files:
        memory_context += (
            f"\n\n[Active Context Files: {', '.join([os.path.basename(f) for f in session.context_files])}]"
        )
    memory_context += f"\n\n[{request_channel_context}]"

    logger.info(
        "Memory search complete (relationship=%d fragments=%d)",
        len(relationship_blocks),
        len(memories),
        extra=log_ctx,
    )

    return memory_context, relationship_blocks, memories

import asyncio
import json as _json
import logging

from langchain_core.messages import HumanMessage

from app.agents.orchestrator_context import log_extra
from app.core.config import settings
from app.core.models import AgentSession

logger = logging.getLogger(__name__)


async def summarize_to_short_term(*, orchestrator: object, session: AgentSession) -> None:
    """
    Summarize unsummarized messages in session into short-term memory.
    """
    from app.agents.context_manager import SUMMARY_INTERVAL

    start_idx = session.last_summary_index
    end_idx = len(session.messages)

    if end_idx - start_idx < SUMMARY_INTERVAL:
        return

    messages_to_summarize = session.messages[start_idx:end_idx]

    transcript_lines = []
    for msg in messages_to_summarize:
        role = msg.role.upper()
        content = msg.content
        if not content or not content.strip():
            continue
        if msg.role == "tool" and len(content) > 300:
            content = content[:300] + "..."
        transcript_lines.append(f"{role}: {content}")

    if not transcript_lines:
        session.last_summary_index = end_idx
        return

    transcript = "\n".join(transcript_lines)

    summary_prompt = f"""Summarize this conversation segment into a concise paragraph (2-4 sentences).
Focus on: what the user asked for, what actions were taken, what results were produced, and any important decisions or facts mentioned.
Do NOT include greetings or filler. Be factual and specific.

Also determine if anything in this conversation is significant enough to be a LONG-TERM MEMORY.
Long-term memories are: user preferences, important facts about the user, key decisions, learned capabilities, or critical information that should be remembered permanently.

Respond in this JSON format:
{{
  "summary": "The concise summary of this conversation segment.",
  "long_term_memory": null or "A specific fact/preference worth remembering permanently."
}}

CONVERSATION:
{transcript}"""

    try:
        meta_timeout_seconds = max(5, min(int(settings.AGENT_LLM_TIMEOUT_SECONDS), 6))
        response = await asyncio.wait_for(
            orchestrator.meta_llm.ainvoke([HumanMessage(content=summary_prompt)]),
            timeout=meta_timeout_seconds,
        )

        content = response.content if hasattr(response, "content") else str(response)

        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = _json.loads(content[start:end])
                summary = parsed.get("summary", content)
                long_term = parsed.get("long_term_memory")
            else:
                summary = content
                long_term = None
        except (_json.JSONDecodeError, Exception):
            summary = content
            long_term = None

        msg_range = f"messages {start_idx + 1}-{end_idx}"
        orchestrator.short_term_memory.add_memory(session.session_id, summary, msg_range)
        logger.info(
            "Short-term memory saved: %s...",
            summary[:80],
            extra=log_extra(session_id=session.session_id, event="summary"),
        )

        if long_term and long_term.strip() and long_term.lower() not in ("null", "none"):
            lt_path = f"long_term/{session.session_id}/auto_{end_idx}"
            orchestrator.memory.add_memory(lt_path, long_term)
            logger.info(
                "Long-term memory saved to %s: %s...",
                lt_path,
                long_term[:80],
                extra=log_extra(session_id=session.session_id, event="summary"),
            )

        session.last_summary_index = end_idx

    except Exception as e:
        logger.warning(
            "Summarization error: %s",
            e,
            extra=log_extra(session_id=session.session_id, event="summary"),
        )
        session.last_summary_index = end_idx

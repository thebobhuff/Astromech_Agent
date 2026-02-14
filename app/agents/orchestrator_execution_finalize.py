import asyncio
from typing import Any, List, Optional, Tuple
import logging

from langchain_core.messages import AIMessage, HumanMessage

from app.core.config import settings
from app.core.models import AgentSession
from app.agents.session_manager import SessionManager

logger = logging.getLogger(__name__)


async def finalize_execution_output(
    *,
    orchestrator: Any,
    messages: List[Any],
    turn_history: List[Any],
    final_answer: Optional[str],
    max_turns: int,
    exec_ctx: dict,
    executor_llm: Any,
    session: AgentSession,
    session_manager: SessionManager,
) -> Tuple[str, bool]:
    hit_turn_limit = False

    if final_answer is None:
        hit_turn_limit = True
        logger.warning("Max turns reached (%d); forcing final text response", max_turns, extra=exec_ctx)

        status_prompt = (
            f"SYSTEM: You have used all {max_turns} execution turns. "
            "You MUST respond with text now - absolutely no tool calls. "
            "Provide a complete response based on everything you accomplished. "
            "Include any partial results and next steps if applicable."
        )
        try:
            messages.append(HumanMessage(content=status_prompt))
            messages = orchestrator.context_manager.sanitize_messages(messages)
            summary_ai_msg = await asyncio.wait_for(
                executor_llm.ainvoke(messages),
                timeout=max(min(int(settings.AGENT_LLM_TIMEOUT_SECONDS), 30), 1),
            )
            raw_content = summary_ai_msg.content
            if isinstance(raw_content, list):
                final_answer = "".join(
                    [b.get("text", "") if isinstance(b, dict) else str(b) for b in raw_content]
                ).strip()
            elif raw_content:
                final_answer = str(raw_content).strip()
            else:
                final_answer = ""
        except Exception as e:
            logger.warning("Post-loop summary failed: %s", e, extra=exec_ctx)
            final_answer = ""

    if not final_answer or not final_answer.strip():
        final_answer = "I wasn't able to generate a response. Please try again or rephrase your request."
        turn_history_to_save = [m for m in turn_history if not isinstance(m, AIMessage)]
    else:
        final_ai_msg = AIMessage(content=final_answer)
        turn_history.append(final_ai_msg)
        turn_history_to_save = turn_history

    for msg in turn_history_to_save:
        session.messages.append(session_manager.langchain_to_dict(msg))

    session.trim_messages()

    return final_answer, hit_turn_limit

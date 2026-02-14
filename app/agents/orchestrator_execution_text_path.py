from typing import Any, Dict, List
import logging

from langchain_core.messages import HumanMessage, ToolMessage

from app.agents.orchestrator_execution_utils import (
    extract_text_content,
    is_hallucinated_tool_text,
    is_placeholder_text,
)

logger = logging.getLogger(__name__)


def handle_text_response(
    *,
    ai_msg: Any,
    messages: List[Any],
    turn_history: List[Any],
    nudge_count: int,
    turn_ctx: Dict[str, Any],
) -> Dict[str, Any]:
    logger.info(
        "LLM returned text (content_type=%s, len=%d)",
        type(ai_msg.content).__name__,
        len(str(ai_msg.content)),
        extra=turn_ctx,
    )
    content = ai_msg.content
    final_answer = extract_text_content(content)

    if final_answer and is_hallucinated_tool_text(final_answer):
        logger.warning(
            "Detected hallucinated tool call text: %s...",
            final_answer[:100],
            extra=turn_ctx,
        )
        trap_msg = HumanMessage(
            content="[SYSTEM: You output a text description/simulation of a tool call, but you did NOT execute the real tool. "
            "STOP simulating. USE THE NATIVE TOOL (e.g. 'terminal', 'write_local_file') to execute this action immediately. "
            "Do not just say you are doing it.]"
        )
        messages.append(trap_msg)
        turn_history.append(trap_msg)
        return {
            "continue_turn": True,
            "break_loop": False,
            "turn_increment": 1,
            "nudge_count": nudge_count,
            "final_answer": None,
        }

    if final_answer and is_placeholder_text(final_answer):
        logger.warning("LLM parroted placeholder: %r", final_answer, extra=turn_ctx)
        final_answer = None

    if not final_answer:
        logger.warning("LLM returned empty content: %r", content, extra=turn_ctx)
        if nudge_count < 3:
            if any(isinstance(m, ToolMessage) for m in turn_history):
                nudge_msg = HumanMessage(
                    content="[SYSTEM: You just received tool results above. "
                    "Now synthesize those results into a clear, helpful response for the user. "
                    "Do NOT call any more tools - respond with text only.]"
                )
            else:
                nudge_msg = HumanMessage(
                    content="[SYSTEM: Your previous response was empty. "
                    "Please provide a substantive response to the user's request.]"
                )
            messages.append(nudge_msg)
            turn_history.append(nudge_msg)
            return {
                "continue_turn": True,
                "break_loop": False,
                "turn_increment": 1,
                "nudge_count": nudge_count + 1,
                "final_answer": None,
            }

        final_answer = (
            "I processed your request but wasn't able to generate a response. "
            "Please try rephrasing or starting a new session."
        )

    return {
        "continue_turn": False,
        "break_loop": True,
        "turn_increment": 0,
        "nudge_count": nudge_count,
        "final_answer": final_answer,
    }

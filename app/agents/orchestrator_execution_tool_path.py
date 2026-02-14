import asyncio
from typing import Any, Awaitable, Callable, Dict, List, Optional
import logging

from langchain_core.messages import AIMessage, HumanMessage

from app.agents.orchestrator_tool_runner import execute_tool_batch
from app.core.config import settings

logger = logging.getLogger(__name__)


async def handle_tool_response(
    *,
    ai_msg: Any,
    messages: List[Any],
    turn_history: List[Any],
    recent_call_signatures: List[Any],
    orchestrator: Any,
    executor_llm: Any,
    full_tool_map: Dict[str, Any],
    session_id: str,
    turn_num: int,
    tool_timeout_seconds: int,
    tool_retry_attempts: int,
    stream_emit: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]],
    turn_ctx: Dict[str, Any],
) -> Dict[str, Any]:
    tool_names_called = [tc["name"] for tc in ai_msg.tool_calls]
    logger.info(
        "Tool call batch detected (count=%d tools=%s)",
        len(ai_msg.tool_calls),
        tool_names_called,
        extra=turn_ctx,
    )
    if stream_emit:
        await stream_emit("tool_start", {"turn": turn_num + 1, "tools": tool_names_called})

    turn_sigs = []
    for tc in ai_msg.tool_calls:
        args = tc["args"]
        sig = (tc["name"], str(sorted(args.items()) if isinstance(args, dict) else args))
        turn_sigs.append(sig)

    batch_sig = tuple(turn_sigs)
    recent_call_signatures.append(batch_sig)

    if len(recent_call_signatures) >= 3:
        last_3 = recent_call_signatures[-3:]
        if last_3[0] == last_3[1] == last_3[2]:
            logger.warning("Tool-call loop detected; same calls repeated for 3 turns", extra=turn_ctx)
            loop_msg = HumanMessage(
                content="[SYSTEM: You are stuck in a loop, calling the same tools repeatedly with "
                "the same arguments. STOP calling tools. Respond with TEXT only - summarize "
                "what you have so far and ask the user for clarification if needed.]"
            )
            messages.append(loop_msg)
            turn_history.append(loop_msg)
            messages[:] = orchestrator.context_manager.sanitize_messages(messages)
            final_answer = None
            try:
                forced = await asyncio.wait_for(
                    executor_llm.ainvoke(messages),
                    timeout=max(min(int(settings.AGENT_LLM_TIMEOUT_SECONDS), 30), 1),
                )
                raw = forced.content
                if isinstance(raw, list):
                    final_answer = "".join(
                        [b.get("text", "") if isinstance(b, dict) else str(b) for b in raw]
                    ).strip()
                elif raw:
                    final_answer = str(raw).strip()
            except Exception as e:
                logger.warning("Forced text after loop detection failed: %s", e, extra=turn_ctx)
            return {
                "break_loop": True,
                "final_answer": final_answer,
                "turn_increment": 0,
            }

    if not ai_msg.content or (isinstance(ai_msg.content, str) and not ai_msg.content.strip()):
        ai_msg = AIMessage(content="(calling tools)", tool_calls=ai_msg.tool_calls)

    messages.append(ai_msg)
    turn_history.append(ai_msg)

    tool_messages, results_summary, valid_tool_names = await execute_tool_batch(
        tool_calls=ai_msg.tool_calls,
        full_tool_map=full_tool_map,
        session_id=session_id,
        turn_num=turn_num,
        tool_timeout_seconds=tool_timeout_seconds,
        tool_retry_attempts=tool_retry_attempts,
        stream_emit=stream_emit,
    )
    for tool_msg in tool_messages:
        messages.append(tool_msg)
        turn_history.append(tool_msg)

    if stream_emit and valid_tool_names:
        await stream_emit("tool_done", {"turn": turn_num + 1, "results": results_summary})

    return {
        "break_loop": False,
        "final_answer": None,
        "turn_increment": 1,
    }

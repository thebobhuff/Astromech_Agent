from typing import Any, Callable, Dict, List, Optional, Tuple
import asyncio
import logging

from langchain_core.messages import HumanMessage

from app.agents.failover import FailoverChain
from app.agents.orchestrator_context import log_extra as _log_extra
from app.agents.orchestrator_execution_finalize import finalize_execution_output
from app.agents.orchestrator_execution_recovery import invoke_llm_with_recovery
from app.agents.orchestrator_execution_text_path import handle_text_response
from app.agents.orchestrator_execution_tool_path import handle_tool_response
from app.agents.orchestrator_types import RouterOutput
from app.agents.run_registry import RunHandle, update_run_turn
from app.agents.session_manager import SessionManager
from app.core.models import AgentSession

logger = logging.getLogger(__name__)


async def run_turn_loop(
    *,
    orchestrator: Any,
    session: AgentSession,
    run_handle: Optional[RunHandle],
    failover: Optional[FailoverChain],
    route: RouterOutput,
    messages: List[Any],
    human_msg: HumanMessage,
    full_tool_map: Dict[str, Any],
    tool_timeout_seconds: int,
    tool_retry_attempts: int,
    llm_timeout_seconds: int,
    stream_emit: Optional[Callable[..., Any]],
    full_system_prompt: str,
    tools_to_bind: List[Any],
    executor_llm: Any,
    llm_with_tools: Any,
    exec_ctx: Dict[str, Any],
    session_manager: SessionManager,
) -> Tuple[str, bool]:
    MAX_TURNS = 30
    final_answer: Optional[str] = None
    turn_history: List[Any] = [human_msg]
    recent_call_signatures: List[Tuple[Any, ...]] = []
    nudge_count = 0

    turn_num = 0
    while turn_num < MAX_TURNS:
        turn_ctx = _log_extra(
            session_id=session.session_id,
            turn=turn_num + 1,
            event="execute",
        )

        if run_handle and run_handle.abort_event.is_set():
            logger.info(
                "Run aborted by registry (reason=%s)",
                run_handle.cancel_reason,
                extra=turn_ctx,
            )
            final_answer = f"[Run cancelled: {run_handle.cancel_reason or 'user request'}]"
            break

        if run_handle:
            while not run_handle.steer_queue.empty():
                try:
                    steer_text = run_handle.steer_queue.get_nowait()
                    steer_msg = HumanMessage(content=f"[USER STEERING]: {steer_text}")
                    messages.append(steer_msg)
                    turn_history.append(steer_msg)
                    logger.info("Injected steer message: %s...", steer_text[:80], extra=turn_ctx)
                except asyncio.QueueEmpty:
                    break

        if run_handle:
            update_run_turn(session.session_id, turn_num + 1)

        if turn_num >= MAX_TURNS - 2:
            current_llm = executor_llm
            if turn_num == MAX_TURNS - 2:
                wrap_msg = HumanMessage(
                    content="[SYSTEM: You are running low on execution capacity. "
                    "Wrap up NOW and provide your final response to the user. "
                    "Do NOT make any more tool calls - respond with text only.]"
                )
                messages.append(wrap_msg)
                turn_history.append(wrap_msg)
        else:
            current_llm = llm_with_tools

        messages = orchestrator.context_manager.sanitize_messages(messages)
        logger.info(
            "Invoking LLM (messages=%d max_turns=%d)",
            len(messages),
            MAX_TURNS,
            extra=turn_ctx,
        )

        bound_tool_check = getattr(current_llm, "bound", None) or hasattr(current_llm, "first")
        logger.info(
            "LLM call setup type=%s has_bound_tools=%s",
            type(current_llm).__name__,
            bound_tool_check,
            extra=turn_ctx,
        )

        invoke_result = await invoke_llm_with_recovery(
            current_llm=current_llm,
            messages=messages,
            llm_timeout_seconds=llm_timeout_seconds,
            failover=failover,
            tools_to_bind=tools_to_bind,
            executor_llm=executor_llm,
            llm_with_tools=llm_with_tools,
            turn_num=turn_num,
            max_turns=MAX_TURNS,
            route=route,
            full_system_prompt=full_system_prompt,
            stream_emit=stream_emit,
            turn_ctx=turn_ctx,
        )
        executor_llm = invoke_result["executor_llm"]
        llm_with_tools = invoke_result["llm_with_tools"]
        if invoke_result["retry_turn"]:
            continue
        if invoke_result["ai_msg"] is None:
            final_answer = invoke_result["final_answer"]
            break
        ai_msg = invoke_result["ai_msg"]

        if not getattr(ai_msg, "tool_calls", None):
            text_result = handle_text_response(
                ai_msg=ai_msg,
                messages=messages,
                turn_history=turn_history,
                nudge_count=nudge_count,
                turn_ctx=turn_ctx,
            )
            nudge_count = text_result["nudge_count"]
            final_answer = text_result["final_answer"]
            if text_result["continue_turn"]:
                turn_num += text_result["turn_increment"]
                continue
            if text_result["break_loop"]:
                break

        tool_result = await handle_tool_response(
            ai_msg=ai_msg,
            messages=messages,
            turn_history=turn_history,
            recent_call_signatures=recent_call_signatures,
            orchestrator=orchestrator,
            executor_llm=executor_llm,
            full_tool_map=full_tool_map,
            session_id=session.session_id,
            turn_num=turn_num,
            tool_timeout_seconds=tool_timeout_seconds,
            tool_retry_attempts=tool_retry_attempts,
            stream_emit=stream_emit,
            turn_ctx=turn_ctx,
        )
        final_answer = tool_result["final_answer"]
        if tool_result["break_loop"]:
            break
        turn_num += tool_result["turn_increment"]

    return await finalize_execution_output(
        orchestrator=orchestrator,
        messages=messages,
        turn_history=turn_history,
        final_answer=final_answer,
        max_turns=MAX_TURNS,
        exec_ctx=exec_ctx,
        executor_llm=executor_llm,
        session=session,
        session_manager=session_manager,
    )

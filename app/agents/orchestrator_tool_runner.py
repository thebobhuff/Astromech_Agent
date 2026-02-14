from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple
import asyncio
import logging

from langchain_core.messages import ToolMessage

from app.agents.orchestrator_context import log_extra as _log_extra
from app.core.guardian import guardian

logger = logging.getLogger(__name__)


def _is_retryable_tool_error(err: Exception) -> bool:
    text = str(err).lower()
    markers = (
        "timeout",
        "timed out",
        "temporarily",
        "temporary",
        "429",
        "rate limit",
        "connection reset",
        "connection refused",
        "service unavailable",
        "gateway",
        "dns",
    )
    return any(m in text for m in markers)


async def _execute_single_tool(
    *,
    tool_call: Dict[str, Any],
    full_tool_map: Dict[str, Any],
    session_id: str,
    turn_num: int,
    tool_timeout_seconds: int,
    tool_retry_attempts: int,
    stream_emit: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]],
) -> ToolMessage:
    t_name = tool_call["name"]
    t_args = tool_call["args"]
    t_id = tool_call.get("id")

    logger.info(
        "Executing tool",
        extra=_log_extra(
            session_id=session_id,
            turn=turn_num + 1,
            tool=t_name,
            event="tool",
        ),
    )

    is_safe, reason, action_id = guardian.validate_tool_call(t_name, t_args)
    if not is_safe:
        logger.warning(
            "Guardian blocked tool call: %s",
            reason,
            extra=_log_extra(
                session_id=session_id,
                turn=turn_num + 1,
                tool=t_name,
                event="guardian",
            ),
        )
        output = (
            "ACTION BLOCKED BY SECURITY PROTOCOL.\n"
            f"Reason: {reason}\n"
            f"Action ID: {action_id}\n\n"
            f"INSTRUCTION: You must inform the user that this action requires approval. Ask them to approve Action ID '{action_id}'."
        )
        return ToolMessage(content=str(output), tool_call_id=t_id, name=t_name)

    output = None
    last_err: Optional[Exception] = None
    for tool_attempt in range(1, tool_retry_attempts + 1):
        try:
            output = await asyncio.wait_for(
                full_tool_map[t_name].ainvoke(t_args),
                timeout=tool_timeout_seconds,
            )
            break
        except Exception as e:
            last_err = e
            retryable = _is_retryable_tool_error(e)
            if tool_attempt >= tool_retry_attempts or not retryable:
                break
            delay = min(0.75 * tool_attempt, 3.0)
            logger.warning(
                "Tool %s failed (attempt %d/%d), retrying in %.2fs: %s",
                t_name,
                tool_attempt,
                tool_retry_attempts,
                delay,
                e,
                extra=_log_extra(
                    session_id=session_id,
                    turn=turn_num + 1,
                    tool=t_name,
                    event="tool",
                ),
            )
            if stream_emit:
                await stream_emit(
                    "phase",
                    {
                        "phase": "recovery",
                        "message": f"Recovering from tool error: retrying {t_name} ({tool_attempt + 1}/{tool_retry_attempts})",
                    },
                )
            await asyncio.sleep(delay)

    if output is None and last_err is not None:
        output = f"Error executing tool {t_name}: {last_err}"

    return ToolMessage(content=str(output), tool_call_id=t_id, name=t_name)


async def execute_tool_batch(
    *,
    tool_calls: List[Dict[str, Any]],
    full_tool_map: Dict[str, Any],
    session_id: str,
    turn_num: int,
    tool_timeout_seconds: int,
    tool_retry_attempts: int,
    stream_emit: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]],
) -> Tuple[List[ToolMessage], List[Dict[str, str]], List[str]]:
    valid_calls: List[Dict[str, Any]] = []
    invalid_calls: List[Dict[str, Any]] = []

    for tool_call in tool_calls:
        if tool_call.get("name") in full_tool_map:
            valid_calls.append(tool_call)
        else:
            invalid_calls.append(tool_call)

    tool_messages: List[ToolMessage] = []
    results_summary: List[Dict[str, str]] = []

    tool_results: List[Any] = []
    if valid_calls:
        tool_results = await asyncio.gather(
            *[
                _execute_single_tool(
                    tool_call=tc,
                    full_tool_map=full_tool_map,
                    session_id=session_id,
                    turn_num=turn_num,
                    tool_timeout_seconds=tool_timeout_seconds,
                    tool_retry_attempts=tool_retry_attempts,
                    stream_emit=stream_emit,
                )
                for tc in valid_calls
            ],
            return_exceptions=True,
        )

        for i, result in enumerate(tool_results):
            if isinstance(result, Exception):
                tc = valid_calls[i]
                result = ToolMessage(
                    content=f"Error executing tool {tc['name']}: {result}",
                    tool_call_id=tc.get("id"),
                    name=tc["name"],
                )
            tool_messages.append(result)

        for i, tc in enumerate(valid_calls):
            out_text = ""
            if i < len(tool_results) and not isinstance(tool_results[i], Exception):
                out_text = str(tool_results[i].content)[:200]
            results_summary.append({"tool": tc["name"], "preview": out_text})

    for tc in invalid_calls:
        tool_messages.append(
            ToolMessage(
                content=f"Error: Tool '{tc['name']}' not found.",
                tool_call_id=tc.get("id"),
                name=tc["name"],
            )
        )

    return tool_messages, results_summary, [tc["name"] for tc in valid_calls]

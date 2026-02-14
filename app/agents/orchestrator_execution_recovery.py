from typing import Any, Awaitable, Callable, Dict, List, Optional
import asyncio
import logging

from langchain_core.messages import SystemMessage

from app.agents.error_handler import classify_error, get_recovery_plan, RecoveryStrategy
from app.agents.failover import FailoverChain
from app.agents.orchestrator_types import RouterOutput

logger = logging.getLogger(__name__)

_TOOL_UNFRIENDLY_FAILOVER_PROVIDERS = {"nvidia"}


def _should_skip_failover_candidate(provider: str, tools_to_bind: List[Any]) -> bool:
    # NVIDIA/Kimi currently warns about uncertain tool-call support in this runtime.
    # If tools are required for this turn, prefer providers with stable tool binding.
    if tools_to_bind and provider in _TOOL_UNFRIENDLY_FAILOVER_PROVIDERS:
        return True
    return False


async def _ainvoke_with_deadline(current_llm: Any, messages: List[Any], timeout_seconds: int) -> Any:
    timeout_seconds = max(int(timeout_seconds), 1)
    task = asyncio.create_task(current_llm.ainvoke(messages))
    done, _ = await asyncio.wait({task}, timeout=timeout_seconds, return_when=asyncio.FIRST_COMPLETED)
    if task in done:
        return await task

    # Do not block waiting for provider cancellation if its SDK ignores cancellation.
    task.cancel()

    def _drain_cancelled_task(t: asyncio.Task) -> None:
        try:
            _ = t.exception()
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    task.add_done_callback(_drain_cancelled_task)
    raise asyncio.TimeoutError(f"LLM invocation timed out after {timeout_seconds}s")


async def invoke_llm_with_recovery(
    *,
    current_llm: Any,
    messages: List[Any],
    llm_timeout_seconds: int,
    failover: Optional[FailoverChain],
    tools_to_bind: List[Any],
    executor_llm: Any,
    llm_with_tools: Any,
    turn_num: int,
    max_turns: int,
    route: RouterOutput,
    full_system_prompt: str,
    stream_emit: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]],
    turn_ctx: Dict[str, Any],
) -> Dict[str, Any]:
    try:
        ai_msg = await _ainvoke_with_deadline(current_llm, messages, llm_timeout_seconds)
        return {
            "retry_turn": False,
            "ai_msg": ai_msg,
            "final_answer": None,
            "executor_llm": executor_llm,
            "llm_with_tools": llm_with_tools,
        }
    except Exception as invoke_err:
        classified = classify_error(invoke_err, context="llm.ainvoke")
        strategy = get_recovery_plan(classified, turn_num + 1)
        logger.warning(
            "LLM invoke error: %s -> %s",
            classified,
            strategy.value,
            extra=turn_ctx,
        )

        if strategy in (RecoveryStrategy.ROTATE_MODEL, RecoveryStrategy.COMPACT_CONTEXT) and failover and not failover.is_exhausted():
            advanced = failover.advance(reason=str(invoke_err))
            while advanced and _should_skip_failover_candidate(
                failover.current_provider,
                tools_to_bind,
            ):
                logger.info(
                    "Skipping failover candidate %s/%s due to tool-call compatibility constraints",
                    failover.current_provider,
                    failover.current_model,
                    extra=turn_ctx,
                )
                advanced = failover.advance(reason="skipped: tool-call compatibility")

            if advanced:
                try:
                    executor_llm = failover.get_llm()
                    if tools_to_bind:
                        try:
                            llm_with_tools = executor_llm.bind_tools(tools_to_bind)
                        except Exception:
                            llm_with_tools = executor_llm
                    else:
                        llm_with_tools = executor_llm

                    new_provider = failover.current_provider or ""
                    if new_provider != route.provider:
                        logger.info(
                            "Provider changed (%s -> %s), rebuilding system prompt",
                            route.provider,
                            new_provider,
                            extra=turn_ctx,
                        )
                        for mi, m in enumerate(messages):
                            if isinstance(m, SystemMessage):
                                provider_note = (
                                    f"\n\n[SYSTEM NOTE: You are running on {new_provider}/{failover.current_model}. Respond concisely.]"
                                )
                                messages[mi] = SystemMessage(content=full_system_prompt + provider_note)
                                break

                    logger.info(
                        "Failover mid-loop -> %s/%s",
                        failover.current_provider,
                        failover.current_model,
                        extra=turn_ctx,
                    )
                    if stream_emit:
                        await stream_emit(
                            "phase",
                            {
                                "phase": "recovery",
                                "message": f"Model failover to {failover.current_provider}/{failover.current_model}",
                            },
                        )
                    return {
                        "retry_turn": True,
                        "ai_msg": None,
                        "final_answer": None,
                        "executor_llm": executor_llm,
                        "llm_with_tools": llm_with_tools,
                    }
                except Exception:
                    pass

        if strategy == RecoveryStrategy.REDUCE_CONTEXT or len(messages) > 5:
            logger.info("Retrying with reduced context", extra=turn_ctx)
            if stream_emit:
                await stream_emit(
                    "phase",
                    {"phase": "recovery", "message": "Retrying with reduced context"},
                )
            system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
            non_system = [m for m in messages if not isinstance(m, SystemMessage)]
            trimmed = system_msgs + non_system[-4:]
            try:
                ai_msg = await _ainvoke_with_deadline(current_llm, trimmed, llm_timeout_seconds)
                return {
                    "retry_turn": False,
                    "ai_msg": ai_msg,
                    "final_answer": None,
                    "executor_llm": executor_llm,
                    "llm_with_tools": llm_with_tools,
                }
            except Exception as retry_err:
                logger.error("Reduced-context retry failed: %s", retry_err, extra=turn_ctx)
                return {
                    "retry_turn": False,
                    "ai_msg": None,
                    "final_answer": f"I encountered an error communicating with the LLM: {invoke_err}",
                    "executor_llm": executor_llm,
                    "llm_with_tools": llm_with_tools,
                }

        return {
            "retry_turn": False,
            "ai_msg": None,
            "final_answer": f"I encountered an error communicating with the LLM: {invoke_err}",
            "executor_llm": executor_llm,
            "llm_with_tools": llm_with_tools,
        }

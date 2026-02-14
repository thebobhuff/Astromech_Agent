from typing import Any, Callable, Dict, List, Optional, Tuple
import logging

from app.agents.failover import FailoverChain
from app.agents.orchestrator_context import log_extra
from app.agents.orchestrator_types import RouterOutput
from app.agents.run_registry import RunHandle, complete_run, register_run
from app.agents.error_handler import classify_error, get_recovery_plan, RecoveryStrategy
from app.core.config import settings
from app.core.models import AgentSession

logger = logging.getLogger(__name__)


async def execute_with_retries(
    *,
    orchestrator: Any,
    user_prompt: str,
    images: Optional[List[str]],
    memory_context: str,
    route_result: RouterOutput,
    session: AgentSession,
    session_tool_map: Dict[str, Any],
    source_channel: str,
    source_metadata: Optional[Dict[str, Any]],
    stream_emit: Optional[Callable[..., Any]],
    log_ctx: Dict[str, Any],
) -> Tuple[Optional[str], bool, FailoverChain, RouterOutput]:
    response: Optional[str] = None
    hit_limit = False
    max_attempts = max(1, int(settings.AGENT_EXECUTION_MAX_ATTEMPTS))
    run_timeout_ms = max(int(settings.AGENT_RUN_TIMEOUT_MS), 0)

    run_handle: Optional[RunHandle] = None
    try:
        run_handle = register_run(
            session.session_id,
            max_turns=30,
            timeout_ms=run_timeout_ms,
        )
    except ValueError:
        logger.warning(
            "Existing active run detected for session; attempting cleanup and re-register",
            extra=log_ctx,
        )
        try:
            complete_run(session.session_id)
        except Exception:
            pass
        try:
            run_handle = register_run(
                session.session_id,
                max_turns=30,
                timeout_ms=run_timeout_ms,
            )
        except Exception:
            run_handle = None

    failover = FailoverChain(
        preferred_provider=route_result.provider,
        preferred_model=route_result.model_name,
    )

    try:
        for attempt in range(max_attempts):
            if attempt > 0:
                logger.info(
                    "Retrying after turn-limit (attempt=%d/%d)",
                    attempt + 1,
                    max_attempts,
                    extra=log_extra(session_id=session.session_id, attempt=attempt + 1, event="run"),
                )
                current_prompt = (
                    f"{user_prompt}\n\n[SYSTEM: Your previous attempt used all execution turns. "
                    "Be more efficient: batch operations, use fewer tool calls, and prioritize the most important steps.]"
                )
            else:
                current_prompt = user_prompt

            try:
                response, hit_limit = await orchestrator._execute(
                    current_prompt,
                    images,
                    memory_context,
                    route_result,
                    session,
                    session_tool_map,
                    run_handle=run_handle,
                    failover=failover,
                    stream_emit=stream_emit,
                    source_channel=source_channel,
                    source_metadata=source_metadata,
                )

                if not hit_limit:
                    break
            except Exception as e:
                classified = classify_error(e, context="orchestrator._execute")
                strategy = get_recovery_plan(classified, attempt + 1)
                logger.warning(
                    "Execution error (attempt=%d): %s -> %s",
                    attempt + 1,
                    classified,
                    strategy.value,
                    extra=log_extra(session_id=session.session_id, attempt=attempt + 1, event="run"),
                )

                if strategy == RecoveryStrategy.ROTATE_MODEL and not failover.is_exhausted():
                    failover.advance(reason=str(e))
                    provider, model = failover.get_current()
                    route_result.provider = provider
                    route_result.model_name = model
                    logger.info(
                        "Failover selected %s/%s",
                        provider,
                        model,
                        extra=log_extra(session_id=session.session_id, attempt=attempt + 1, event="failover"),
                    )
                elif strategy == RecoveryStrategy.ABORT:
                    break

                response = None
                hit_limit = False
    finally:
        if run_handle:
            try:
                complete_run(session.session_id)
            except Exception:
                pass

    return response, hit_limit, failover, route_result

from typing import Any, Callable, Dict, List, Optional
import logging

from app.agents.context_manager import SUMMARY_INTERVAL
from app.agents.orchestrator_context import log_extra as _log_extra
from app.agents.orchestrator_types import AgentResponse
from app.agents.orchestrator_run_execution import execute_with_retries
from app.agents.orchestrator_run_memory_context import build_memory_context
from app.agents.orchestrator_run_session_context import (
    apply_profile_model_override,
    prepare_session_channel_context,
)
from app.core.guardian import guardian
from app.core.models import AgentSession
from app.core.user_profile import evaluate_and_update_user_preferences
from app.tools.context_tools import get_context_tools

logger = logging.getLogger(__name__)


async def run_orchestrator(
    *,
    orchestrator: Any,
    user_prompt: str,
    session: Optional[AgentSession],
    images: Optional[List[str]],
    model_override: Optional[str],
    stream_callback: Optional[Callable],
    source_channel: Optional[str],
    source_metadata: Optional[Dict[str, Any]],
) -> AgentResponse:
    if session is None:
        session = AgentSession(session_id="default")
    resolved_channel, request_channel_context = prepare_session_channel_context(
        session=session,
        source_channel=source_channel,
        source_metadata=source_metadata,
    )
    log_ctx = _log_extra(session_id=session.session_id, event="run")

    # Opportunistically learn durable user preferences from first-person phrasing.
    try:
        evaluate_and_update_user_preferences(user_prompt)
    except Exception as pref_err:
        logger.debug("Preference extraction skipped: %s", pref_err, extra=log_ctx)

    model_override = apply_profile_model_override(
        agent_profile=orchestrator.agent_profile,
        model_override=model_override,
    )

    # Dynamic Context Tools bound to this session
    session_context_tools = get_context_tools(session)
    session_tool_map = {t.name: t for t in session_context_tools}

    # Stream helper (no-op if no callback)
    async def _emit(event: str, data: Dict[str, Any] = {}):
        if stream_callback:
            try:
                await stream_callback(event, data)
            except Exception:
                pass  # Never let stream errors kill the pipeline

    await _emit("phase", {"phase": "evaluating", "message": "Evaluating prompt..."})
    logger.info(
        "Run start: evaluating prompt (prompt_len=%d, images=%d, channel=%s)",
        len(user_prompt or ""),
        len(images or []),
        resolved_channel,
        extra=log_ctx,
    )
    if images:
        logger.info("Attached images: %d", len(images), extra=log_ctx)

    eval_result = await orchestrator._evaluate_prompt(user_prompt)
    logger.info("Evaluator intent: %s", eval_result.intent, extra=log_ctx)
    await _emit("intent", {"intent": eval_result.intent})

    await _emit("phase", {"phase": "memory", "message": "Searching memories..."})
    memory_context, relationship_blocks, memories = await build_memory_context(
        orchestrator=orchestrator,
        user_prompt=user_prompt,
        eval_result=eval_result,
        session=session,
        request_channel_context=request_channel_context,
        log_ctx=log_ctx,
    )

    await _emit("phase", {"phase": "routing", "message": "Selecting tools & model..."})
    logger.info("Routing model/tool selection", extra=log_ctx)
    route_result = await orchestrator._route_request(
        user_prompt, memory_context, list(session_tool_map.keys())
    )

    # Apply override if present
    if model_override:
        logger.info("Applying model override: %s", model_override, extra=log_ctx)
        parts = model_override.split("/", 1)
        if len(parts) == 2:
            route_result.provider = parts[0]
            route_result.model_name = parts[1]
        else:
            route_result.provider = model_override
            route_result.model_name = None

    logger.info(
        "Routing decision model=%s/%s tools=%s",
        route_result.provider,
        route_result.model_name,
        route_result.selected_tools,
        extra=log_ctx,
    )

    await _emit(
        "phase",
        {
            "phase": "executing",
            "message": "Executing...",
            "model": f"{route_result.provider}/{route_result.model_name}",
            "tools": route_result.selected_tools,
        },
    )
    logger.info("Execution phase start", extra=log_ctx)

    if orchestrator._should_request_plan_approval(user_prompt, route_result, session):
        plan = await orchestrator._build_execution_plan(user_prompt, memory_context, route_result)
        if len(plan.steps) >= 2:
            action_id = guardian.create_plan_approval(
                session_id=session.session_id,
                goal=user_prompt,
                plan=plan.model_dump(),
            )
            await _emit(
                "phase",
                {
                    "phase": "approval",
                    "message": "Plan generated and waiting for approval.",
                    "action_id": action_id,
                },
            )
            plan_lines = [
                f"Execution plan requires approval (Action ID: {action_id}).",
                f"Plan: {plan.name}",
            ]
            for step in plan.steps:
                deps = ", ".join(step.depends_on) if step.depends_on else "none"
                mode = "parallel" if step.parallelizable else "dependent"
                plan_lines.append(
                    f"- [{step.id}] {step.title} | mode={mode} | depends_on={deps} | priority={step.priority}"
                )
            plan_lines.append("Approve via POST /api/v1/agent/approve/{action_id}.")
            return AgentResponse(
                response="\n".join(plan_lines),
                metadata={
                    "approval_required": True,
                    "action_id": action_id,
                    "plan": plan.model_dump(),
                    "model_used": f"{route_result.provider}/{route_result.model_name}",
                },
                session_data=session,
            )

    response, hit_limit, failover, route_result = await execute_with_retries(
        orchestrator=orchestrator,
        user_prompt=user_prompt,
        images=images,
        memory_context=memory_context,
        route_result=route_result,
        session=session,
        session_tool_map=session_tool_map,
        source_channel=resolved_channel,
        source_metadata=source_metadata,
        stream_emit=_emit,
        log_ctx=log_ctx,
    )

    if not response or not response.strip():
        response = (
            "I apologize, but I encountered an unexpected issue and could not generate a response. "
            "Please try again."
        )

    # Auto-summarize check: summarize when enough new messages accumulated.
    unsummarized_count = len(session.messages) - session.last_summary_index
    if unsummarized_count >= SUMMARY_INTERVAL:
        logger.info(
            "Auto-summarize triggered (%d unsummarized messages)",
            unsummarized_count,
            extra=log_ctx,
        )
        try:
            await orchestrator._summarize_to_short_term(session)
        except Exception as e:
            logger.warning("Auto-summarize failed (non-fatal): %s", e, extra=log_ctx)

    # Cleanup expired short-term memories.
    try:
        orchestrator.short_term_memory.cleanup_expired(session.session_id)
    except Exception:
        pass

    metadata = {
        "intent": eval_result.intent,
        "relationship_memory_used": len(relationship_blocks),
        "memory_used": len(memories),
        "model_used": f"{route_result.provider}/{route_result.model_name}",
        "tools_used": route_result.selected_tools,
        "failover_attempts": failover.attempts if failover.attempts else None,
        "source_channel": resolved_channel,
    }

    await _emit("complete", {"response": response, "metadata": metadata})
    logger.info("Run complete (metadata=%s)", metadata, extra=log_ctx)

    return AgentResponse(
        response=response,
        metadata=metadata,
        session_data=session,  # Return updated session
    )

from typing import Any, Callable, Dict, List, Optional, Tuple
import logging

from app.agents.failover import FailoverChain
from app.agents.orchestrator_context import log_extra as _log_extra
from app.agents.orchestrator_execution_model_bind import (
    resolve_executor_llm,
    select_tools_to_bind,
    bind_tools_with_fallback,
)
from app.agents.orchestrator_execution_prompt_context import (
    build_full_system_prompt,
    build_human_message,
    build_initial_messages,
)
from app.agents.orchestrator_execution_loop import run_turn_loop
from app.agents.orchestrator_types import RouterOutput
from app.agents.run_registry import RunHandle
from app.agents.session_manager import SessionManager
from app.core.config import settings
from app.core.llm import get_llm
from app.core.models import AgentSession

logger = logging.getLogger(__name__)


async def execute_with_tools(
    orchestrator,
    prompt: str,
    images: Optional[List[str]],
    memory: str,
    route: RouterOutput,
    session: AgentSession,
    session_tool_map: Dict[str, Any] = {},
    run_handle: Optional[RunHandle] = None,
    failover: Optional[FailoverChain] = None,
    stream_emit: Optional[Callable[..., Any]] = None,
    source_channel: str = "ui",
    source_metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[str, bool]:
    sm = SessionManager()
    exec_ctx = _log_extra(session_id=session.session_id, event="execute")
    # Execution model calls should fail fast enough for failover to kick in.
    llm_timeout_seconds = max(min(int(settings.AGENT_LLM_TIMEOUT_SECONDS), 30), 1)
    tool_timeout_seconds = max(int(settings.AGENT_TOOL_TIMEOUT_SECONDS), 1)
    tool_retry_attempts = max(int(settings.AGENT_TOOL_RETRY_ATTEMPTS), 1)

    # Combine static tools and dynamic session tools
    full_tool_map = {**orchestrator.tool_map, **session_tool_map}

    # 1. Resolve model and bind tools
    try:
        executor_llm = resolve_executor_llm(route, failover)
    except Exception:
        executor_llm = get_llm()
    tools_to_bind = select_tools_to_bind(
        full_tool_map=full_tool_map,
        route=route,
        session_tool_map=session_tool_map,
    )
    llm_with_tools = bind_tools_with_fallback(executor_llm, tools_to_bind)

    # 2. Build prompt/context/messages
    full_system_prompt = await build_full_system_prompt(
        orchestrator=orchestrator,
        memory=memory,
        source_channel=source_channel,
        source_metadata=source_metadata,
    )
    
    messages = build_initial_messages(
        orchestrator=orchestrator,
        session_manager=sm,
        session=session,
        prompt=prompt,
        full_system_prompt=full_system_prompt,
    )
    
    # Append current user prompt to the optimized list
    human_msg = build_human_message(prompt=prompt, images=images, exec_ctx=exec_ctx)
        
    messages.append(human_msg)
    
    final_answer, hit_turn_limit = await run_turn_loop(
        orchestrator=orchestrator,
        session=session,
        run_handle=run_handle,
        failover=failover,
        route=route,
        messages=messages,
        human_msg=human_msg,
        full_tool_map=full_tool_map,
        tool_timeout_seconds=tool_timeout_seconds,
        tool_retry_attempts=tool_retry_attempts,
        llm_timeout_seconds=llm_timeout_seconds,
        stream_emit=stream_emit,
        full_system_prompt=full_system_prompt,
        tools_to_bind=tools_to_bind,
        executor_llm=executor_llm,
        llm_with_tools=llm_with_tools,
        exec_ctx=exec_ctx,
        session_manager=sm,
    )
    return final_answer, hit_turn_limit


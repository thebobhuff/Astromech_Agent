from typing import List, Dict, Any, Optional, Tuple, Callable
from app.core.llm import get_llm
from app.memory.rag import get_vector_memory
from app.core.models import AgentSession, AgentProfile
from app.agents.context_manager import ContextManager
from app.memory.short_term import ShortTermMemoryManager
from app.memory.relationship_memory import RelationshipMemoryStore
from app.agents.run_registry import RunHandle
from app.agents.failover import FailoverChain
from app.agents.orchestrator_types import (
    EvaluatorOutput,
    RouterOutput,
    ExecutionPlan,
    AgentResponse,
)
from app.agents.orchestrator_planning import (
    should_request_plan_approval,
    build_execution_plan,
    evaluate_prompt,
    route_request,
)
from app.agents.orchestrator_memory import summarize_to_short_term
from app.agents.orchestrator_execution import execute_with_tools
from app.agents.orchestrator_run import run_orchestrator

# --- Orchestrator ---

def _lazy_load_all_tools() -> list:
    """Import and collect tools only when first needed — avoids loading
    playwright, google-generativeai, etc. at process startup."""
    from app.tools.local_system import get_local_tools
    from app.tools.task_tools import get_task_tools
    from app.tools.web_search import get_web_tools
    from app.tools.browser import get_browser_tools
    from app.tools.skill_tools import get_skill_tools
    from app.tools.api_tools import get_api_tools
    from app.tools.agent_tools import get_agent_tools
    from app.tools.media_tools import get_media_tools
    from app.tools.code_tools import get_code_tools
    from app.tools.self_modify_tools import get_self_modify_tools
    from app.tools.memory_tools import get_memory_tools
    from app.tools.github_tools import get_github_tools
    from app.tools.image_tools import get_image_tools
    return (
        get_local_tools() + get_task_tools() + get_web_tools()
        + get_browser_tools() + get_skill_tools() + get_api_tools()
        + get_agent_tools() + get_media_tools() + get_code_tools()
        + get_self_modify_tools() + get_memory_tools() + get_github_tools()
        + get_image_tools()
    )


class AgentOrchestrator:
    # ── Class-level cache so tools are loaded once across all instances ──
    _cached_tools: Optional[list] = None

    def __init__(self, context_manager: Optional[ContextManager] = None, agent_profile: Optional[AgentProfile] = None):
        # Use process-wide singleton for VectorMemory (avoids duplicate embedding models)
        self.memory = get_vector_memory()
        self.short_term_memory = ShortTermMemoryManager()
        self.relationship_memory = RelationshipMemoryStore()
        self.agent_profile = agent_profile

        # Lazy-load tools once, then reuse across all orchestrator instances
        if AgentOrchestrator._cached_tools is None:
            AgentOrchestrator._cached_tools = _lazy_load_all_tools()
        base_tools = AgentOrchestrator._cached_tools

        if self.agent_profile and "all" not in self.agent_profile.allowed_tools:
            self.available_tools = [t for t in base_tools if t.name in self.agent_profile.allowed_tools]
        else:
            self.available_tools = list(base_tools)

        self.tool_map = {t.name: t for t in self.available_tools}
        self.context_manager = context_manager or ContextManager()
        # Keep evaluator/router on a fast, stable model so chat does not stall
        # when the default execution model is slow or unavailable.
        try:
            self.meta_llm = get_llm(provider="gemini", model_name="gemini-2.0-flash")
        except Exception:
            self.meta_llm = get_llm()  # Fallback to default model config

    async def run(
        self,
        user_prompt: str,
        session: Optional[AgentSession] = None,
        images: Optional[List[str]] = None,
        model_override: Optional[str] = None,
        stream_callback: Optional[Callable] = None,
        source_channel: Optional[str] = None,
        source_metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        return await run_orchestrator(
            orchestrator=self,
            user_prompt=user_prompt,
            session=session,
            images=images,
            model_override=model_override,
            stream_callback=stream_callback,
            source_channel=source_channel,
            source_metadata=source_metadata,
        )

    def _should_request_plan_approval(
        self,
        user_prompt: str,
        route_result: RouterOutput,
        session: AgentSession,
    ) -> bool:
        return should_request_plan_approval(
            user_prompt=user_prompt,
            route_result=route_result,
            session=session,
        )

    async def _build_execution_plan(
        self,
        user_prompt: str,
        memory_context: str,
        route_result: RouterOutput,
    ) -> ExecutionPlan:
        return await build_execution_plan(
            meta_llm=self.meta_llm,
            user_prompt=user_prompt,
            memory_context=memory_context,
            route_result=route_result,
        )

    async def _evaluate_prompt(self, prompt: str) -> EvaluatorOutput:
        return await evaluate_prompt(meta_llm=self.meta_llm, prompt=prompt)

    async def _route_request(self, prompt: str, memory_context: str, extra_tool_names: List[str] = []) -> RouterOutput:
        return await route_request(
            meta_llm=self.meta_llm,
            tool_map=self.tool_map,
            prompt=prompt,
            memory_context=memory_context,
            extra_tool_names=extra_tool_names,
        )

    async def _execute(
        self,
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
        return await execute_with_tools(
            orchestrator=self,
            prompt=prompt,
            images=images,
            memory=memory,
            route=route,
            session=session,
            session_tool_map=session_tool_map,
            run_handle=run_handle,
            failover=failover,
            stream_emit=stream_emit,
            source_channel=source_channel,
            source_metadata=source_metadata,
        )

    async def _summarize_to_short_term(self, session: AgentSession):
        await summarize_to_short_term(orchestrator=self, session=session)

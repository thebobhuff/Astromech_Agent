import asyncio
from typing import Any, List

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.core.models import AgentSession
from app.core.models_config import load_models_config
from app.core.config import settings
from app.agents.orchestrator_types import (
    EvaluatorOutput,
    ExecutionPlan,
    PlanStep,
    RouterOutput,
)


async def _invoke_with_timeout(chain: Any, payload: dict) -> Any:
    # Meta calls (evaluate/route/plan) should fail fast to keep streaming responsive.
    timeout_seconds = max(5, min(int(settings.AGENT_LLM_TIMEOUT_SECONDS), 20))
    return await asyncio.wait_for(chain.ainvoke(payload), timeout=timeout_seconds)


def should_request_plan_approval(
    user_prompt: str,
    route_result: RouterOutput,
    session: AgentSession,
) -> bool:
    if not settings.AGENT_REQUIRE_PLAN_APPROVAL:
        return False
    if session.session_id.startswith("task_") or session.session_id.startswith("sub-"):
        return False
    if session.session_id == "heartbeat_session":
        return False
    if "Background Task Execution:" in user_prompt:
        return False
    if not route_result.selected_tools:
        return False
    lowered = user_prompt.lower()
    planning_cues = (
        "plan",
        "roadmap",
        "break",
        "phases",
        "long-running",
        "long running",
        "step by step",
        "multi-step",
        "project",
    )
    return any(cue in lowered for cue in planning_cues)


async def build_execution_plan(
    *,
    meta_llm: Any,
    user_prompt: str,
    memory_context: str,
    route_result: RouterOutput,
) -> ExecutionPlan:
    parser = JsonOutputParser(pydantic_object=ExecutionPlan)
    available_tools = ", ".join(sorted(route_result.selected_tools))
    system_prompt = """You are a planning specialist.
Build an execution plan for a long-running agent workflow.
Requirements:
1. Return 2-8 concrete steps.
2. Each step must include id, title, description, depends_on, parallelizable, priority.
3. Use depends_on to model strict ordering.
4. Mark parallelizable=true only when no strict dependency blocks it.
5. Keep priority between 1 and 5.
6. Ensure dependencies only reference existing step IDs.
Return valid JSON only."""
    chain = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        (
            "user",
            "GOAL:\n{goal}\n\nMEMORY CONTEXT:\n{memory}\n\nROUTER TOOLS:\n{tools}\n\n{format_instructions}",
        ),
    ]) | meta_llm | parser
    try:
        result = await _invoke_with_timeout(
            chain,
            {
                "goal": user_prompt,
                "memory": memory_context or "(none)",
                "tools": available_tools or "(none)",
                "format_instructions": parser.get_format_instructions(),
            },
        )
        plan = ExecutionPlan(**result) if isinstance(result, dict) else result
    except Exception:
        plan = ExecutionPlan(
            name="Fallback Plan",
            goal=user_prompt,
            steps=[
                PlanStep(
                    id="s1",
                    title="Execute requested task",
                    description=user_prompt,
                    depends_on=[],
                    parallelizable=False,
                    priority=3,
                )
            ],
        )

    known_ids = {s.id for s in plan.steps}
    normalized_steps: List[PlanStep] = []
    for idx, step in enumerate(plan.steps, start=1):
        sid = step.id.strip() or f"s{idx}"
        deps = [d for d in step.depends_on if d in known_ids and d != sid]
        normalized_steps.append(
            PlanStep(
                id=sid,
                title=step.title.strip() or f"Step {idx}",
                description=step.description.strip() or step.title.strip() or f"Step {idx}",
                depends_on=deps,
                parallelizable=bool(step.parallelizable and not deps),
                priority=min(max(int(step.priority), 1), 5),
            )
        )
    plan.steps = normalized_steps
    return plan


async def evaluate_prompt(*, meta_llm: Any, prompt: str) -> EvaluatorOutput:
    parser = JsonOutputParser(pydantic_object=EvaluatorOutput)

    system_prompt = """You are the 'Evaluator' of an AI agent.
Analyze the user's prompt to understand their intent and what memory context is needed.
Output JSON with:
- intent: Short summary.
- memory_queries: List of 1-3 search queries for the vector DB.
"""
    chain = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "{prompt}\n\n{format_instructions}")
    ]) | meta_llm | parser

    try:
        result = await _invoke_with_timeout(
            chain,
            {
                "prompt": prompt,
                "format_instructions": parser.get_format_instructions(),
            },
        )
        if isinstance(result, dict):
            return EvaluatorOutput(**result)
        return result
    except Exception:
        return EvaluatorOutput(intent="General query", memory_queries=[prompt])


async def route_request(
    *,
    meta_llm: Any,
    tool_map: dict,
    prompt: str,
    memory_context: str,
    extra_tool_names: List[str],
) -> RouterOutput:
    parser = JsonOutputParser(pydantic_object=RouterOutput)
    tool_names = ", ".join(list(tool_map.keys()) + extra_tool_names)

    models_cfg = load_models_config()
    active_models_str = ", ".join([
        f"{m.provider}/{m.model_id} (alias: {m.name})"
        for m in models_cfg.active_models
        if m.is_active
    ])

    default_model = models_cfg.get_model("default")
    smart_model = models_cfg.get_model("smart")

    default_ex = default_model.model_id if default_model else "configured default"
    smart_ex = smart_model.model_id if smart_model else "configured smart model"

    system_prompt = f"""You are the 'Router' of an AI agent.
Based on the USER PROMPT and MEMORY CONTEXT, decide:
1. Which TOOLS are needed from this list: [{tool_names}]. If none, return empty list.
2. Which LLM PROVIDER/MODEL to use for execution.
   Available Configured Models: [{active_models_str}]

   - Use alias 'default' (e.g. {default_ex}) for simple, fast tasks.
   - Use alias 'smart' (e.g. {smart_ex}) for reasoning-heavy or coding tasks.
   - Use 'ollama/llama3' only if privacy is explicitly requested.

Format as JSON."""

    chain = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "MEMORY:\n{memory}\n\nUSER PROMPT: {prompt}\n\n{format_instructions}")
    ]) | meta_llm | parser

    try:
        result = await _invoke_with_timeout(
            chain,
            {
                "prompt": prompt,
                "memory": memory_context,
                "format_instructions": parser.get_format_instructions(),
            },
        )
        if isinstance(result, dict):
            return RouterOutput(**result)
        return result
    except Exception:
        return RouterOutput(
            selected_tools=[],
            provider="gemini",
            model_name="default",
            reasoning="Fallback due to router failure.",
        )

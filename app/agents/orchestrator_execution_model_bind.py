from typing import Any, Dict, List, Optional
import logging

from app.agents.failover import FailoverChain
from app.agents.orchestrator_types import RouterOutput
from app.core.config import settings
from app.core.llm import get_llm

logger = logging.getLogger(__name__)

CORE_TOOLS = {
    "web_search",
    "read_local_file",
    "write_local_file",
    "replace_text_in_file",
    "terminal",
    "run_python_code",
    "save_memory",
    "visit_webpage",
}


def resolve_executor_llm(route: RouterOutput, failover: Optional[FailoverChain]) -> Any:
    """Try failover chain first, then route-based resolution."""
    if failover and not failover.is_exhausted():
        try:
            return failover.get_llm()
        except Exception as e:
            logger.warning("Failover chain get_llm failed: %s", e)

    model_name = route.model_name
    if model_name:
        if "/" in model_name and not model_name.startswith("models/"):
            parts = model_name.split("/")
            if len(parts) == 2:
                model_name = parts[1]
        if "default" in model_name.lower():
            model_name = None

    provider = route.provider
    if provider:
        provider = provider.lower()
        if provider == "google":
            provider = "gemini"
        if "default" in provider:
            provider = None

    if provider == "ollama" and settings.DEFAULT_LLM_PROVIDER != "ollama":
        return get_llm()
    return get_llm(provider, model_name)


def select_tools_to_bind(
    *,
    full_tool_map: Dict[str, Any],
    route: RouterOutput,
    session_tool_map: Dict[str, Any],
) -> List[Any]:
    all_tools = list(full_tool_map.values())
    if route.selected_tools:
        selected_names = set(route.selected_tools) | CORE_TOOLS
        tools_to_bind = [t for t in all_tools if t.name in selected_names]
        if len(tools_to_bind) < 3:
            tools_to_bind = all_tools
        return tools_to_bind

    session_tools = list(session_tool_map.keys()) if session_tool_map else []
    selected_names = CORE_TOOLS | set(session_tools)
    tools_to_bind = [t for t in all_tools if t.name in selected_names]
    if len(tools_to_bind) < 3:
        tools_to_bind = all_tools
    return tools_to_bind


def bind_tools_with_fallback(executor_llm: Any, tools_to_bind: List[Any]) -> Any:
    if not tools_to_bind:
        return executor_llm

    try:
        llm_with_tools = executor_llm.bind_tools(tools_to_bind)
        logger.info("Bound %d tools to executor LLM", len(tools_to_bind))
        return llm_with_tools
    except Exception as bind_err:
        logger.error("bind_tools FAILED with %d tools: %s", len(tools_to_bind), bind_err)
        emergency_tools = [
            t
            for t in tools_to_bind
            if t.name in {"read_local_file", "write_local_file", "replace_text_in_file", "terminal"}
        ]
        if emergency_tools:
            try:
                llm_with_tools = executor_llm.bind_tools(emergency_tools)
                logger.info("Bound emergency tool set (%d tools)", len(emergency_tools))
                return llm_with_tools
            except Exception as emergency_err:
                logger.error("Emergency bind_tools FAILED: %s - LLM will have NO tools", emergency_err)
        return executor_llm

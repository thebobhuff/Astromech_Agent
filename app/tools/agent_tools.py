from langchain_core.tools import tool
from typing import Optional, List
import asyncio

from app.agents.registry import get_agent_registry
from app.core.models import AgentSession, AgentProfile
# Avoid module-level import of AgentOrchestrator to prevent circular dependency
# from app.agents.orchestrator import AgentOrchestrator

@tool
def create_subagent(
    id: str, 
    name: str, 
    description: str,
    system_prompt: str,
    allowed_tools: List[str] = ["read_file", "google_search"],
    provider: Optional[str] = "gemini",
    model: Optional[str] = "gemini-1.5-flash"
) -> str:
    """
    Creates and registers a new specialized sub-agent for a specific task.
    
    Args:
        id: Unique identifier (snake_case, e.g., 'data_analyst').
        name: Display name (e.g., 'Data Analyst').
        description: Brief description of the agent's purpose.
        system_prompt: Detailed instructions for the agent.
        allowed_tools: List of tool names the agent is allowed to use.
        provider: The LLM provider to use (e.g., 'gemini', 'ollama').
        model: The specific model ID (e.g., 'gemini-1.5-flash').
    """
    registry = get_agent_registry()
    
    try:
        profile = AgentProfile(
            id=id,
            name=name,
            description=description,
            system_prompt=system_prompt,
            allowed_tools=allowed_tools,
            provider=provider,
            model=model
        )
        registry.register_agent(profile)
        return f"✅ Sub-agent '{name}' ({id}) created successfully.\nProvider: {provider}\nModel: {model}\nTools: {', '.join(allowed_tools)}"
    except Exception as e:
        return f"❌ Failed to create sub-agent: {str(e)}"

@tool
def list_available_agents() -> str:
    """Lists all available specialized agents that tasks can be delegated to."""
    registry = get_agent_registry()
    agents = registry.list_agents()
    
    output = "Available Agents:\n"
    for agent in agents:
        output += f"- ID: {agent.id}\n  Name: {agent.name}\n  Description: {agent.description}\n  Model: {agent.provider}/{agent.model}\n"
    return output

@tool
async def delegate_task(agent_id: str, task_description: str) -> str:
    """
    Delegates a specific task to a sub-agent.
    
    Args:
        agent_id: The ID of the agent to use (use list_available_agents to find IDs).
        task_description: A clear, self-contained description of what the sub-agent should do.
    """
    registry = get_agent_registry()
    profile = registry.get_agent(agent_id)
    
    if not profile:
        return f"Error: Agent with ID '{agent_id}' not found. Use list_available_agents to see valid options."
    
    # Deferred import to avoid circular dependency
    from app.agents.orchestrator import AgentOrchestrator
    
    print(f"\n>>> Spawning Sub-Agent: {profile.name} ({agent_id}) <<<")
    print(f"Task: {task_description[:100]}...")
    
    # Create a fresh session for the sub-agent
    session = AgentSession(
        session_id=f"sub-{agent_id}-{asyncio.get_event_loop().time()}"
    )
    
    # Instantiate orchestrator with specific profile
    orchestrator = AgentOrchestrator(agent_profile=profile)
    
    try:
        result = await orchestrator.run(
            task_description,
            session,
            source_channel="subagent",
            source_metadata={"transport": "delegate_task"},
        )
        print(f">>> Sub-Agent {profile.name} Finished <<<")
        return f"Sub-Agent {profile.name} Report:\n{result.response}"
    except Exception as e:
        print(f"Sub-Agent Error: {e}")
        return f"Error executing task with agent {agent_id}: {str(e)}"

def get_agent_tools():
    return [list_available_agents, delegate_task, create_subagent]

# Plan: Sub-Agents and Teams Implementation

## Objective
Implement a multi-agent system where the core `Astromech` agent can spawn sub-agents, delegate tasks to them, and manage teams of specialized agents. This is inspired by `openclaw`'s agent configuration and sandboxing model.

## Analysis of OpenClaw Model
- **Configuration**: Agents are defined in config files (`agents.list[]`) with specific:
  - `id`: Unique identifier (e.g., "coder", "researcher").
  - `sandbox`: Security boundaries (Docker, tool restrictions).
  - `tools`: Allow/deny lists for tools.
- **Routing**: Messages are routed to agents based on rules/bindings.
- **Isolation**: Agents have their own workspaces and auth stores.

## Implementation Plan for Astromech

### 1. Data Model: Agent Profiles
We will introduce `AgentProfile` to define the capabilities and identity of an agent.

**Location**: `app/core/models.py`
```python
class AgentProfile(BaseModel):
    id: str                 # e.g., "researcher"
    name: str               # e.g., "Deep Research Bot"
    description: str        # For the Router/Main agent to know when to use this
    system_prompt: str      # Specialized instructions
    allowed_tools: List[str]# Restrict usage (e.g., "read_file" only) - "all" for everything
    parent_id: Optional[str] = None
```

### 2. Configuration: Agent Registry
Create a registry to load agent definitions from JSON/YAML.

**Location**: `app/agents/registry.py`
- Load `data/agents.json` (New file).
- methods: `get_agent(id)`, `list_agents()`.

**New File**: `data/agents.json`
```json
[
  {
    "id": "researcher",
    "name": "Researcher",
    "description": "Expert at searching the web and summarizing documentation.",
    "tools": ["google_search", "read_file", "summarize"]
  },
  {
    "id": "coder",
    "name": "Senior Engineer",
    "description": "Expert Python/JS developer.",
    "tools": ["all"]
  }
]
```

### 3. Tooling: Delegation
The core agent needs a tool to "spawn" or "call" these sub-agents.

**Location**: `app/tools/agent_tools.py` (New File)
- **Tool**: `delegate_task(agent_id: str, task: str)`
  - **Logic**:
    1. Look up `agent_id` in registry.
    2. Instantiate a *new*, ephemeral `AgentOrchestrator`.
    3. Configure it with the sub-agent's system prompt and tool whitelist.
    4. Run the sub-agent with the `task`.
    5. Return the sub-agent's final answer to the main agent.

### 4. Orchestrator Refactor
The `AgentOrchestrator` currently assumes it is "The One".

**Refactor**: `app/agents/orchestrator.py`
- Allow `__init__` to accept an `AgentProfile`.
- If a profile is provided:
  - Override `identity` (System Prompt).
  - Filter `self.available_tools` based on `profile.allowed_tools`.

### 5. CLI Updates
Allow users to interact with specific agents directly or list them.

**Refactor**: `cli.py`
- Add support for `python cli.py --agent researcher`.
- Add command `/agents` inside the REPL to list available sub-agents.

### 6. Sandbox (Future/Advanced)
To match `openclaw`'s security:
- When a sub-agent is spawned, we could optionally enforce a read-only file system or specific working directory rooted in `data/workspaces/{agent_id}`.
- For now, we will implement logical separation via Tool Filtering.

## Execution Steps

1.  **Create Models**: Add `AgentProfile` to `app/core/models.py`.
2.  **Create Registry**: Implement `app/agents/registry.py` and `data/agents.json`.
3.  **Refactor Orchestrator**: Update `AgentOrchestrator` to accept `profile` argument.
4.  **Implement Tool**: Create `app/tools/agent_tools.py` with `delegate_task`.
5.  **Expose Tool**: Register `agent_tools` in `orchestrator.py` (available strictly to the *root* agent or manager agents).
6.  **Verify**: Test by having the main agent delegate a query to the "researcher" agent.

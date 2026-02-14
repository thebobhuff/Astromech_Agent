# Guardrails & Safety Protocol Implementation Plan

## Objective
Implement a safety layer to prevent autonomous agents from executing destructive commands (deletes, drops, system modification) without explicit human approval.

## Core Components

### 1. The Guardian (`app/core/guardian.py`)
A centralized security controller that intercepts tool calls before execution.

- **Responsibilities**:
  - Maintain a registry of "Restricted Tools".
  - Inspect tool calls (Name + Arguments).
  - Enforce policies (Block, Allow, Require Approval).
  - Manage "Pending Approvals" state.

### 2. Orchestrator Integration
Middleware within the `AgentOrchestrator` loop to consult the Guardian.

- **Workflow**:
  1. LLM selects Tool T.
  2. Orchestrator asks Guardian: `can_execute(T, args)?`
  3. **If Safe**: Execute T.
  4. **If Unsafe**:
     - Guardian generates `action_id`.
     - Tool execution is **SKIPPED**.
     - Fake Tool Output returned: `[Review Required] Action blocked. ID: <action_id>. User must approve.`
  5. LLM informs User: "I need approval for..."

### 3. Approval API
Endpoints for the user/frontend to grant permissions.

- `POST /api/agent/approve_action/{action_id}`
  - Validates ID.
  - Marks action as "Approved" (one-time use or time-window).

### 4. Implementation Details

#### Restricted Tools List (Initial)
- `delete_file` (File System)
- `os_command` (Shell - specific dangerous cmds)
- `execute_sql` (if contains DROP/TRUNCATE)
- `python_repl` (Potential for dangerous code)

#### Data Structures

```python
class PendingAction(BaseModel):
    id: str
    tool_name: str
    tool_args: dict
    status: str = "pending" # pending, approved, rejected
    created_at: datetime
```

## User Experience

1. **Trigger**: User asks "Delete all logs."
2. **Agent**: Calls `delete_file("logs/")`.
3. **Guardian**: Intercepts. Returns "Action requires approval (ID: act_552)."
4. **Agent Response**: "I've prepared the standard cleanup, but I need your approval to delete the 'logs/' directory. (Action ID: act_552)"
5. **User**: Clicks "Approve" on UI (or says "Approve act_552").
6. **System**:
   - UI calls API to approve.
   - User prompt "Retry" or "Go ahead" signals Agent to try again.
   - Agent retries `delete_file`.
   - Guardian sees `act_552` matches approved signature -> **ALLOW**.

## Future work
- Role-based Access Control (RBAC).
- Auto-approval for specific sub-agents (e.g., "CleanupBot" has delete perms).
- Visual "Pending Actions" queue in Frontend.

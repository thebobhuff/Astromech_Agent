from typing import Dict, Any, Optional, List, Set, Tuple
import uuid
import logging
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ActionState(BaseModel):
    id: str
    action_type: str = "tool_call"  # tool_call, plan_approval
    tool_name: str
    tool_args: Dict[str, Any]
    status: str = "pending"  # pending, approved, rejected, consumed
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None


class SecurityPolicy:
    """Defines which tools are restricted."""

    REPO_ROOT = Path(__file__).resolve().parents[2]
    SENSITIVE_SELF_MODIFY_PREFIXES: Set[str] = {
        "app/core",
        "app/agents",
    }

    # Tools that always require approval
    RESTRICTED_TOOLS: Set[str] = {
        "delete_file",
        "move_file",   # Can be destructive if overwriting
        "format_disk",  # Hypothetical
        "install_python_package",  # System modification
        "run_shell_command",      # High risk
    }

    # Key-phrases in arguments that trigger restriction for generic tools (e.g. SQL)
    DANGEROUS_KEYWORDS: List[str] = [
        "DROP TABLE", "DELETE FROM", "TRUNCATE", "rm -rf", "format c:"
    ]

    @classmethod
    def is_restricted(cls, tool_name: str, args: Dict[str, Any]) -> bool:
        if tool_name in cls.RESTRICTED_TOOLS:
            return True

        # Guard self-editing for critical runtime code paths.
        if tool_name == "self_modify_code":
            path_arg = str(args.get("path", "")).strip()
            if not path_arg:
                return True
            try:
                candidate = Path(path_arg)
                if not candidate.is_absolute():
                    candidate = cls.REPO_ROOT / candidate
                resolved = candidate.resolve()
                if resolved != cls.REPO_ROOT and cls.REPO_ROOT not in resolved.parents:
                    return True
                relative = resolved.relative_to(cls.REPO_ROOT).as_posix().lower()
                for prefix in cls.SENSITIVE_SELF_MODIFY_PREFIXES:
                    p = prefix.lower()
                    if relative == p or relative.startswith(f"{p}/"):
                        return True
            except Exception:
                return True

        # Heuristic check for generic executors
        if tool_name in ["run_python_code", "python_repl"]:
            code = args.get("code", "") or args.get("script", "")
            if "os.remove" in code or "shutil.rmtree" in code:
                return True

        return False


class GuardianObject:
    """Singleton-patterned guardian instance."""

    def __init__(self):
        self.pending_actions: Dict[str, ActionState] = {}
        # Map (tool_name, frozenset(args_items)) -> action_id for quick lookup of pre-approvals
        self._approval_cache: Dict[str, str] = {}

    def validate_tool_call(self, tool_name: str, tool_args: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """
        Check if a tool call is allowed.
        Returns: (is_allowed, reason_message, action_id)
        """
        # 1. Check Policy
        if not SecurityPolicy.is_restricted(tool_name, tool_args):
            return True, "Safe", None

        # 2. Check for existing Approval
        # We try to match exactly the signature.
        signature_key = self._get_signature(tool_name, tool_args)

        # Check if we have a pending action that is APPROVED
        for action_id, state in self.pending_actions.items():
            if state.status == "approved":
                check_sig = self._get_signature(state.tool_name, state.tool_args)
                if check_sig == signature_key:
                    # Consumed!
                    state.status = "consumed"
                    return True, "Approved by user", action_id

        # 3. Create Pending Action
        action_id = f"act_{uuid.uuid4().hex[:8]}"
        state = ActionState(
            id=action_id,
            action_type="tool_call",
            tool_name=tool_name,
            tool_args=tool_args,
            status="pending"
        )
        self.pending_actions[action_id] = state

        logger.warning(f"Guardian intercepted destructive action: {tool_name} -> ID {action_id}")

        return False, "Destructive action intercepted. User approval required.", action_id

    def create_plan_approval(
        self,
        *,
        session_id: str,
        goal: str,
        plan: Dict[str, Any],
    ) -> str:
        """Create a pending plan-approval action and return its action ID."""
        action_id = f"plan_{uuid.uuid4().hex[:8]}"
        state = ActionState(
            id=action_id,
            action_type="plan_approval",
            tool_name="execute_plan",
            tool_args={
                "session_id": session_id,
                "goal": goal,
                "plan": plan,
            },
            status="pending",
        )
        self.pending_actions[action_id] = state
        logger.info("Guardian created plan approval request: %s", action_id)
        return action_id

    def approve_action(self, action_id: str) -> bool:
        """User approves an action."""
        if action_id in self.pending_actions:
            self.pending_actions[action_id].status = "approved"
            return True
        return False

    def reject_action(self, action_id: str) -> bool:
        if action_id in self.pending_actions:
            self.pending_actions[action_id].status = "rejected"
            return True
        return False

    def get_action(self, action_id: str) -> Optional[ActionState]:
        return self.pending_actions.get(action_id)

    def consume_action(self, action_id: str) -> bool:
        action = self.pending_actions.get(action_id)
        if not action:
            return False
        action.status = "consumed"
        return True

    def list_pending_actions(self, action_type: Optional[str] = None) -> List[ActionState]:
        actions = [a for a in self.pending_actions.values() if a.status == "pending"]
        if action_type:
            actions = [a for a in actions if a.action_type == action_type]
        return actions

    def _get_signature(self, name: str, args: Dict) -> str:
        # Simple serialization for comparison
        # Note: robust implementation would handle arg types better
        return f"{name}:{str(sorted(args.items()))}"


# Global instance
guardian = GuardianObject()

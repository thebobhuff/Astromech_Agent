from __future__ import annotations

import platform
import subprocess
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from app.core.config import settings


class NodeDescriptor(BaseModel):
    node_id: str
    name: str
    platform: str
    capabilities: List[str] = Field(default_factory=list)


class NodeInvokeResult(BaseModel):
    ok: bool
    action: str
    node_id: str
    message: str = ""
    output: str = ""
    error: str = ""
    exit_code: int | None = None


class LocalNodeRuntime:
    """Minimal local node runtime for device-style actions."""

    NODE_ID = "local-host-node"

    def list_nodes(self) -> List[NodeDescriptor]:
        capabilities = ["system.notify"]
        if settings.NODE_RUNTIME_ALLOW_SYSTEM_RUN:
            capabilities.append("system.run")
        return [
            NodeDescriptor(
                node_id=self.NODE_ID,
                name=settings.NODE_RUNTIME_NAME,
                platform=platform.platform(),
                capabilities=capabilities,
            )
        ]

    def invoke(self, node_id: str, action: str, args: Dict[str, Any] | None = None) -> NodeInvokeResult:
        if not settings.NODE_RUNTIME_ENABLED:
            return NodeInvokeResult(
                ok=False,
                action=action,
                node_id=node_id,
                error="Node runtime is disabled. Set NODE_RUNTIME_ENABLED=true.",
            )
        if node_id != self.NODE_ID:
            return NodeInvokeResult(
                ok=False,
                action=action,
                node_id=node_id,
                error=f"Unknown node_id '{node_id}'.",
            )

        payload = args or {}
        if action == "system.run":
            return self._run_command(node_id=node_id, action=action, args=payload)
        if action == "system.notify":
            return self._send_notification(node_id=node_id, action=action, args=payload)

        return NodeInvokeResult(
            ok=False,
            action=action,
            node_id=node_id,
            error=f"Unsupported action '{action}'.",
        )

    def _run_command(self, node_id: str, action: str, args: Dict[str, Any]) -> NodeInvokeResult:
        if not settings.NODE_RUNTIME_ALLOW_SYSTEM_RUN:
            return NodeInvokeResult(
                ok=False,
                action=action,
                node_id=node_id,
                error=(
                    "system.run is disabled. Set NODE_RUNTIME_ALLOW_SYSTEM_RUN=true "
                    "to enable command execution."
                ),
            )

        command = str(args.get("command", "")).strip()
        if not command:
            return NodeInvokeResult(
                ok=False,
                action=action,
                node_id=node_id,
                error="Missing required argument: command",
            )

        timeout_seconds = int(args.get("timeout_seconds", 30) or 30)
        timeout_seconds = max(1, min(timeout_seconds, 120))

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
            )
            output = (result.stdout or "").strip()
            error = (result.stderr or "").strip()
            return NodeInvokeResult(
                ok=result.returncode == 0,
                action=action,
                node_id=node_id,
                output=output,
                error=error,
                exit_code=result.returncode,
                message="Command executed.",
            )
        except Exception as exc:
            return NodeInvokeResult(
                ok=False,
                action=action,
                node_id=node_id,
                error=str(exc),
                message="Command execution failed.",
            )

    def _send_notification(self, node_id: str, action: str, args: Dict[str, Any]) -> NodeInvokeResult:
        title = str(args.get("title", "Astromech")).strip() or "Astromech"
        message = str(args.get("message", "")).strip()
        if not message:
            return NodeInvokeResult(
                ok=False,
                action=action,
                node_id=node_id,
                error="Missing required argument: message",
            )

        system_name = platform.system().lower()
        try:
            if "darwin" in system_name:
                script = f'display notification "{message}" with title "{title}"'
                subprocess.run(["osascript", "-e", script], check=True, capture_output=True, text=True)
                return NodeInvokeResult(ok=True, action=action, node_id=node_id, message="Notification sent.")

            if "windows" in system_name:
                # Fallback: use msg.exe when available (session-dependent).
                proc = subprocess.run(
                    ["msg", "*", f"{title}: {message}"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                if proc.returncode == 0:
                    return NodeInvokeResult(ok=True, action=action, node_id=node_id, message="Notification sent.")
                return NodeInvokeResult(
                    ok=False,
                    action=action,
                    node_id=node_id,
                    error=(proc.stderr or proc.stdout or "").strip(),
                    exit_code=proc.returncode,
                    message="Notification command failed on Windows host.",
                )

            # Linux and similar platforms.
            proc = subprocess.run(
                ["notify-send", title, message],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if proc.returncode == 0:
                return NodeInvokeResult(ok=True, action=action, node_id=node_id, message="Notification sent.")
            return NodeInvokeResult(
                ok=False,
                action=action,
                node_id=node_id,
                error=(proc.stderr or proc.stdout or "").strip(),
                exit_code=proc.returncode,
                message="Notification command failed on Linux host.",
            )
        except Exception as exc:
            return NodeInvokeResult(
                ok=False,
                action=action,
                node_id=node_id,
                error=str(exc),
                message="Notification dispatch failed.",
            )


node_runtime = LocalNodeRuntime()

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import sys
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.agents.registry import get_agent_registry
from app.core.config import settings
from app.core.identity import is_configured
from app.core.node_runtime import node_runtime
from app.core.models import AgentSession
from app.skills.loader import load_skills


class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


@dataclass
class HealthCheck:
    level: str  # ok | warn | fail
    check: str
    message: str
    fix: str = ""


def _resolve_active_model() -> str:
    provider = settings.DEFAULT_LLM_PROVIDER
    if provider == "ollama":
        return settings.OLLAMA_MODEL
    if provider == "nvidia":
        return settings.NVIDIA_MODEL
    return "auto"


def collect_status() -> Dict[str, Any]:
    nodes = [n.model_dump() for n in node_runtime.list_nodes()]
    return {
        "project": settings.PROJECT_NAME,
        "configured": is_configured(),
        "provider": settings.DEFAULT_LLM_PROVIDER,
        "model": _resolve_active_model(),
        "skills_loaded": len(load_skills()),
        "agents_registered": len(get_agent_registry().list_agents()),
        "node_runtime_enabled": settings.NODE_RUNTIME_ENABLED,
        "nodes": nodes,
        "workspace": os.getcwd(),
        "python_version": platform.python_version(),
        "env_file_present": os.path.exists(".env"),
    }


def run_health_checks() -> List[HealthCheck]:
    checks: List[HealthCheck] = []

    if not os.path.exists(".env"):
        checks.append(
            HealthCheck(
                level="warn",
                check="env_file",
                message=".env file is missing.",
                fix="Create .env from .env.example and set provider credentials.",
            )
        )
    else:
        checks.append(HealthCheck(level="ok", check="env_file", message=".env file found."))

    provider = settings.DEFAULT_LLM_PROVIDER
    required_by_provider = {
        "openai": ("OPENAI_API_KEY", settings.OPENAI_API_KEY),
        "anthropic": ("ANTHROPIC_API_KEY", settings.ANTHROPIC_API_KEY),
        "gemini": ("GOOGLE_API_KEY", settings.GOOGLE_API_KEY),
        "deepseek": ("DEEPSEEK_API_KEY", settings.DEEPSEEK_API_KEY),
        "openrouter": ("OPENROUTER_API_KEY", settings.OPENROUTER_API_KEY),
        "kimi": ("KIMI_API_KEY", settings.KIMI_API_KEY),
        "nvidia": ("NVIDIA_API_KEY", settings.NVIDIA_API_KEY),
    }
    req = required_by_provider.get(provider)
    if req:
        key_name, key_value = req
        if key_value:
            checks.append(
                HealthCheck(level="ok", check="provider_auth", message=f"{key_name} is configured.")
            )
        else:
            checks.append(
                HealthCheck(
                    level="fail",
                    check="provider_auth",
                    message=f"{provider} provider selected but {key_name} is not set.",
                    fix=f"Set {key_name} in .env or switch DEFAULT_LLM_PROVIDER.",
                )
            )
    else:
        checks.append(
            HealthCheck(level="ok", check="provider_auth", message=f"{provider} provider does not require a remote key by default.")
        )

    if settings.TELEGRAM_POLLING_ENABLED and not settings.TELEGRAM_BOT_TOKEN:
        checks.append(
            HealthCheck(
                level="warn",
                check="telegram",
                message="Telegram polling is enabled but TELEGRAM_BOT_TOKEN is missing.",
                fix="Set TELEGRAM_BOT_TOKEN or set TELEGRAM_POLLING_ENABLED=false.",
            )
        )
    else:
        checks.append(HealthCheck(level="ok", check="telegram", message="Telegram runtime configuration is coherent."))

    if settings.NODE_RUNTIME_ENABLED:
        checks.append(HealthCheck(level="ok", check="node_runtime", message="Node runtime enabled."))
    else:
        checks.append(
            HealthCheck(
                level="warn",
                check="node_runtime",
                message="Node runtime is disabled.",
                fix="Set NODE_RUNTIME_ENABLED=true to expose local node actions.",
            )
        )

    if settings.NODE_RUNTIME_ENABLED and not settings.NODE_RUNTIME_ALLOW_SYSTEM_RUN:
        checks.append(
            HealthCheck(
                level="warn",
                check="node_system_run",
                message="Node action system.run is disabled by policy.",
                fix="Set NODE_RUNTIME_ALLOW_SYSTEM_RUN=true only if command execution via node actions is required.",
            )
        )
    elif settings.NODE_RUNTIME_ENABLED:
        checks.append(HealthCheck(level="ok", check="node_system_run", message="Node action system.run is enabled."))

    return checks


def print_status(status: Dict[str, Any]) -> None:
    print(f"{Colors.BOLD}Astromech Status{Colors.ENDC}")
    print(f"Project: {status['project']}")
    print(f"Configured: {status['configured']}")
    print(f"Provider/Model: {status['provider']}/{status['model']}")
    print(f"Skills loaded: {status['skills_loaded']}")
    print(f"Agents registered: {status['agents_registered']}")
    print(f"Node runtime enabled: {status['node_runtime_enabled']}")
    print(f"Nodes: {len(status['nodes'])}")
    print(f"Workspace: {status['workspace']}")
    print(f"Python: {status['python_version']}")
    print(f".env present: {status['env_file_present']}")


def print_health(checks: List[HealthCheck]) -> None:
    palette = {"ok": Colors.GREEN, "warn": Colors.WARNING, "fail": Colors.FAIL}
    for check in checks:
        color = palette.get(check.level, Colors.ENDC)
        print(f"[{color}{check.level.upper()}{Colors.ENDC}] {check.check}: {check.message}")
        if check.fix:
            print(f"  fix: {check.fix}")


async def run_chat(agent_id: Optional[str], session_id: Optional[str]) -> int:
    from app.agents.orchestrator import AgentOrchestrator

    print(f"{Colors.HEADER}Initializing Astromech CLI...{Colors.ENDC}")
    print(f"Provider: {Colors.CYAN}{settings.DEFAULT_LLM_PROVIDER}{Colors.ENDC}")

    profile = None
    if agent_id:
        profile = get_agent_registry().get_agent(agent_id)
        if not profile:
            print(f"{Colors.FAIL}Agent '{agent_id}' not found.{Colors.ENDC}")
            return 1
        print(f"{Colors.GREEN}Running as agent: {profile.name}{Colors.ENDC}")

    try:
        orchestrator = AgentOrchestrator(agent_profile=profile)
    except Exception as exc:
        print(f"{Colors.FAIL}Failed to initialize orchestrator: {exc}{Colors.ENDC}")
        return 1

    print(f"\n{Colors.GREEN}Astromech Online. Type 'exit' to quit. Type '/agents' to list agents.{Colors.ENDC}")
    current_session = AgentSession(session_id=session_id or str(uuid.uuid4()))
    print("-" * 60)

    while True:
        try:
            user_input = input(f"{Colors.BLUE}You: {Colors.ENDC}").strip()
            if not user_input:
                continue

            if user_input.lower() in {"exit", "quit", "q"}:
                print(f"{Colors.HEADER}Shutting down...{Colors.ENDC}")
                return 0

            if user_input.lower() == "/agents":
                agents = get_agent_registry().list_agents()
                print(f"\n{Colors.CYAN}Available Agents:{Colors.ENDC}")
                for agent in agents:
                    print(f"- {Colors.BOLD}{agent.id}{Colors.ENDC}: {agent.name}")
                print("-" * 60)
                continue

            print(f"{Colors.WARNING}Astromech thinking...{Colors.ENDC}")
            response_obj = await orchestrator.run(user_input, session=current_session)
            if response_obj.session_data:
                current_session = response_obj.session_data

            print(f"\n{Colors.GREEN}Astromech:{Colors.ENDC} {response_obj.response}")
            if response_obj.metadata:
                intent = response_obj.metadata.get("intent", "unknown")
                tools = response_obj.metadata.get("tools_used", [])
                model = response_obj.metadata.get("model_used", "unknown")
                suffix = f" | Tools: {', '.join(tools)}" if tools else ""
                print(f"{Colors.HEADER}[{model} | Intent: {intent}{suffix}]{Colors.ENDC}")
            print("-" * 60)
        except KeyboardInterrupt:
            print("\nExiting...")
            return 0
        except Exception as exc:
            print(f"{Colors.FAIL}Error: {exc}{Colors.ENDC}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Astromech CLI")
    subparsers = parser.add_subparsers(dest="command")

    chat = subparsers.add_parser("chat", help="Start interactive chat shell.")
    chat.add_argument("--agent", default=None, help="Agent profile id")
    chat.add_argument("--session-id", default=None, help="Session id for persistence")

    status = subparsers.add_parser("status", help="Print runtime status summary.")
    status.add_argument("--json", action="store_true", help="Emit JSON output")

    health = subparsers.add_parser("health", help="Run health checks.")
    health.add_argument("--json", action="store_true", help="Emit JSON output")

    doctor = subparsers.add_parser("doctor", help="Run diagnostics and remediation hints.")
    doctor.add_argument("--json", action="store_true", help="Emit JSON output")

    return parser


def main() -> int:
    if os.name == "nt":
        os.system("color")

    parser = build_parser()
    args = parser.parse_args()

    command = args.command or "chat"

    if command == "chat":
        return asyncio.run(run_chat(agent_id=getattr(args, "agent", None), session_id=getattr(args, "session_id", None)))

    if command == "status":
        status = collect_status()
        if args.json:
            print(json.dumps(status, indent=2, default=str))
        else:
            print_status(status)
        return 0

    if command in {"health", "doctor"}:
        checks = run_health_checks()
        summary = {
            "checks": [c.__dict__ for c in checks],
            "ok": sum(1 for c in checks if c.level == "ok"),
            "warn": sum(1 for c in checks if c.level == "warn"),
            "fail": sum(1 for c in checks if c.level == "fail"),
        }
        if args.json:
            print(json.dumps(summary, indent=2, default=str))
        else:
            print_health(checks)
            print(
                f"\nSummary: ok={summary['ok']} warn={summary['warn']} fail={summary['fail']}"
            )
            if command == "doctor" and summary["fail"] == 0 and summary["warn"] == 0:
                print("Doctor: no issues detected.")
        return 1 if summary["fail"] > 0 else 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

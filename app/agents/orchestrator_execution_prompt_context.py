from typing import Any, Dict, List, Optional
import os
import logging

from langchain_core.messages import HumanMessage

from app.agents.orchestrator_context import (
    build_request_channel_context as _build_request_channel_context,
    encode_image,
)
from app.agents.session_manager import SessionManager
from app.core.identity import get_cached_system_prompt
from app.core.models import AgentSession
from app.core.system_info import get_system_context_string
from app.skills.loader import format_skills_for_prompt, load_skills

logger = logging.getLogger(__name__)


async def build_full_system_prompt(
    *,
    orchestrator: Any,
    memory: str,
    source_channel: str,
    source_metadata: Optional[Dict[str, Any]],
) -> str:
    sys_context = await get_system_context_string()
    request_channel_context = _build_request_channel_context(source_channel, source_metadata)

    if orchestrator.agent_profile:
        return (
            f"{sys_context}\n\n{orchestrator.agent_profile.system_prompt}\n\n"
            f"{request_channel_context}\n\nCONTEXT:\n{memory}"
        )

    system_text = get_cached_system_prompt()
    skills = load_skills()
    skills_text = format_skills_for_prompt(skills)
    memory_instructions = (
        "\n\nMEMORY SYSTEM:\n"
        "You have a tiered memory system:\n"
        "- RELATIONSHIP MEMORY (HIGHEST PRIORITY): Durable user facts (preferences, habits, recurring projects, communication style) with confidence and last-confirmed metadata.\n"
        "- SHORT-TERM: Automatic summaries of earlier conversation (shown in system prompt as 'SHORT-TERM MEMORY'). These cover today's conversation history beyond the visible message window.\n"
        "- LONG-TERM (RAG): Persistent memories stored in the vector database. Use the 'save_memory' tool to store very important facts, user preferences, key decisions, or critical information that should be remembered across sessions.\n"
        "Only save to long-term memory when information is genuinely significant and worth remembering permanently. Do not save trivial exchanges."
    )
    tool_instructions = (
        "\n\nTOOL USAGE PROTOCOL:\n"
        "1. PREFER NATIVE TOOLS: You have real, executable tools. USE THEM.\n"
        "2. NO SIMULATION: Do NOT describe actions (e.g., 'I will run this command...'). Do NOT output code blocks to simulate actions. Do NOT output '**Tool Call**'.\n"
        "3. FILE EDITS: You CAN modify repository files. Use 'read_local_file' to inspect, 'replace_text_in_file' for surgical edits, and 'write_local_file' for full rewrites.\n"
        "4. COMMANDS: To run shell commands, use the 'terminal' tool with the command string.\n"
        "5. PYTHON: To run Python, use 'run_python_code' or write a script to disk and run it with 'terminal'.\n"
        "6. SILENCE: Do not narrate your tool calls. Just call them.\n"
        "7. MULTI-STEP: If a task requires multiple steps, execute them in sequence using tool calls.\n"
        "8. RESPONSES: Only respond with text alone when the user is asking a question that requires no action."
    )
    personality_instructions = (
        "\n\nPERSONALITY ENFORCEMENT:\n"
        "1. Stay in R2 astromech character for every final user-facing response.\n"
        "2. Keep personality visible but controlled: brief droid flavor, then concrete answer.\n"
        "3. Do not become generic/corporate assistant voice after tool calls; preserve character continuity.\n"
        "4. For high-stakes topics, keep tone direct and precise while retaining light character markers.\n"
        "5. Start with the answer first, then include concise supporting detail or next actions."
    )
    return (
        f"{sys_context}\n\n{system_text}\n\n{skills_text}{memory_instructions}{tool_instructions}{personality_instructions}\n\n"
        f"{request_channel_context}\n\nCONTEXT:\n{memory}"
    )


def build_human_message(
    *,
    prompt: str,
    images: Optional[List[str]],
    exec_ctx: Dict[str, Any],
) -> HumanMessage:
    if not images:
        return HumanMessage(content=prompt)

    content_blocks = [{"type": "text", "text": prompt}]
    for img_path in images:
        try:
            if os.path.exists(img_path):
                img_data = encode_image(img_path)
                content_blocks.append({"type": "image_url", "image_url": {"url": img_data}})
            elif img_path.startswith("http"):
                content_blocks.append({"type": "image_url", "image_url": {"url": img_path}})
        except Exception as e:
            logger.warning("Failed to encode image '%s': %s", img_path, e, extra=exec_ctx)

    return HumanMessage(content=content_blocks)


def build_initial_messages(
    *,
    orchestrator: Any,
    session_manager: SessionManager,
    session: AgentSession,
    prompt: str,
    full_system_prompt: str,
) -> List[Any]:
    history_msgs = [session_manager.dict_to_langchain(m) for m in session.messages]
    short_term_ctx = orchestrator.short_term_memory.get_today_context(session.session_id)
    return orchestrator.context_manager.optimize_context(
        full_system_prompt,
        history_msgs,
        prompt,
        session.context_files,
        short_term_context=short_term_ctx,
    )

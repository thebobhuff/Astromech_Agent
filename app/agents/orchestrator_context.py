import base64
import mimetypes
from typing import Any, Dict, Optional


def normalize_source_channel(channel: Optional[str], session_id: str) -> str:
    value = (channel or "").strip().lower()
    aliases = {
        "web": "ui",
        "frontend": "ui",
        "chat": "ui",
        "telegram_bot": "telegram",
        "discord_bot": "discord",
        "task": "heartbeat",
    }
    if value in aliases:
        value = aliases[value]

    allowed = {
        "ui",
        "telegram",
        "discord",
        "heartbeat",
        "subagent",
        "api",
        "cli",
    }
    if value in allowed:
        return value

    sid = (session_id or "").lower()
    if sid.startswith("telegram_"):
        return "telegram"
    if sid.startswith("discord_"):
        return "discord"
    if sid.startswith("task_") or sid == "heartbeat_session":
        return "heartbeat"
    if sid.startswith("sub-"):
        return "subagent"
    return "ui"


def build_request_channel_context(
    source_channel: str,
    source_metadata: Optional[Dict[str, Any]] = None,
) -> str:
    lines = [
        "REQUEST CONTEXT:",
        f"- Source channel: {source_channel}",
    ]
    if source_metadata:
        safe_items = []
        for key in ("platform_user_id", "platform_username", "chat_id", "is_dm", "transport"):
            if key not in source_metadata:
                continue
            value = str(source_metadata.get(key) or "").strip()
            if not value:
                continue
            safe_items.append(f"{key}={value}")
        if safe_items:
            lines.append(f"- Source metadata: {', '.join(safe_items)}")
    lines.append(
        "- Adapt tone/format/tool choices to this channel while preserving the same task outcome."
    )
    return "\n".join(lines)


def log_extra(
    session_id: Optional[str] = None,
    turn: Optional[int] = None,
    attempt: Optional[int] = None,
    tool: Optional[str] = None,
    event: Optional[str] = None,
) -> Dict[str, Any]:
    extra: Dict[str, Any] = {}
    if session_id:
        extra["session_id"] = session_id
    if turn is not None:
        extra["turn"] = turn
    if attempt is not None:
        extra["attempt"] = attempt
    if tool:
        extra["tool"] = tool
    if event:
        extra["event"] = event
    return extra


def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("utf-8")
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type:
            mime_type = "image/jpeg"
        return f"data:{mime_type};base64,{encoded}"

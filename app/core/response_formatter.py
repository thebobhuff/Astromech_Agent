from __future__ import annotations

import re
from typing import Literal, List

ChannelType = Literal["ui", "telegram", "discord"]

_CHANNEL_LIMITS = {
    "ui": 48,      # preserve existing UI pseudo-streaming behavior
    "telegram": 4000,  # hard limit is 4096, keep safety margin
    "discord": 1900,   # hard limit is 2000, keep safety margin
}


def normalize_channel(channel: str | None) -> ChannelType:
    value = (channel or "ui").strip().lower()
    if value in {"telegram", "discord", "ui"}:
        return value  # type: ignore[return-value]
    return "ui"


def _sanitize_common(text: str) -> str:
    out = (text or "").replace("\r\n", "\n").strip()
    out = re.sub(r"\[(.*?)\]\((https?://[^\s)]+)\)", r"\1 (\2)", out)
    out = re.sub(r"<(https?://[^>]+)>", r"\1", out)
    return out


def _to_plain_text_markdown(text: str) -> str:
    out = text
    out = re.sub(r"^\s{0,3}#{1,6}\s*", "", out, flags=re.MULTILINE)
    out = re.sub(r"^\s{0,3}>\s?", "", out, flags=re.MULTILINE)
    out = re.sub(r"^\s{0,3}[-*+]\s+", "- ", out, flags=re.MULTILINE)
    out = re.sub(r"```([a-zA-Z0-9_-]+)?\n", "Code:\n", out)
    out = out.replace("```", "")
    out = out.replace("**", "").replace("__", "")
    out = out.replace("`", "")
    return out


def format_response_for_channel(text: str, channel: str | None) -> str:
    """
    Format a model response for delivery in a target channel.
    - ui: preserve markdown-rich output.
    - discord: preserve markdown, normalize links/newlines.
    - telegram: simplify markdown to plain-text friendly output.
    """
    normalized = normalize_channel(channel)
    content = _sanitize_common(text)
    if normalized == "telegram":
        return _to_plain_text_markdown(content)
    return content


def split_response_for_channel(text: str, channel: str | None) -> List[str]:
    normalized = normalize_channel(channel)
    max_len = _CHANNEL_LIMITS[normalized]
    if not text:
        return []
    if len(text) <= max_len:
        return [text]

    chunks: List[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= max_len:
            chunks.append(remaining)
            break

        split_at = remaining.rfind("\n", 0, max_len)
        if split_at < int(max_len * 0.5):
            split_at = remaining.rfind(" ", 0, max_len)
        if split_at < int(max_len * 0.5):
            split_at = max_len

        chunk = remaining[:split_at]
        if chunk:
            chunks.append(chunk)
        # Preserve boundary whitespace so reconstructed streaming text
        # does not lose spaces between adjacent chunks.
        remaining = remaining[split_at:]

    return chunks

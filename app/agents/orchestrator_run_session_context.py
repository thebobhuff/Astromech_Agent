from typing import Any, Dict, Optional, Tuple

from app.agents.orchestrator_context import (
    normalize_source_channel,
    build_request_channel_context,
)
from app.core.models import AgentProfile, AgentSession


def prepare_session_channel_context(
    *,
    session: AgentSession,
    source_channel: Optional[str],
    source_metadata: Optional[Dict[str, Any]],
) -> Tuple[str, str]:
    resolved_channel = normalize_source_channel(source_channel, session.session_id)
    request_channel_context = build_request_channel_context(resolved_channel, source_metadata)

    session.metadata["last_channel"] = resolved_channel
    if source_metadata:
        session.metadata["last_source_metadata"] = dict(source_metadata)

    channel_history = session.metadata.get("channel_history", [])
    if not isinstance(channel_history, list):
        channel_history = []
    channel_history.append(resolved_channel)
    session.metadata["channel_history"] = channel_history[-25:]

    return resolved_channel, request_channel_context


def apply_profile_model_override(
    *,
    agent_profile: Optional[AgentProfile],
    model_override: Optional[str],
) -> Optional[str]:
    if not agent_profile or model_override:
        return model_override

    if agent_profile.provider and agent_profile.model:
        return f"{agent_profile.provider}/{agent_profile.model}"
    if agent_profile.provider:
        return f"{agent_profile.provider}/default"
    return model_override
